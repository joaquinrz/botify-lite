import json
import os
import structlog
from typing import AsyncGenerator, Dict, Any, Optional

from openai import AsyncAzureOpenAI
from traceloop.sdk.decorators import task

from ..core.config import settings

# Set up structured logging
logger = structlog.get_logger(__name__)


class AzureOpenAIService:
    """Service for interacting with Azure OpenAI APIs."""
    
    def __init__(self):
        """Initialize the Azure OpenAI client with settings from config."""
        # Validate settings using centralized validation
        validation_result = settings.validate_service_config("openai")
        if not validation_result["configured"]:
            missing = ", ".join(validation_result["missing"])
            raise ValueError(
                f"Missing required OpenAI settings: {missing}. "
                f"Please update your credentials.env file with the required values."
            )
            
        # Vector store is also required for this service
        vector_store_validation = settings.validate_service_config("vector_store")
        if not vector_store_validation["configured"]:
            raise ValueError(
                "Missing vector store ID. Please set AZURE_OPENAI_VECTOR_STORE_ID in your credentials.env file."
            )
        
        # Initialize client if validation passes
        self.client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version
        )
        self.model_name = settings.model_name
        self.vector_store_id = settings.vector_store_id
        
        # Load the assistant instructions
        self.assistant_instructions = self._load_instructions()
        
        # Store last response IDs for Responses API to maintain threaded context
        self.last_response_id: Dict[str, str] = {}
    
    @task(name="load_instructions")
    def _load_instructions(self) -> str:
        """Load the assistant instructions from the prompt file."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        prompt_path = os.path.join(base_dir, "prompts", "assistant_instructions.txt")
        
        try:
            with open(prompt_path, "r") as file:
                return file.read()
        except FileNotFoundError:
            logger.warning("openai.instructions_missing", path=prompt_path)
            return """
            1. You must not use prior knowledge to answer questions; only information retrieved from the vector store is allowed.
            2. Your output MUST always be a valid JSON object with voiceSummary and displayResponse properties.
            """

    @task(name="get_chat_response")
    async def get_chat_response(self, prompt: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Single‐turn or continued chat via Responses API. If session_id is provided, previous context is preserved.
        """
        # Retrieve last response ID for keeping track of the conversation
        prev_id = self.last_response_id.get(session_id) if session_id else None

        # Call the Responses API (non-streaming)
        resp = await self.client.responses.create(
            model=self.model_name,
            instructions=self.assistant_instructions,
            input=prompt,
            previous_response_id=prev_id,
            tools=[{
                "type": "file_search",
                "vector_store_ids": [self.vector_store_id],
            }],
            stream=False
        )

        # Parse the assistant's JSON response
        result = json.loads(resp.output_text)

        # Store the new response ID for next turn
        if session_id:
            self.last_response_id[session_id] = resp.id

        return result

    @task(name="get_chat_response_stream")
    async def get_chat_response_stream(
        self,
        prompt: str,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Yields text.delta chunks as they arrive via Responses API streaming.
        """
        prev_id = self.last_response_id.get(session_id) if session_id else None

        response = await self.client.responses.create(
            model=self.model_name,
            instructions=self.assistant_instructions,
            input=prompt,
            previous_response_id=prev_id,
            tools=[{
                "type": "file_search",
                "vector_store_ids": [self.vector_store_id],
            }],
            stream=True
        )

        async for event in response:
            # Only yield the text.delta payloads
            if getattr(event, "type", "").endswith("text.delta"):
                yield event.delta
        # Handle the end of the stream
            elif getattr(event, "type", "").endswith("response.completed"):
                self.last_response_id[session_id] = event.response.id
                

# Create a service instance to be used throughout the application
try:
    openai_service = AzureOpenAIService()
except ValueError as e:
    logger.error(f"Azure OpenAI service initialization failed: {e}")
    # Still create the service, but it will raise errors when methods are called
    openai_service = None
