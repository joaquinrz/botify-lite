import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from sse_starlette.sse import EventSourceResponse

from ..services.openai_service import openai_service

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    """Request model for chat endpoints."""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoints."""
    voiceSummary: str
    displayResponse: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Non-streaming chat endpoint.
    
    Args:
        request: The chat request containing the message and optional session_id
        
    Returns:
        ChatResponse: The response from the Azure OpenAI API
    """
    if openai_service is None:
        return ChatResponse(
            voiceSummary="Configuration Error",
            displayResponse="Azure OpenAI service is not properly configured. Please check your credentials.env file and ensure all required environment variables are set correctly."
        )
        
    try:
        # Pass the session_id to the service
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


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events.
    
    Args:
        request: The chat request containing the message and optional session_id
        
    Returns:
        EventSourceResponse: A streaming response with chat tokens
    """
    if openai_service is None:
        # Send a raw error message if the service is not properly configured
        async def error_stream():
            yield "Configuration Error: Azure OpenAI service is not properly configured. Please check your credentials.env file and ensure all required environment variables are set correctly."
            
        return EventSourceResponse(error_stream())
        
    try:
        # Pass the session_id to the service
        return EventSourceResponse(openai_service.get_chat_response_stream(request.message, session_id=request.session_id))
    except Exception as e:
        error_message = str(e)
        
        # Create an error stream generator with raw text error messages
        async def error_stream():
            if "API key" in error_message or "endpoint" in error_message:
                # More user-friendly message for credential errors
                yield f"Configuration Error: Azure OpenAI Configuration Error: {error_message}"
            else:
                yield f"Error processing streaming chat: {error_message}"
                
        return EventSourceResponse(error_stream())