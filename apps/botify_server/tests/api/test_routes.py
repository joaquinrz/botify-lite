import json
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.openai_service import AzureOpenAIService


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_openai_service():
    """Mock the OpenAI service for testing."""
    with patch('app.api.routes.openai_service') as mock_service:
        yield mock_service


def test_root_endpoint(client):
    """Test the root endpoint returns the correct response."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Botify Assistant API is running"}


def test_health_check(client):
    """Test the health check endpoint returns the correct response."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_chat_endpoint(client, mock_openai_service):
    """Test the non-streaming chat endpoint."""
    # Mock the get_chat_response method
    mock_response = {
        "voiceSummary": "This is a voice summary",
        "displayResponse": "This is a detailed display response"
    }
    mock_openai_service.get_chat_response = AsyncMock(return_value=mock_response)
    
    # Make a request to the chat endpoint
    response = client.post(
        "/api/chat",
        json={"message": "Hello, how are you?"}
    )
    
    # Check the response
    assert response.status_code == 200
    assert response.json() == mock_response
    
    # Verify the mock was called with the correct argument - now expecting session_id=None
    mock_openai_service.get_chat_response.assert_called_once_with("Hello, how are you?", session_id=None)


def test_chat_stream_endpoint(client, mock_openai_service):
    """Test the streaming chat endpoint."""
    # Mock the get_chat_response_stream method with support for session_id parameter
    async def mock_stream_generator(message, session_id=None):
        yield "Chunk 1"
        yield "Chunk 2"
        yield "Chunk 3"
    
    mock_openai_service.get_chat_response_stream = mock_stream_generator
    
    # Make a request to the streaming chat endpoint
    with client.stream("POST", "/api/chat/stream", json={"message": "Hello, stream response please"}) as response:
        # Check the response status and headers
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        
        # Read the stream content and convert to a string
        content = b''
        for chunk in response.iter_raw():
            content += chunk
        
        # Convert to string and check if our expected chunks are in the response
        content_str = content.decode('utf-8')
        assert "Chunk 1" in content_str
        assert "Chunk 2" in content_str
        assert "Chunk 3" in content_str


def test_chat_endpoint_error(client, mock_openai_service):
    """Test the chat endpoint handles errors properly."""
    # Mock the get_chat_response method to raise an exception
    mock_openai_service.get_chat_response = AsyncMock(side_effect=Exception("Test error"))
    
    # Make a request to the chat endpoint
    response = client.post(
        "/api/chat",
        json={"message": "This will cause an error"}
    )
    
    # Check the response
    assert response.status_code == 500
    assert "Test error" in response.json()["detail"]