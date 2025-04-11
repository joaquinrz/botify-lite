import json
import asyncio
import os
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List, Union, Tuple

from openai import AsyncAzureOpenAI

from ..core.config import settings

# Set up logging
logger = logging.getLogger(__name__)


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
        
        # Store thread IDs by session to maintain conversation state
        self.sessions = {}
        # Store assistants by thread IDs
        self.assistants = {}
    
    def _load_instructions(self) -> str:
        """Load the assistant instructions from the prompt file."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        prompt_path = os.path.join(base_dir, "prompts", "assistant_instructions.txt")
        
        try:
            with open(prompt_path, "r") as file:
                return file.read()
        except FileNotFoundError:
            logger.warning(f"Instructions file not found at {prompt_path}. Using default instructions.")
            return """
            1. You must not use prior knowledge to answer questions; only information retrieved from the vector store is allowed.
            2. Your output MUST always be a valid JSON object with voiceSummary and displayResponse properties.
            """
    
    async def create_assistant(self) -> Any:
        """Create an assistant with the specified configuration."""
        try:
            return await self.client.beta.assistants.create(
                model=self.model_name,
                instructions=self.assistant_instructions,
                tools=[{"type": "file_search"}],
                tool_resources={"file_search": {"vector_store_ids": [self.vector_store_id]}},
                temperature=1,
                top_p=1,
            )
        except Exception as e:
            self._enhance_error_message(e)
    
    def _enhance_error_message(self, error: Exception) -> None:
        """Enhance error messages with more context and raise appropriate exceptions."""
        error_message = str(error)
        if "Authorization" in error_message:
            raise ValueError(
                f"Authorization failed: Please check your AZURE_OPENAI_API_KEY. Error: {error_message}"
            ) from error
        elif "not found" in error_message and self.model_name in error_message:
            raise ValueError(
                f"Model '{self.model_name}' was not found. Please check your AZURE_OPENAI_MODEL_NAME. Error: {error_message}"
            ) from error
        elif "resource" in error_message and "not found" in error_message:
            raise ValueError(
                f"Azure OpenAI resource not found. Please check your AZURE_OPENAI_ENDPOINT. Error: {error_message}"
            ) from error
        else:
            raise ValueError(f"Error with Azure OpenAI service: {error_message}") from error
    
    async def get_or_create_thread(self, session_id: Optional[str] = None) -> Any:
        """Get an existing thread or create a new one for a session."""
        # If no session ID is provided or the session doesn't exist, create a new thread
        if not session_id or session_id not in self.sessions:
            logger.info(f"Creating new thread for session: {session_id}")
            thread = await self.client.beta.threads.create()
            logger.info(f"New thread created with ID: {thread.id}")
            
            # If we have a session ID, store it for later use
            if session_id:
                self.sessions[session_id] = thread.id
                
            return thread
        
        # If the session exists, get the thread ID
        thread_id = self.sessions[session_id]
        logger.info(f"Using existing thread ID {thread_id} for session ID {session_id}")
        
        # Return a simple object with just the ID to use in API calls
        return type('Thread', (), {'id': thread_id})
    
    async def get_or_create_assistant(self, thread_id: str) -> Any:
        """Get an existing assistant or create a new one for a thread."""
        # If the thread doesn't have an associated assistant, create one
        if thread_id not in self.assistants:
            assistant = await self.create_assistant()
            self.assistants[thread_id] = assistant.id
            return assistant
            
        # If the thread has an associated assistant, get the assistant ID
        assistant_id = self.assistants[thread_id]
        
        # Return a simple object with the ID
        return type('Assistant', (), {'id': assistant_id})
    
    async def add_message_to_thread(self, thread_id: str, message: str) -> Any:
        """Add a user message to the thread."""
        return await self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )
    
    async def run_thread(self, thread_id: str, assistant_id: str) -> Any:
        """Run the thread with the specified assistant."""
        return await self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
    
    async def poll_run_status(self, thread_id: str, run_id: str) -> Any:
        """Poll for run status until completion."""
        run = await self.client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )
        
        poll_count = 0
        run_start_time = asyncio.get_event_loop().time()
        
        while run.status in ["queued", "in_progress", "cancelling"]:
            poll_count += 1
            await asyncio.sleep(1)
            logger.info(f"Polling run status ({poll_count}): {run.status}")
            
            run = await self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
        
        run_duration = asyncio.get_event_loop().time() - run_start_time
        logger.info(f"Run completed with status {run.status} after {run_duration:.2f} seconds and {poll_count} polls")
        
        return run
    
    async def get_messages(self, thread_id: str, order: str = "desc", limit: int = 10) -> List[Any]:
        """Get messages from a thread."""
        messages = await self.client.beta.threads.messages.list(
            thread_id=thread_id,
            order=order,
            limit=limit
        )
        
        return messages.data
    
    async def find_assistant_message(self, messages: List[Any], baseline_message_ids: set = None) -> Optional[Any]:
        """Find the most relevant assistant message from a list of messages."""
        # If we have baseline message IDs, look for new assistant messages
        if baseline_message_ids:
            for msg in messages:
                if msg.role == "assistant" and msg.id not in baseline_message_ids:
                    logger.info(f"Found new assistant message with ID: {msg.id}")
                    return msg
        
        # If no specific new message is found, use the first assistant message
        for msg in messages:
            if msg.role == "assistant":
                return msg
                
        return None
    
    def extract_message_content(self, message: Any) -> Dict[str, str]:
        """Extract and parse the content from an assistant message."""
        if not message or not message.content:
            logger.warning("No valid message content found")
            return {
                "voiceSummary": "No response was generated",
                "displayResponse": "No response was generated"
            }
        
        try:
            content_text = message.content[0].text.value
            # Parse JSON from assistant's response
            return json.loads(content_text)
        except (json.JSONDecodeError, AttributeError, IndexError) as e:
            logger.error(f"Error processing response content: {str(e)}")
            return {
                "voiceSummary": "Error processing response",
                "displayResponse": f"Error processing response: {str(e)}"
            }
    
    async def get_chat_response(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get a chat response for a message (non-streaming)."""
        try:
            logger.info(f"Processing chat request: '{message[:20]}...' (session: {session_id})")
            start_time = asyncio.get_event_loop().time()
            
            # Set up thread, assistant and get baseline message IDs
            thread, assistant, baseline_message_ids = await self._setup_thread_for_chat(message, session_id)
            
            # Run the thread
            run = await self.run_thread(thread.id, assistant.id)
            
            # Wait for the run to complete
            run = await self.poll_run_status(thread.id, run.id)
            
            if run.status == "completed":
                # Get messages after completion
                messages = await self.get_messages(thread.id)
                
                # Find the assistant's response message
                assistant_message = await self.find_assistant_message(messages, baseline_message_ids)
                
                # Extract and return the content
                result = self.extract_message_content(assistant_message)
                
                total_duration = asyncio.get_event_loop().time() - start_time
                logger.info(f"Total request processing took {total_duration:.2f} seconds")
                return result
            
            logger.error(f"Chat request failed with run status: {run.status}")
            return {
                "voiceSummary": f"Error: {run.status}",
                "displayResponse": f"Error: Run completed with status '{run.status}'"
            }
        except ValueError as e:
            logger.error(f"Configuration error: {str(e)}")
            # Pass through credential-related errors
            return self._create_error_response(e, is_config_error=True)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return self._create_error_response(e)
    
    async def get_chat_response_stream(self, message: str, session_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Get a streaming chat response with word by word streaming."""
        try:
            logger.info(f"Processing streaming chat: '{message[:20]}...' (session: {session_id})")
            start_time = asyncio.get_event_loop().time()
            
            # Set up thread, assistant and get baseline message IDs
            thread, assistant, initial_message_ids = await self._setup_thread_for_chat(message, session_id)
            
            # Run the thread
            run = await self.run_thread(thread.id, assistant.id)
            
            # Track the accumulated response for detecting changes
            last_content_length = 0
            poll_count = 0
            content_updates = 0
            assistant_message_id = None
            current_word_buffer = ""
            
            # Wait for the run to complete while streaming
            while run.status in ["queued", "in_progress", "cancelling"]:
                poll_count += 1
                
                if run.status == "in_progress":
                    # Get the latest messages
                    messages = await self.get_messages(thread.id)
                    
                    # Look for new assistant messages
                    for msg in messages:
                        if msg.role == "assistant" and msg.id not in initial_message_ids:
                            # Found a new assistant message
                            if assistant_message_id is None or msg.id == assistant_message_id:
                                assistant_message_id = msg.id
                                if msg.content:
                                    try:
                                        current_content = msg.content[0].text.value
                                        
                                        # If we have new content
                                        if len(current_content) > last_content_length:
                                            content_updates += 1
                                            new_text = current_content[last_content_length:]
                                            last_content_length = len(current_content)
                                            
                                            # Use our helper to stream the new text word by word
                                            async for word in self._stream_text_word_by_word(new_text):
                                                yield word
                                            
                                            # If there's anything left in the buffer at the end of new text,
                                            # keep it for the next iteration
                                    except (AttributeError, IndexError) as e:
                                        logger.error(f"Error processing streaming content: {str(e)}")
                                    break
                
                # Short interval for responsive polling
                await asyncio.sleep(0.3)
                run = await self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            # Run completed, check final status
            if run.status == "completed":
                # Get final response
                messages = await self.get_messages(thread.id)
                
                # Find the latest assistant message
                assistant_message = None
                for msg in messages:
                    if msg.role == "assistant" and (assistant_message_id is None or msg.id == assistant_message_id):
                        assistant_message = msg
                        break
                
                if assistant_message and assistant_message.content:
                    try:
                        final_content = assistant_message.content[0].text.value
                        # Send any remaining content
                        remaining = final_content[last_content_length:]
                        if remaining:
                            # Use our helper to stream any remaining text
                            async for word in self._stream_text_word_by_word(remaining):
                                yield word
                    except (AttributeError, IndexError) as e:
                        logger.error(f"Error processing final streaming content: {str(e)}")
            else:
                # If run failed, yield an error message
                error_json = json.dumps({
                    "voiceSummary": f"Error: {run.status}",
                    "displayResponse": f"Error: Run completed with status '{run.status}'"
                })
                logger.error(f"Stream failed with status: {run.status}")
                
                # Use our helper to stream the error message word by word
                async for word in self._stream_text_word_by_word(error_json):
                    yield word
                
            total_duration = asyncio.get_event_loop().time() - start_time
            logger.info(f"Total streaming request took {total_duration:.2f} seconds")
                
        except ValueError as e:
            # For credential-related errors
            logger.error(f"Configuration error in streaming: {str(e)}")
            error_response = self._create_error_response(e, is_config_error=True)
            error_json = json.dumps(error_response)
            
            # Stream the error message using our helper
            async for word in self._stream_text_word_by_word(error_json):
                yield word
                
        except Exception as e:
            # For other errors
            logger.error(f"Unexpected error in streaming: {str(e)}", exc_info=True)
            error_response = self._create_error_response(e)
            error_json = json.dumps(error_response)
            
            # Stream the error message using our helper
            async for word in self._stream_text_word_by_word(error_json):
                yield word
                
    async def cleanup_session(self, session_id: str) -> bool:
        """Cleanup resources associated with a session."""
        if session_id in self.sessions:
            thread_id = self.sessions[session_id]
            
            # Remove the assistant if it exists
            if thread_id in self.assistants:
                del self.assistants[thread_id]
            
            # Remove the session
            del self.sessions[session_id]
            return True
            
        return False
    
    async def _stream_text_word_by_word(self, text: str) -> AsyncGenerator[str, None]:
        """
        Helper method to stream text word by word with appropriate pauses.
        
        Args:
            text: Text content to stream
            
        Yields:
            Words or word fragments with punctuation
        """
        # Split text by spaces but keep punctuation attached to words
        words = []
        current_word = ""
        
        for char in text:
            if char == ' ':
                if current_word:
                    words.append(current_word)
                    current_word = ""
            else:
                current_word += char
        
        # Add the last word if there is one
        if current_word:
            words.append(current_word)
        
        # Yield each word with a small delay
        for word in words:
            yield word
            await asyncio.sleep(0.05)  # Consistent pause between words
    
    async def _setup_thread_for_chat(self, message: str, session_id: Optional[str] = None) -> Tuple[Any, Any, set]:
        """
        Common setup for both streaming and non-streaming chat responses.
        
        Args:
            message: The user message
            session_id: Optional session ID for conversation persistence
            
        Returns:
            Tuple containing (thread, assistant, baseline_message_ids)
        """
        # Get or create thread for this session
        thread = await self.get_or_create_thread(session_id)
        
        # Get or create assistant for this thread
        assistant = await self.get_or_create_assistant(thread.id)
        
        # Get baseline messages before adding the new message
        baseline_messages = await self.get_messages(thread.id)
        baseline_message_ids = {msg.id for msg in baseline_messages}
        
        # Add user message to thread
        await self.add_message_to_thread(thread.id, message)
        
        # Return the setup results
        return thread, assistant, baseline_message_ids
    
    def _create_error_response(self, error: Exception, is_config_error: bool = False) -> Dict[str, str]:
        """Create a standardized error response."""
        error_message = str(error)
        if is_config_error:
            summary = f"Configuration Error: {error_message}"
            display = f"The AI service is not properly configured: {error_message}"
        else:
            summary = f"Error: {error_message}"
            display = f"An unexpected error occurred: {error_message}"
        
        return {
            "voiceSummary": summary,
            "displayResponse": display
        }


# Create a service instance to be used throughout the application
try:
    openai_service = AzureOpenAIService()
except ValueError as e:
    logger.error(f"Azure OpenAI service initialization failed: {e}")
    # Still create the service, but it will raise errors when methods are called
    openai_service = None