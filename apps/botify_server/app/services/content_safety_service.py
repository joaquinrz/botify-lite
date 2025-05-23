import asyncio
import json
import time
import httpx
from typing import Dict, Any, Tuple, List
from ..core.config import settings
import structlog

# Import telemetry components
from opentelemetry import trace
from ..telemetry.decorators import traced, content_safety_telemetry

# Set up structured logging
logger = structlog.get_logger(__name__)

class ContentSafetyService:
    """
    Service for content safety checking using Azure Content Safety API.
    
    This service performs two safety checks in parallel:
    1. Shield Prompt - to detect potentially harmful prompts
    2. Harmful Text Analysis - to analyze content for harmful categories
    """
    
    def __init__(self):
        """Initialize the content safety service."""
        # Build API endpoints
        api_version = f"?api-version={settings.content_safety_api_version}"
        base_endpoint = settings.content_safety_endpoint
        
        self.prompt_shield_endpoint = f"{base_endpoint}contentsafety/text:shieldPrompt{api_version}"
        self.harmful_text_analysis_endpoint = f"{base_endpoint}contentsafety/text:analyze{api_version}"
        
        # API headers
        self.headers = {
            "Ocp-Apim-Subscription-Key": settings.content_safety_key,
            "Content-Type": "application/json",
        }
    
    @content_safety_telemetry
    async def check_content_safety(self, message: str) -> Dict[str, Any]:
        """
        Check if the content is safe using Azure Content Safety API.
        
        Args:
            message: The message to check
            
        Returns:
            A dictionary with the safety check result
        """
        # Log the message being checked (truncated for privacy)
        logger.debug("message.safety_check")
        
        try:
            # Prepare request payloads
            shield_payload = {"userPrompt": message, "documents": None}
            harmful_payload = {"text": message}
            
            # Create a client with retry capability and reasonable timeout
            async with httpx.AsyncClient(
                transport=httpx.AsyncHTTPTransport(retries=3),
                timeout=10.0
            ) as client:
                # Run both checks concurrently
                shield_response, harmful_response = await asyncio.gather(
                    self._make_api_request(client, "shield", self.prompt_shield_endpoint, shield_payload),
                    self._make_api_request(client, "harmful", self.harmful_text_analysis_endpoint, harmful_payload),
                    return_exceptions=True
                )
                
                # Process responses to JSON, handling exceptions
                shield_data = self._process_response(shield_response, "shield")
                harmful_data = self._process_response(harmful_response, "content analysis")
            
            # Analyze the safety responses
            result = self._analyze_safety_responses(shield_data, harmful_data, message)
            
            return result
            
        except httpx.TimeoutException:
            logger.error("Content safety API request timed out")
            return {
                "is_safe": False,
                "detected_terms": ["Content safety service timeout"],
                "message": "Content safety check timed out. Request cannot be processed."
            }
        except Exception as e:
            logger.error(f"Content safety API error: {e}")
            return {
                "is_safe": False,
                "detected_terms": ["Content safety service error"],
                "message": f"Content safety check failed: {str(e)}"
            }
    
    def _process_response(self, response, api_name: str) -> Dict:
        """Convert API response to JSON, handling any errors."""
        if isinstance(response, Exception):
            logger.error(f"Error in {api_name} request: {str(response)}")
            return {"error": str(response)}
        
        try:
            data = response.json()
            logger.debug(f"{api_name} response: {json.dumps(data)}")
            return data
        except Exception as e:
            logger.error(f"Error parsing {api_name} response: {str(e)}")
            return {"error": f"Failed to parse API response: {str(e)}"}
    
    def _analyze_safety_responses(self, shield_response: Dict, harmful_response: Dict, message: str) -> Dict[str, Any]:
        """
        Process and combine the responses from both safety checks.
        
        Returns:
            Dictionary with safety analysis results: is_safe, detected_terms, and message
        """
        detected_issues = []
        messages = []
        api_error = False
        
        # Check for API errors in either response
        for response, name in [(shield_response, "Shield"), (harmful_response, "Content analysis")]:
            if "error" in response:
                logger.warning(f"{name} error: {response['error']}")
                messages.append(f"{name} error: {response['error']}")
                if "Content safety service error" not in detected_issues:
                    detected_issues.append("Content safety service error")
                api_error = True
                
        if api_error:
            # Add "check failed" to the message for API errors - needed for tests
            messages.append("check failed")
        
        if not api_error:
            # Check for jailbreak attempts in shield response
            if "userPromptAnalysis" in shield_response:
                if shield_response.get("userPromptAnalysis", {}).get("attackDetected", False):
                    detected_issues.append("jailbreak")
                    messages.append("Detected potential jailbreak attempt")
                    # Log a clear message for potential jailbreak attempt
                    logger.warning(
                        "Detected potential jailbreak attempt",
                        event_type="jailbreak_attempt_detected",
                        is_safe=False,
                        message_content=message[:500] if len(message) > 500 else message
                    )
            
            # Check for harmful content in content analysis response
            if "categoriesAnalysis" in harmful_response:
                for category in harmful_response["categoriesAnalysis"]:
                    if category.get("severity", 0) >= 2:  # Moderate to high severity
                        category_name = category.get("category", "unknown")
                        detected_issues.append(category_name)
                        messages.append(f"Content may be {category_name}")
                        # Log a clear message for harmful content detection
                        logger.warning(
                            f"Harmful content detected: {category_name}",
                            event_type="harmful_content_detected",
                            category=category_name,
                            severity=category.get("severity", 0),
                            detected_issues=detected_issues,
                            message_content=message[:500] if len(message) > 500 else message
                        )
        
        # Content is safe only if no issues were detected and no API errors occurred
        is_safe = not detected_issues and not api_error
        message = "Content is safe" if is_safe else ". ".join(messages)
        
        # Include exactly "check failed" text in the message for API errors (needed for tests)
        if api_error:
            message = f"{message}. Content safety check failed"
        
        return {
            "is_safe": is_safe,
            "detected_terms": detected_issues,
            "message": message
        }
    
    async def is_safe_content(self, message: str) -> Tuple[bool, List[str]]:
        """
        Check if content is safe and return a tuple of (is_safe, reasons).
        This method is the main entry point used by the API routes.
        
        Args:
            message: The message to check
            
        Returns:
            A tuple containing (is_safe, reasons)
        """
        if not settings.content_safety_key or not settings.content_safety_endpoint:
            logger.warning("safety.credentials_missing")
            return True, []
            
        result = await self.check_content_safety(message)
        return result["is_safe"], result["detected_terms"]
    
    @traced(
        name="content_safety.api_request",
        attributes={"component": "content_safety_service", "api_type": "azure_content_safety"}
    )
    async def _make_api_request(self, client, check_type, endpoint, payload):
        """
        Make an API request with tracing.
        
        Args:
            client: The HTTPX client to use
            check_type: The type of check (shield or harmful)
            endpoint: The API endpoint
            payload: The request payload
            
        Returns:
            The API response
        """
        # Add additional attributes to the current span created by the decorator
        span = trace.get_current_span()
        if span:
            # Add HTTP details
            span.set_attribute("http.url", endpoint)
            span.set_attribute("http.method", "POST")
            span.set_attribute("request.size", len(json.dumps(payload)))
            
            # Add content safety specific attributes
            span.set_attribute("content_safety.check_type", check_type)

        # Make the API request
        response = await client.post(endpoint, json=payload, headers=self.headers)
        
        # Record response details in span if it exists
        if span and response:
            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("response.size", len(response.content))
            
        return response


# Create a service instance to be used throughout the application
content_safety_service = ContentSafetyService()
