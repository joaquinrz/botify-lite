import json
import asyncio
import os
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List

from openai import AsyncAzureOpenAI
from sse_starlette.sse import EventSourceResponse

from ..core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AzureOpenAIService:
    """Service for interacting with Azure OpenAI APIs."""
    
    def __init__(self):
        """Initialize the Azure OpenAI client with settings from config."""
        # Validate required settings
        self._validate_settings()
        
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
    
    def _validate_settings(self) -> None:
        """Validate the required Azure OpenAI settings.
        
        Raises:
            ValueError: If any required setting is missing or empty.
        """
        missing_settings = []
        
        if not settings.azure_openai_endpoint:
            missing_settings.append("AZURE_OPENAI_ENDPOINT")
        
        if not settings.azure_openai_api_key:
            missing_settings.append("AZURE_OPENAI_API_KEY")
        
        if not settings.model_name:
            missing_settings.append("AZURE_OPENAI_MODEL_NAME")
        
        if not settings.vector_store_id:
            missing_settings.append("AZURE_OPENAI_VECTOR_STORE_ID")
        
        if missing_settings:
            raise ValueError(
                f"Missing required Azure OpenAI settings: {', '.join(missing_settings)}. "
                f"Please update your credentials.env file with the required values."
            )
    
    def _load_instructions(self) -> str:
        """Load the assistant instructions from the prompt file.
        
        Returns:
            The content of the assistant instructions file.
        
        Raises:
            FileNotFoundError: If the instructions file cannot be found.
        """
        # Get the base directory of the application
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        prompt_path = os.path.join(base_dir, "prompts", "assistant_instructions.txt")
        
        try:
            with open(prompt_path, "r") as file:
                return file.read()
        except FileNotFoundError:
            # Fallback to a default instruction if the file is not found
            print(f"Warning: Instructions file not found at {prompt_path}. Using default instructions.")
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
            # Enhance error message with more context
            error_message = str(e)
            if "Authorization" in error_message:
                raise ValueError(
                    f"Authorization failed: Please check your AZURE_OPENAI_API_KEY. Error: {error_message}"
                ) from e
            elif "not found" in error_message and self.model_name in error_message:
                raise ValueError(
                    f"Model '{self.model_name}' was not found. Please check your AZURE_OPENAI_MODEL_NAME. Error: {error_message}"
                ) from e
            elif "resource" in error_message and "not found" in error_message:
                raise ValueError(
                    f"Azure OpenAI resource not found. Please check your AZURE_OPENAI_ENDPOINT. Error: {error_message}"
                ) from e
            else:
                raise ValueError(f"Error creating assistant: {error_message}") from e
    
    async def get_or_create_thread(self, session_id: Optional[str] = None) -> Any:
        """Get an existing thread or create a new one for a session.
        
        Args:
            session_id: Optional session identifier to maintain conversation state.
            
        Returns:
            Thread object from OpenAI API.
        """
        # If no session ID is provided or the session doesn't exist, create a new thread
        if not session_id or session_id not in self.sessions:
            logger.info(f"Creating new thread for session: {session_id}")
            # Create a new thread
            thread = await self.client.beta.threads.create()
            logger.info(f"New thread created with ID: {thread.id}")
            
            # If we have a session ID, store it for later use
            if session_id:
                self.sessions[session_id] = thread.id
                logger.info(f"Associated thread ID {thread.id} with session ID {session_id}")
                
            return thread
        
        # If the session exists, get the thread ID
        thread_id = self.sessions[session_id]
        logger.info(f"Using existing thread ID {thread_id} for session ID {session_id}")
        
        # We don't need to retrieve the thread object, just provide its ID
        # This is a simple object with just the ID to use in API calls
        return type('Thread', (), {'id': thread_id})
    
    async def get_or_create_assistant(self, thread_id: str) -> Any:
        """Get an existing assistant or create a new one for a thread.
        
        Args:
            thread_id: Thread identifier to associate with an assistant.
            
        Returns:
            Assistant object from OpenAI API.
        """
        # If the thread doesn't have an associated assistant, create one
        if thread_id not in self.assistants:
            assistant = await self.create_assistant()
            self.assistants[thread_id] = assistant.id
            return assistant
            
        # If the thread has an associated assistant, get the assistant ID
        assistant_id = self.assistants[thread_id]
        
        # Similar to the thread, we just need a simple object with the ID
        return type('Assistant', (), {'id': assistant_id})
    
    def add_message_to_thread(self, thread_id: str, message: str) -> Any:
        """Add a user message to the thread."""
        return self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )
    
    def run_thread(self, thread_id: str, assistant_id: str) -> Any:
        """Run the thread with the specified assistant."""
        return self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
    
    def get_run_status(self, thread_id: str, run_id: str) -> Any:
        """Check the status of a run."""
        return self.client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )
    
    def get_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get messages from a thread."""
        messages = self.client.beta.threads.messages.list(
            thread_id=thread_id,
            order="asc"  # Get messages in ascending order (oldest first)
        )
        return messages.data
    
    async def get_chat_response(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get a chat response for a message (non-streaming).
        
        Args:
            message: The user message to process.
            session_id: Optional session identifier to maintain conversation state.
            
        Returns:
            A dictionary with voiceSummary and displayResponse.
            
        Raises:
            ValueError: If there's an issue with Azure OpenAI credentials.
            Exception: For other errors during processing.
        """
        try:
            logger.info(f"Processing chat request with message: '{message[:20]}...' and session ID: {session_id}")
            start_time = asyncio.get_event_loop().time()
            
            # Get or create thread for this session
            thread = await self.get_or_create_thread(session_id)
            logger.info(f"Using thread ID: {thread.id}")
            
            # Get or create assistant for this thread
            assistant = await self.get_or_create_assistant(thread.id)
            logger.info(f"Using assistant ID: {assistant.id}")
            
            # Get baseline messages before adding the new message
            baseline_messages = await self.client.beta.threads.messages.list(
                thread_id=thread.id,
                order="desc",
                limit=10
            )
            baseline_message_ids = {msg.id for msg in baseline_messages.data}
            
            # Add user message to thread
            logger.info(f"Adding message to thread {thread.id}")
            user_message = await self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=message
            )
            
            # Track the user message ID to find the corresponding response later
            user_message_id = user_message.id
            logger.info(f"Added user message with ID: {user_message_id}")
            
            # Run the thread
            logger.info(f"Starting thread run with thread ID {thread.id} and assistant ID {assistant.id}")
            run_start_time = asyncio.get_event_loop().time()
            run = await self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id
            )
            run_id = run.id
            logger.info(f"Run created with ID: {run_id}, initial status: {run.status}")
            
            # Wait for the run to complete
            poll_count = 0
            while run.status in ["queued", "in_progress", "cancelling"]:
                poll_count += 1
                await asyncio.sleep(1)
                logger.info(f"Polling run status ({poll_count}): {run.status}")
                run = await self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            run_duration = asyncio.get_event_loop().time() - run_start_time
            logger.info(f"Run completed with status {run.status} after {run_duration:.2f} seconds and {poll_count} polls")
            
            if run.status == "completed":
                logger.info(f"Getting messages from thread {thread.id}")
                # Get messages in descending order (newest first) after completion
                messages = await self.client.beta.threads.messages.list(
                    thread_id=thread.id,
                    order="desc", # Newest messages first
                    limit=20
                )
                
                if not messages.data:
                    logger.warning("No messages found in thread after completion")
                    return {
                        "voiceSummary": "No response was generated",
                        "displayResponse": "No response was generated"
                    }
                
                # First, look for new assistant messages that weren't in our baseline
                assistant_message = None
                
                for msg in messages.data:
                    if msg.role == "assistant" and msg.id not in baseline_message_ids:
                        # This is a new assistant message - very likely our response
                        assistant_message = msg
                        logger.info(f"Found new assistant message with ID: {msg.id}")
                        break
                
                # If we didn't find any new assistant messages, try a different approach
                if assistant_message is None:
                    # Find the last user message (which should be ours)
                    last_user_message = next((m for m in messages.data if m.role == "user"), None)
                    
                    if last_user_message and last_user_message.id == user_message_id:
                        # Now find the first assistant message that comes after this in the conversation
                        # Since we're in desc order, we need to find assistant messages later in the list
                        found_user_message = False
                        for idx, msg in enumerate(messages.data):
                            if found_user_message and msg.role == "assistant":
                                assistant_message = msg
                                logger.info(f"Found assistant message with ID: {msg.id} using user message position")
                                break
                            
                            if msg.id == user_message_id:
                                found_user_message = True
                
                # If we still don't have an assistant message, just take the most recent one
                if assistant_message is None:
                    assistant_message = next((m for m in messages.data if m.role == "assistant"), None)
                    if assistant_message:
                        logger.info(f"Using most recent assistant message with ID: {assistant_message.id}")
                
                if assistant_message and assistant_message.content:
                    try:
                        content_text = assistant_message.content[0].text.value
                        logger.info(f"Successfully retrieved assistant message content with ID: {assistant_message.id}")
                        
                        # Parse JSON from assistant's response
                        result = json.loads(content_text)
                        total_duration = asyncio.get_event_loop().time() - start_time
                        logger.info(f"Total request processing took {total_duration:.2f} seconds")
                        return result
                    except (json.JSONDecodeError, AttributeError, IndexError) as e:
                        logger.error(f"Error processing response: {str(e)}")
                        return {
                            "voiceSummary": "Error processing response",
                            "displayResponse": f"Error processing response: {str(e)}"
                        }
                else:
                    logger.warning("No assistant message found in thread")
                    return {
                        "voiceSummary": "No response was generated",
                        "displayResponse": "No response was generated"
                    }
            
            logger.error(f"Chat request failed with run status: {run.status}")
            return {
                "voiceSummary": f"Error: {run.status}",
                "displayResponse": f"Error: Run completed with status '{run.status}'"
            }
        except ValueError as e:
            logger.error(f"Configuration error: {str(e)}")
            # Pass through credential-related errors
            return {
                "voiceSummary": "Configuration Error",
                "displayResponse": f"Azure OpenAI Configuration Error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return {
                "voiceSummary": "Error processing request",
                "displayResponse": f"Error processing request: {str(e)}"
            }
    
    async def get_chat_response_stream(self, message: str, session_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Get a streaming chat response with typewriter effect while properly handling thread history.
        
        Args:
            message: The user message to process.
            session_id: Optional session identifier to maintain conversation state.
            
        Yields:
            Individual characters for typewriter effect.
            
        Raises:
            ValueError: If there's an issue with Azure OpenAI credentials.
            Exception: For other errors during processing.
        """
        try:
            logger.info(f"Processing streaming chat request with message: '{message[:20]}...' and session ID: {session_id}")
            start_time = asyncio.get_event_loop().time()
            
            # Get or create thread for this session
            thread = await self.get_or_create_thread(session_id)
            logger.info(f"Using thread ID for streaming: {thread.id}")
            
            # Get or create assistant for this thread
            assistant = await self.get_or_create_assistant(thread.id)
            logger.info(f"Using assistant ID for streaming: {assistant.id}")
            
            # Add user message to thread
            logger.info(f"Adding message to thread {thread.id}")
            user_message = await self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=message
            )
            user_message_id = user_message.id
            logger.info(f"Added user message with ID: {user_message_id}")
            
            # Run the thread
            logger.info(f"Starting thread run for streaming with thread ID {thread.id} and assistant ID {assistant.id}")
            run_start_time = asyncio.get_event_loop().time()
            run = await self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id
            )
            run_id = run.id
            logger.info(f"Run created for streaming with ID: {run_id}, initial status: {run.status}")
            
            # Get initial messages to establish baseline
            initial_messages = await self.client.beta.threads.messages.list(
                thread_id=thread.id,
                order="desc",
                limit=10
            )
            initial_message_ids = {msg.id for msg in initial_messages.data}
            
            # Track the accumulated response for detecting changes
            last_content_length = 0
            poll_count = 0
            content_updates = 0
            assistant_message_id = None
            
            # Wait for the run to complete
            while run.status in ["queued", "in_progress", "cancelling"]:
                poll_count += 1
                
                if run.status == "in_progress":
                    # Get the latest messages
                    logger.info(f"Polling for streaming content ({poll_count}) with run status: {run.status}")
                    messages = await self.client.beta.threads.messages.list(
                        thread_id=thread.id,
                        order="desc",
                        limit=10
                    )
                    
                    # Look for new assistant messages that weren't in our initial set
                    for msg in messages.data:
                        if msg.role == "assistant" and msg.id not in initial_message_ids:
                            # Found a new assistant message - likely our current response
                            if assistant_message_id is None or msg.id == assistant_message_id:
                                assistant_message_id = msg.id
                                if msg.content:
                                    try:
                                        current_content = msg.content[0].text.value
                                        
                                        # If we have new content
                                        if len(current_content) > last_content_length:
                                            content_updates += 1
                                            logger.info(f"Content update #{content_updates}: New content available (+{len(current_content) - last_content_length} chars) from message {msg.id}")
                                            
                                            # Get only the new characters (the delta)
                                            new_text = current_content[last_content_length:]
                                            
                                            # Update for next check
                                            last_content_length = len(current_content)
                                            
                                            # Stream character by character for typewriter effect
                                            for char in new_text:
                                                yield char
                                                # Brief pause between characters for typewriter effect
                                                await asyncio.sleep(0.01)
                                            
                                    except (AttributeError, IndexError) as e:
                                        logger.error(f"Error processing streaming content: {str(e)}")
                                    break  # Found our message, no need to check others
                
                # Short interval for responsive polling but not too frequent
                await asyncio.sleep(0.3)
                run = await self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            run_duration = asyncio.get_event_loop().time() - run_start_time
            logger.info(f"Run completed with status {run.status} after {run_duration:.2f} seconds, {poll_count} polls, and {content_updates} content updates")
            
            if run.status == "completed":
                # Get final response
                logger.info("Getting final content for streaming response")
                messages = await self.client.beta.threads.messages.list(
                    thread_id=thread.id,
                    order="desc",
                    limit=10
                )
                
                # Find the latest assistant message
                assistant_message = None
                for msg in messages.data:
                    if msg.role == "assistant" and (assistant_message_id is None or msg.id == assistant_message_id):
                        assistant_message = msg
                        break
                
                if assistant_message and assistant_message.content:
                    try:
                        final_content = assistant_message.content[0].text.value
                        # Check if there's any remaining content we haven't sent yet
                        remaining = final_content[last_content_length:]
                        if remaining:
                            logger.info(f"Sending remaining {len(remaining)} characters")
                            # Character by character streaming for remaining content
                            for char in remaining:
                                yield char
                                # Brief pause between characters
                                await asyncio.sleep(0.01)
                    except (AttributeError, IndexError) as e:
                        logger.error(f"Error processing final streaming content: {str(e)}")
                else:
                    logger.warning("No assistant message found in thread for final streaming content")
            else:
                # If run failed, yield an error message character by character
                error_json = json.dumps({
                    "voiceSummary": f"Error: {run.status}",
                    "displayResponse": f"Error: Run completed with status '{run.status}'"
                })
                logger.error(f"Stream failed with status: {run.status}")
                for char in error_json:
                    yield char
                    await asyncio.sleep(0.01)
                
            total_duration = asyncio.get_event_loop().time() - start_time
            logger.info(f"Total streaming request took {total_duration:.2f} seconds")
                
        except ValueError as e:
            # For credential-related errors - send as formatted JSON error
            logger.error(f"Configuration error in streaming: {str(e)}")
            error_json = json.dumps({
                "voiceSummary": "Configuration Error",
                "displayResponse": f"Azure OpenAI Configuration Error: {str(e)}"
            })
            for char in error_json:
                yield char
                await asyncio.sleep(0.01)
        except Exception as e:
            # For other errors - send as formatted JSON error
            logger.error(f"Unexpected error in streaming: {str(e)}", exc_info=True)
            error_json = json.dumps({
                "voiceSummary": "Error processing request",
                "displayResponse": f"Error processing request: {str(e)}"
            })
            for char in error_json:
                yield char
                await asyncio.sleep(0.01)
                
    # Helper method to cleanup a session when it's done
    async def cleanup_session(self, session_id: str) -> bool:
        """Cleanup resources associated with a session.
        
        Args:
            session_id: The session ID to cleanup.
            
        Returns:
            True if successful, False otherwise.
        """
        if session_id in self.sessions:
            thread_id = self.sessions[session_id]
            
            # Remove the assistant if it exists
            if thread_id in self.assistants:
                del self.assistants[thread_id]
            
            # Remove the session
            del self.sessions[session_id]
            return True
            
        return False


# Create a service instance to be used throughout the application
try:
    openai_service = AzureOpenAIService()
except ValueError as e:
    print(f"Warning: Azure OpenAI service initialization failed: {e}")
    # Still create the service, but it will raise errors when methods are called
    openai_service = None