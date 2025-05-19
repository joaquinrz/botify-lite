"""Authentication module for the Botify Server API."""
import logging
import os
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer

# JWT validation
try:
    import jwt
    from jwt.exceptions import PyJWTError
    HAS_JWT = True
except ImportError:
    HAS_JWT = False
    logging.warning("PyJWT not installed. JWT validation will not be available.")

# Environment variables
ALLOW_ANONYMOUS = os.getenv("ALLOW_ANONYMOUS", "false").lower() == "true"
API_APP_ID = os.getenv("API_APP_ID")

# OAuth2 scheme
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="",  # Not used in this flow
    tokenUrl="",         # Not used in this flow
    auto_error=False
)

logger = logging.getLogger(__name__)

async def validate_token(token: str = Depends(oauth2_scheme)) -> Optional[Dict[str, Any]]:
    """
    Validate the access token.
    
    Args:
        token: The OAuth2 access token
        
    Returns:
        The decoded token payload if valid, None if token not provided and anonymous access is allowed
        
    Raises:
        HTTPException: If the token is invalid or missing (when anonymous access is disabled)
    """
    # Check if token is provided
    if not token:
        # Allow anonymous access if configured
        if ALLOW_ANONYMOUS:
            logger.debug("Anonymous access allowed")
            return None
        
        logger.warning("Authentication failed: No token provided and anonymous access is disabled")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate JWT token
    if not HAS_JWT:
        logger.error("PyJWT not installed but token validation requested")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server is not properly configured for authentication"
        )
    
    try:
        # In production, verify_signature should be True with proper jwks setup
        # For simplicity in development, we're skipping signature verification
        verify_signature = os.getenv("VERIFY_JWT_SIGNATURE", "false").lower() == "true"
        
        # Decode and validate the token
        payload = jwt.decode(
            token, 
            options={"verify_signature": verify_signature},
            audience=API_APP_ID
        )
        
        # Log success
        logger.debug("Token validated successfully")
        return payload
        
    except PyJWTError as e:
        logger.warning(f"Token validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
