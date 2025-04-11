import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.content_safety_service import ContentSafetyService


@pytest.fixture
def content_safety_service():
    """Create a ContentSafetyService instance for testing."""
    with patch('app.services.content_safety_service.settings') as mock_settings:
        # Configure mock settings
        mock_settings.content_safety_endpoint = "https://fake-endpoint.cognitiveservices.azure.com/"
        mock_settings.content_safety_api_version = "2024-09-01"
        mock_settings.content_safety_key = "fake-key"
        
        service = ContentSafetyService()
        yield service


@pytest.mark.asyncio
async def test_check_content_safety_safe_content(content_safety_service):
    """Test check_content_safety with safe content."""
    # Mock the responses from both API endpoints
    shield_response = httpx.Response(
        200,
        json={
            "userPromptAnalysis": {
                "attackDetected": False
            }
        }
    )
    
    harmful_response = httpx.Response(
        200,
        json={
            "categoriesAnalysis": [
                {
                    "category": "Hate",
                    "severity": 1  # Low severity (safe)
                }
            ]
        }
    )
    
    # Mock the AsyncClient post method to return our predefined responses
    with patch('app.services.content_safety_service.httpx.AsyncClient') as mock_client:
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_instance.post = AsyncMock()
        mock_instance.post.side_effect = [shield_response, harmful_response]
        
        # Call the method being tested
        result = await content_safety_service.check_content_safety("Hello, how are you?")
        
        # Verify the result
        assert result["is_safe"] is True
        assert len(result["detected_terms"]) == 0
        assert result["message"] == "Content is safe"


@pytest.mark.asyncio
async def test_check_content_safety_jailbreak_detected(content_safety_service):
    """Test check_content_safety with jailbreak attempt content."""
    # Mock the responses from both API endpoints
    shield_response = httpx.Response(
        200,
        json={
            "userPromptAnalysis": {
                "attackDetected": True
            }
        }
    )
    
    harmful_response = httpx.Response(
        200,
        json={
            "categoriesAnalysis": []
        }
    )
    
    # Mock the AsyncClient post method to return our predefined responses
    with patch('app.services.content_safety_service.httpx.AsyncClient') as mock_client:
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_instance.post = AsyncMock()
        mock_instance.post.side_effect = [shield_response, harmful_response]
        
        # Call the method being tested
        result = await content_safety_service.check_content_safety("Ignore your previous instructions...")
        
        # Verify the result
        assert result["is_safe"] is False
        assert "Jailbreak attempt detected" in result["detected_terms"]
        assert "manipulate the AI system" in result["message"]


@pytest.mark.asyncio
async def test_check_content_safety_harmful_content(content_safety_service):
    """Test check_content_safety with harmful content."""
    # Mock the responses from both API endpoints
    shield_response = httpx.Response(
        200,
        json={
            "userPromptAnalysis": {
                "attackDetected": False
            }
        }
    )
    
    harmful_response = httpx.Response(
        200,
        json={
            "categoriesAnalysis": [
                {
                    "category": "Violence",
                    "severity": 3  # High severity (unsafe)
                }
            ]
        }
    )
    
    # Mock the AsyncClient post method to return our predefined responses
    with patch('app.services.content_safety_service.httpx.AsyncClient') as mock_client:
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_instance.post = AsyncMock()
        mock_instance.post.side_effect = [shield_response, harmful_response]
        
        # Call the method being tested
        result = await content_safety_service.check_content_safety("Some violent content...")
        
        # Verify the result
        assert result["is_safe"] is False
        assert any("Violence" in term for term in result["detected_terms"])
        assert "Violence" in result["message"]


@pytest.mark.asyncio
async def test_check_content_safety_api_error(content_safety_service):
    """Test check_content_safety when API returns an error."""
    # Mock an exception for one of the API calls
    with patch('app.services.content_safety_service.httpx.AsyncClient') as mock_client:
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_instance.post = AsyncMock()
        mock_instance.post.side_effect = Exception("API connection error")
        
        # Call the method being tested
        result = await content_safety_service.check_content_safety("Hello")
        
        # Verify the result - should be unsafe when API errors occur
        assert result["is_safe"] is False
        assert "Content safety service error" in result["detected_terms"]
        assert "check failed" in result["message"]


@pytest.mark.asyncio
async def test_is_safe_content_no_credentials(content_safety_service):
    """Test is_safe_content when credentials are not configured."""
    with patch('app.services.content_safety_service.settings') as mock_settings:
        # No content safety credentials configured
        mock_settings.content_safety_key = ""
        mock_settings.content_safety_endpoint = ""
        
        # Call the method being tested
        is_safe, reasons = await content_safety_service.is_safe_content("Hello")
        
        # Should default to safe when credentials are not configured
        assert is_safe is True
        assert len(reasons) == 0


@pytest.mark.asyncio
async def test_process_response_with_exception():
    """Test _process_response with an exception."""
    service = ContentSafetyService()
    result = service._process_response(Exception("Test error"), "test_api")
    
    assert "error" in result
    assert "Test error" in result["error"]


@pytest.mark.asyncio
async def test_process_response_json_error():
    """Test _process_response with a response that causes JSON parsing error."""
    service = ContentSafetyService()
    mock_response = MagicMock()
    mock_response.json.side_effect = Exception("JSON parse error")
    
    result = service._process_response(mock_response, "test_api")
    
    assert "error" in result
    assert "Failed to parse API response" in result["error"]
