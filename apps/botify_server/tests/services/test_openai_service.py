import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import asyncio

from app.services.openai_service import AzureOpenAIService


@pytest.fixture
def openai_service():
    """Create an AzureOpenAIService instance for testing with mocked dependencies."""
    with patch('app.services.openai_service.settings') as mock_settings, \
         patch('app.services.openai_service.AsyncAzureOpenAI') as mock_openai, \
         patch('app.services.openai_service.os.path.exists', return_value=True), \
         patch('builtins.open', MagicMock()):
        
        # Configure mock settings
        mock_settings.azure_openai_endpoint = "https://fake-endpoint.openai.azure.com/"
        mock_settings.azure_openai_api_key = "fake-key"
        mock_settings.azure_openai_api_version = "2024-05-01-preview"
        mock_settings.model_name = "gpt-4o-mini"
        mock_settings.vector_store_id = "fake-vector-store-id"
        
        # Configure validation results
        mock_settings.validate_service_config.return_value = {"configured": True, "missing": []}
        
        # Configure the mock client
        mock_instance = mock_openai.return_value
        mock_instance.beta = MagicMock()
        mock_instance.beta.threads = MagicMock()
        mock_instance.beta.threads.create = AsyncMock()
        mock_instance.beta.threads.messages = MagicMock()
        mock_instance.beta.threads.messages.create = AsyncMock()
        mock_instance.beta.threads.messages.list = AsyncMock()
        mock_instance.beta.threads.runs = MagicMock()
        mock_instance.beta.threads.runs.create = AsyncMock()
        mock_instance.beta.threads.runs.retrieve = AsyncMock()
        mock_instance.beta.assistants = MagicMock()
        mock_instance.beta.assistants.create = AsyncMock()
        
        # Create service instance
        service = AzureOpenAIService()
        service.client = mock_instance
        
        yield service


@pytest.mark.asyncio
async def test_create_assistant(openai_service):
    """Test create_assistant method."""
    mock_assistant = MagicMock()
    mock_assistant.id = "assistant_123"
    openai_service.client.beta.assistants.create.return_value = mock_assistant
    
    result = await openai_service.create_assistant()
    
    # Verify the assistant was created with the correct parameters
    openai_service.client.beta.assistants.create.assert_called_once()
    call_kwargs = openai_service.client.beta.assistants.create.call_args.kwargs
    assert call_kwargs["model"] == openai_service.model_name
    assert call_kwargs["instructions"] == openai_service.assistant_instructions
    assert call_kwargs["tools"] == [{"type": "file_search"}]
    assert call_kwargs["tool_resources"]["file_search"]["vector_store_ids"] == [openai_service.vector_store_id]
    assert result == mock_assistant


@pytest.mark.asyncio
async def test_get_or_create_thread_new(openai_service):
    """Test get_or_create_thread creates a new thread when session ID doesn't exist."""
    # Set up mock return values
    mock_thread = MagicMock()
    mock_thread.id = "thread_123"
    openai_service.client.beta.threads.create.return_value = mock_thread
    
    # Call the method with a new session ID
    result = await openai_service.get_or_create_thread("new_session")
    
    # Verify a new thread was created
    openai_service.client.beta.threads.create.assert_called_once()
    assert result == mock_thread
    assert openai_service.sessions["new_session"] == "thread_123"


@pytest.mark.asyncio
async def test_get_or_create_thread_existing(openai_service):
    """Test get_or_create_thread returns existing thread when session ID exists."""
    # Set up an existing session/thread mapping
    openai_service.sessions = {"existing_session": "thread_456"}
    
    # Call the method with an existing session ID
    result = await openai_service.get_or_create_thread("existing_session")
    
    # Verify no new thread was created
    openai_service.client.beta.threads.create.assert_not_called()
    assert result.id == "thread_456"


