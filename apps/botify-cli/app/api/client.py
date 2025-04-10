import json
import logging
from typing import Dict, Generator, Any, Optional
import requests
import sseclient
from requests.exceptions import RequestException, ConnectionError, Timeout
import uuid

from ..core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class APIClient:
    """Client for communicating with the backend API server."""
    
    def __init__(self, base_url: Optional[str] = None):
        """Initialize the API client.
        
        Args:
            base_url: Optional override for the API base URL.
        """
        self.base_url = base_url or settings.api_base_url
        self.session_id = str(uuid.uuid4())
        logger.info(f"Initialized API client with base URL: {self.base_url} and session ID: {self.session_id}")
    
    def chat(self, message: str) -> Dict[str, str]:
        """Send a message to the chat API (non-streaming).
        
        Args:
            message: The message to send to the chat API.
            
        Returns:
            A dictionary containing the chat response.
            
        Raises:
            ConnectionError: If the backend server is unavailable.
            Timeout: If the request times out.
            RequestException: If there is an error with the request.
        """
        try:
            url = f"{self.base_url}/api/chat"
            logger.debug(f"Sending POST request to {url} with session ID: {self.session_id}")
            
            response = requests.post(
                url, 
                json={"message": message, "session_id": self.session_id}, 
                timeout=120  # Increased timeout to 2 minutes
            )
            logger.debug(f"Received response with status code: {response.status_code}")
            response.raise_for_status()
            return response.json()
        except ConnectionError as e:
            logger.error(f"Connection error: {str(e)}")
            return {
                "voiceSummary": "Connection Error",
                "displayResponse": f"Could not connect to backend server at {self.base_url}. Please ensure the server is running and accessible."
            }
        except Timeout as e:
            logger.error(f"Timeout error: {str(e)}")
            return {
                "voiceSummary": "Request Timeout",
                "displayResponse": f"The request to the backend server at {self.base_url} timed out after 120 seconds. The server might be overloaded or experiencing issues."
            }
        except RequestException as e:
            logger.error(f"Request exception: {str(e)}")
            if e.response is not None:
                # Try to extract error details if available
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get("detail", str(e))
                    return {
                        "voiceSummary": f"Error: {e.response.status_code}",
                        "displayResponse": f"Backend server error: {error_detail}"
                    }
                except (ValueError, AttributeError):
                    pass
            
            return {
                "voiceSummary": "Request Error",
                "displayResponse": f"Error communicating with backend server: {str(e)}"
            }
    
    def chat_stream(self, message: str) -> Generator[str, None, None]:
        """Send a message to the chat API and stream the response.
        
        Args:
            message: The message to send to the chat API.
            
        Yields:
            Chunks of the response as they arrive.
            
        Raises:
            ConnectionError: If the backend server is unavailable.
            Timeout: If the request times out.
            RequestException: If there is an error with the request.
        """
        try:
            url = f"{self.base_url}/api/chat/stream"
            logger.debug(f"Sending streaming POST request to {url} with session ID: {self.session_id}")
            
            response = requests.post(
                url, 
                json={"message": message, "session_id": self.session_id}, 
                stream=True, 
                timeout=180  # Increased timeout to 3 minutes for streaming
            )
            logger.debug(f"Received initial streaming response with status code: {response.status_code}")
            response.raise_for_status()
            
            client = sseclient.SSEClient(response)
            for event in client.events():
                if event.data:
                    # Pass through raw data directly without any processing
                    yield event.data
                    
        except ConnectionError as e:
            logger.error(f"Stream connection error: {str(e)}")
            yield f"Connection Error: Could not connect to backend server at {self.base_url}. Please ensure the server is running and accessible."
        except Timeout as e:
            logger.error(f"Stream timeout error: {str(e)}")
            yield f"Request Timeout: The request to the backend server at {self.base_url} timed out after 180 seconds. The server might be overloaded or experiencing issues."
        except RequestException as e:
            logger.error(f"Stream request exception: {str(e)}")
            yield f"Request Error: Error communicating with backend server: {str(e)}"


# Create a single instance of the API client
api_client = APIClient()