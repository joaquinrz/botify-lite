import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, Any
from sse_starlette.sse import EventSourceResponse

from ..services.openai_service import openai_service
from ..services.content_safety_service import content_safety_service

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    """Request model for chat endpoints."""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoints."""
    voiceSummary: str
    displayResponse: str


class SessionRequest(BaseModel):
    """Request model for session management."""
    session_id: str


async def _check_service_availability() -> Optional[ChatResponse]:
    """Helper function to check if the OpenAI service is available."""
    if openai_service is None:
        return ChatResponse(
            voiceSummary="Configuration Error",
            displayResponse="Azure OpenAI service is not properly configured. Please check your credentials.env file."
        )
    return None

async def _check_content_safety(message: str) -> Dict[str, Any]:
    """
    Helper function to check content safety.
    
    Returns:
        Dict with keys:
        - is_safe: bool - Whether the content is safe
        - response: Optional[ChatResponse] - Response to return if content is not safe, None if safe
    """
    # Check content safety
    is_safe, reasons = await content_safety_service.is_safe_content(message)
    
    if is_safe:
        return {"is_safe": True, "response": None}
    
    # Content is not safe, prepare appropriate response
    is_jailbreak = any("Jailbreak attempt" in reason for reason in reasons)
    
    if is_jailbreak:
        # Specific message for jailbreak attempts
        response = ChatResponse(
            voiceSummary="Jailbreak Attempt Detected",
            displayResponse="Your message was not processed as it appears to be attempting to manipulate the AI system"
        )
    else:
        # General message for other harmful content
        response = ChatResponse(
            voiceSummary="Content Safety Alert",
            displayResponse=f"Your message was not processed for safety reasons: {'; '.join(reasons)}"
        )
    
    return {"is_safe": False, "response": response}

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Non-streaming chat endpoint.
    
    Args:
        request: The chat request containing the message and optional session_id
        
    Returns:
        ChatResponse: The response from the Azure OpenAI API
    """
    # Check service availability
    service_error = await _check_service_availability()
    if service_error:
        return service_error
    
    try:
        # Check content safety
        safety_check = await _check_content_safety(request.message)
        if not safety_check["is_safe"]:
            return safety_check["response"]
            
        # If content is safe, pass the session_id to the service
        response = await openai_service.get_chat_response(request.message, session_id=request.session_id)
        return response
    except Exception as e:
        error_message = str(e)
        if "API key" in error_message or "endpoint" in error_message:
            # More user-friendly message for credential errors
            return ChatResponse(
                voiceSummary="Configuration Error",
                displayResponse=f"Azure OpenAI Configuration Error: {error_message}"
            )
        else:
            raise HTTPException(status_code=500, detail=f"Error processing chat: {error_message}")


async def _create_error_stream(message: str):
    """Helper function to create a simple error stream."""
    async def error_stream():
        yield message
    return error_stream


async def _create_response_stream(response: ChatResponse):
    """Helper function to create a stream from a ChatResponse."""
    async def response_stream():
        yield json.dumps({
            "voiceSummary": response.voiceSummary,
            "displayResponse": response.displayResponse
        })
    return response_stream


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events.
    
    Args:
        request: The chat request containing the message and optional session_id
        
    Returns:
        EventSourceResponse: A streaming response with chat tokens
    """
    # Check service availability
    service_error = await _check_service_availability()
    if service_error:
        error_stream = await _create_error_stream(
            f"Configuration Error: {service_error.displayResponse}"
        )
        return EventSourceResponse(error_stream())
    
    try:
        # Check content safety
        safety_check = await _check_content_safety(request.message)
        if not safety_check["is_safe"]:
            response = safety_check["response"]
            response_stream = await _create_response_stream(response)
            return EventSourceResponse(response_stream())
            
        # If content is safe, pass the session_id to the service
        return EventSourceResponse(
            openai_service.get_chat_response_stream(
                request.message, 
                session_id=request.session_id
            )
        )
    except Exception as e:
        error_message = str(e)
        
        if "API key" in error_message or "endpoint" in error_message:
            # More user-friendly message for credential errors
            message = f"Configuration Error: Azure OpenAI Configuration Error: {error_message}"
        else:
            message = f"Error processing streaming chat: {error_message}"
        
        error_stream = await _create_error_stream(message)
        return EventSourceResponse(error_stream())


@router.post("/session/cleanup")
async def cleanup_session(request: SessionRequest):
    """
    Cleanup session resources.
    
    Args:
        request: The session request containing the session_id to clean up
        
    Returns:
        dict: Status of the cleanup operation
    """
    # Check service availability using our helper function
    service_error = await _check_service_availability()
    if service_error:
        raise HTTPException(
            status_code=503, 
            detail="Azure OpenAI service is not properly configured. Please check your credentials.env file."
        )
        
    try:
        success = await openai_service.cleanup_session(request.session_id)
        if success:
            return {"status": "success", "message": f"Session {request.session_id} cleaned up successfully"}
        else:
            return {"status": "not_found", "message": f"Session {request.session_id} not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up session: {str(e)}")