@pytest.mark.asyncio
async def test_get_or_create_assistant_new(openai_service):
    """Test get_or_create_assistant creates a new assistant when thread doesn't have one."""
    # Set up mock return values
    mock_assistant = MagicMock()
    mock_assistant.id = "assistant_789"
    
    # Mock the create_assistant method
    openai_service.create_assistant = AsyncMock(return_value=mock_assistant)
    
    # Call the method with a new thread ID
    result = await openai_service.get_or_create_assistant("thread_new")
    
    # Verify a new assistant was created
    openai_service.create_assistant.assert_called_once()
    assert result == mock_assistant
    assert openai_service.assistants["thread_new"] == "assistant_789"


@pytest.mark.asyncio
async def test_get_or_create_assistant_existing(openai_service):
    """Test get_or_create_assistant returns existing assistant when thread has one."""
    # Set up an existing thread/assistant mapping
    openai_service.assistants = {"thread_existing": "assistant_101"}
    
    # Mock the create_assistant method to track if it's called
    openai_service.create_assistant = AsyncMock()
    
    # Call the method with an existing thread ID
    result = await openai_service.get_or_create_assistant("thread_existing")
    
    # Verify no new assistant was created
    assert not openai_service.create_assistant.called
    assert result.id == "assistant_101"


@pytest.mark.asyncio
async def test_add_message_to_thread(openai_service):
    """Test add_message_to_thread method."""
    mock_message = MagicMock()
    openai_service.client.beta.threads.messages.create.return_value = mock_message
    
    result = await openai_service.add_message_to_thread("thread_123", "Hello, world!")
    
    # Verify the message was created with the correct parameters
    openai_service.client.beta.threads.messages.create.assert_called_once_with(
        thread_id="thread_123",
        role="user",
        content="Hello, world!"
    )
    assert result == mock_message


@pytest.mark.asyncio
async def test_run_thread(openai_service):
    """Test run_thread method."""
    mock_run = MagicMock()
    openai_service.client.beta.threads.runs.create.return_value = mock_run
    
    result = await openai_service.run_thread("thread_123", "assistant_456")
    
    # Verify the run was created with the correct parameters
    openai_service.client.beta.threads.runs.create.assert_called_once_with(
        thread_id="thread_123",
        assistant_id="assistant_456"
    )
    assert result == mock_run


@pytest.mark.asyncio
async def test_poll_run_status_completed_immediately(openai_service):
    """Test poll_run_status when run completes immediately."""
    # Create a mock run object with status "completed"
    mock_run = MagicMock()
    mock_run.status = "completed"
    openai_service.client.beta.threads.runs.retrieve.return_value = mock_run
    
    result = await openai_service.poll_run_status("thread_123", "run_789")
    
    # Verify the run status was retrieved once and returned
    openai_service.client.beta.threads.runs.retrieve.assert_called_once_with(
        thread_id="thread_123",
        run_id="run_789"
    )
    assert result == mock_run
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_poll_run_status_eventually_completed(openai_service):
    """Test poll_run_status when run eventually completes."""
    # Create mock runs with different statuses for sequential calls
    mock_run_queued = MagicMock()
    mock_run_queued.status = "queued"
    
    mock_run_in_progress = MagicMock()
    mock_run_in_progress.status = "in_progress"
    
    mock_run_completed = MagicMock()
    mock_run_completed.status = "completed"
    
    # Setup the retrieve method to return different values on sequential calls
    openai_service.client.beta.threads.runs.retrieve.side_effect = [
        mock_run_queued, mock_run_in_progress, mock_run_completed
    ]
    
    # Patch asyncio.sleep to avoid actual waiting
    with patch('asyncio.sleep', AsyncMock()):
        result = await openai_service.poll_run_status("thread_123", "run_789")
    
    # Verify the run status was retrieved multiple times
    assert openai_service.client.beta.threads.runs.retrieve.call_count == 3
    assert result == mock_run_completed
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_get_messages(openai_service):
    """Test get_messages method."""
    # Mock the return value of the list method
    mock_response = MagicMock()
    mock_response.data = ["message1", "message2"]
    openai_service.client.beta.threads.messages.list.return_value = mock_response
    
    result = await openai_service.get_messages("thread_123", order="desc", limit=5)
    
    # Verify the messages were retrieved with the correct parameters
    openai_service.client.beta.threads.messages.list.assert_called_once_with(
        thread_id="thread_123",
        order="desc",
        limit=5
    )
    assert result == ["message1", "message2"]


