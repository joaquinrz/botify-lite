import pytest
import json
from unittest.mock import Mock, patch, ANY
from sseclient import Event

from app.api.client import APIClient


@pytest.fixture
def mock_response():
    """Mock response for non-streaming requests."""
    mock = Mock()
    mock.json.return_value = {
        "voiceSummary": "Test summary",
        "displayResponse": "Test detailed response"
    }
    mock.raise_for_status = Mock()
    return mock


@pytest.fixture
def mock_streaming_response():
    """Mock response for streaming requests."""
    mock = Mock()
    mock.raise_for_status = Mock()
    return mock


@pytest.fixture
def api_client():
    """Create an instance of the API client with a test base URL."""
    return APIClient(base_url="http://test-api")


def test_chat_endpoint(api_client, mock_response):
    """Test the chat endpoint (non-streaming)."""
    with patch('requests.post', return_value=mock_response) as mock_post:
        response = api_client.chat("Hello")
        
        # Check that the request was made with the right parameters
        # Use ANY for session_id since it's a UUID that changes each time
        mock_post.assert_called_once_with(
            "http://test-api/api/chat",
            json={"message": "Hello", "session_id": ANY},
            timeout=120
        )
        
        # Check that the response was parsed correctly
        assert response == {
            "voiceSummary": "Test summary",
            "displayResponse": "Test detailed response"
        }


def test_chat_stream_endpoint(api_client, mock_streaming_response):
    """Test the streaming chat endpoint."""
    # Create mock events that will be returned by SSEClient
    event1 = Mock(spec=Event)
    event1.data = '{"partial": "chunk1"}'
    
    event2 = Mock(spec=Event)
    event2.data = '{"partial": "chunk2"}'
    
    event3 = Mock(spec=Event)
    event3.data = '{"final": "complete"}'
    
    # Mock the SSEClient to return our mock events
    mock_client = Mock()
    mock_client.events.return_value = [event1, event2, event3]
    
    with patch('requests.post', return_value=mock_streaming_response) as mock_post, \
         patch('sseclient.SSEClient', return_value=mock_client) as mock_sse:
        
        # Call the streaming API
        chunks = list(api_client.chat_stream("Hello streaming"))
        
        # Check that the request was made with the right parameters
        # Use ANY for session_id since it's a UUID that changes each time
        mock_post.assert_called_once_with(
            "http://test-api/api/chat/stream",
            json={"message": "Hello streaming", "session_id": ANY},
            stream=True,
            timeout=180
        )
        
        # Check that SSEClient was constructed with our response
        mock_sse.assert_called_once_with(mock_streaming_response)
        
        # Check that we got all the chunks
        assert chunks == ['{"partial": "chunk1"}', '{"partial": "chunk2"}', '{"final": "complete"}']


def test_chat_error_handling(api_client):
    """Test error handling in the chat method."""
    with patch('requests.post', side_effect=Exception("Test error")) as mock_post:
        with pytest.raises(Exception) as excinfo:
            api_client.chat("This will fail")
        
        assert "Test error" in str(excinfo.value)