@pytest.mark.asyncio
async def test_get_chat_response(openai_service):
    """Test get_chat_response method."""
    # Mock the various components needed for the test
    thread_mock = MagicMock()
    thread_mock.id = "thread_123"
    
    assistant_mock = MagicMock()
    assistant_mock.id = "assistant_456"
    
    run_mock = MagicMock()
    run_mock.id = "run_789"
    run_mock.status = "completed"
    
    message_mock = MagicMock()
    message_mock.role = "assistant"
    message_mock.id = "message_101"
    message_mock.content = [MagicMock()]
    message_mock.content[0].text.value = '{"voiceSummary": "Hello", "displayResponse": "Hello, world!"}'
    
    # Set up the mocks for method calls
    openai_service._setup_thread_for_chat = AsyncMock(return_value=(thread_mock, assistant_mock, {"old_message_id"}))
    openai_service.run_thread = AsyncMock(return_value=run_mock)
    openai_service.poll_run_status = AsyncMock(return_value=run_mock)
    openai_service.get_messages = AsyncMock(return_value=[message_mock])
    openai_service.find_assistant_message = AsyncMock(return_value=message_mock)
    
    # Call the method
    result = await openai_service.get_chat_response("Hello, AI!", session_id="test_session")
    
    # Verify all the expected method calls
    openai_service._setup_thread_for_chat.assert_called_once_with("Hello, AI!", "test_session")
    openai_service.run_thread.assert_called_once_with("thread_123", "assistant_456")
    openai_service.poll_run_status.assert_called_once_with("thread_123", "run_789")
    openai_service.get_messages.assert_called_once_with("thread_123")
    openai_service.find_assistant_message.assert_called_once()
    
    # Verify the result
    assert result == {"voiceSummary": "Hello", "displayResponse": "Hello, world!"}


@pytest.mark.asyncio
async def test_get_chat_response_error_handling(openai_service):
    """Test get_chat_response error handling."""
    # Set up the mock to raise an exception
    openai_service._setup_thread_for_chat = AsyncMock(side_effect=ValueError("API configuration error"))
    
    # Call the method and check the error handling
    result = await openai_service.get_chat_response("Hello", "test_session")
    
    # Verify we got an error response
    assert "Configuration Error" in result["voiceSummary"]
    assert "API configuration error" in result["displayResponse"]


@pytest.mark.asyncio
async def test_stream_text_word_by_word(openai_service):
    """Test _stream_text_word_by_word helper."""
    # Patch asyncio.sleep to avoid actual waiting
    with patch('asyncio.sleep', AsyncMock()):
        # Collect all words yielded by the generator
        words = []
        async for word in openai_service._stream_text_word_by_word("Hello, world!"):
            words.append(word)
    
    # Verify the words were split correctly
    assert "Hello," in words
    assert "world!" in words
    assert len(words) == 2  # Two words with punctuation


@pytest.mark.asyncio
async def test_cleanup_session_existing(openai_service):
    """Test cleanup_session with an existing session."""
    # Set up test data
    openai_service.sessions = {"test_session": "thread_123"}
    openai_service.assistants = {"thread_123": "assistant_456"}
    
    # Call the method
    result = await openai_service.cleanup_session("test_session")
    
    # Verify the result and state changes
    assert result is True
    assert "test_session" not in openai_service.sessions
    assert "thread_123" not in openai_service.assistants


@pytest.mark.asyncio
async def test_cleanup_session_nonexistent(openai_service):
    """Test cleanup_session with a non-existent session."""
    # Set up test data (empty)
    openai_service.sessions = {}
    
    # Call the method
    result = await openai_service.cleanup_session("nonexistent_session")
    
    # Verify the result
    assert result is False
