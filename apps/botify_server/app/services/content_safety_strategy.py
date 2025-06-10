"""
Content safety strategy service for runtime switching between Azure Content Safety and NeMo Guardrails.
"""
import os
import time
from typing import Tuple, List, Optional
from enum import Enum
import structlog

from .content_safety_service import content_safety_service
from .nemo_guardrails_service import nemo_guardrails_service

logger = structlog.get_logger(__name__)


class ContentSafetyStrategy(Enum):
    """Enum for content safety strategies."""
    AZURE = "AZURE"
    NEMO = "NEMO"


class ContentSafetyStrategyService:
    """
    Service that manages content safety strategy switching at runtime.
    
    This service acts as a facade for different content safety implementations,
    allowing runtime switching based on the CONTENT_SAFETY_STRATEGY environment variable.
    """
    
    def __init__(self):
        """Initialize the strategy service."""
        self._cached_strategy = None
        self._last_check_time = 0
        self._cache_duration = 60  # Cache strategy for 60 seconds
        logger = structlog.get_logger(__name__)
        logger.info("Content safety strategy service initialized")

    def _get_strategy_from_env(self) -> ContentSafetyStrategy:
        """
        Get the content safety strategy from environment variable.
        
        Returns:
            ContentSafetyStrategy: The strategy to use (defaults to AZURE if not set or invalid)
        """
        strategy_env = os.getenv("CONTENT_SAFETY_STRATEGY", "AZURE").upper()
        
        try:
            return ContentSafetyStrategy(strategy_env)
        except ValueError:
            logger.warning(
                f"Invalid CONTENT_SAFETY_STRATEGY value: {strategy_env}. "
                f"Valid values are: {', '.join([s.value for s in ContentSafetyStrategy])}. "
                f"Defaulting to AZURE."
            )
            return ContentSafetyStrategy.AZURE

    def get_current_strategy(self) -> ContentSafetyStrategy:
        """
        Get the currently configured strategy with caching.
        
        The strategy is cached for a short time to avoid constant environment variable reads,
        but will be refreshed periodically to allow for runtime changes.
        """
        current_time = time.time()
        
        # Check if we need to refresh the cached strategy
        if (self._cached_strategy is None or 
            current_time - self._last_check_time > self._cache_duration):
            
            self._cached_strategy = self._get_strategy_from_env()
            self._last_check_time = current_time
            
            logger.info(f"Content safety strategy loaded/refreshed", strategy=self._cached_strategy.value)
        
        return self._cached_strategy

    async def is_safe_content(self, message: str) -> Tuple[bool, List[str]]:
        """
        Check if content is safe using the configured strategy.
        
        Args:
            message: The message to check for safety
            
        Returns:
            Tuple of (is_safe: bool, reasons: List[str])
            - is_safe: True if content is safe, False otherwise
            - reasons: List of reasons why content is unsafe (empty if safe)
        """
        strategy = self.get_current_strategy()
        
        if strategy == ContentSafetyStrategy.AZURE:
            return await self._check_with_azure(message)
        elif strategy == ContentSafetyStrategy.NEMO:
            return await self._check_with_nemo(message)
        else:
            # Fallback (should not happen due to enum validation)
            logger.error(f"Unknown strategy: {strategy}")
            return await self._check_with_azure(message)

    async def _check_with_azure(self, message: str) -> Tuple[bool, List[str]]:
        """
        Check content safety using Azure Content Safety service.
        
        Args:
            message: The message to check
            
        Returns:
            Tuple of (is_safe: bool, reasons: List[str])
        """
        try:
            logger.debug("Checking content safety with Azure Content Safety", message_length=len(message))
            return await content_safety_service.is_safe_content(message)
        except Exception as e:
            logger.error(f"Error checking content safety with Azure: {e}")
            # On error, be conservative and mark as unsafe
            return False, [f"Azure Content Safety service error: {str(e)}"]

    async def _check_with_nemo(self, message: str) -> Tuple[bool, List[str]]:
        """
        Check content safety using NeMo Guardrails service.
        
        Args:
            message: The message to check
            
        Returns:
            Tuple of (is_safe: bool, reasons: List[str])
        """
        try:
            logger.debug("Checking content safety with NeMo Guardrails", message_length=len(message))
            return await nemo_guardrails_service.is_safe_content(message)
        except Exception as e:
            logger.error(f"Error checking content safety with NeMo: {e}")
            # On error, be conservative and mark as unsafe
            return False, [f"NeMo Guardrails service error: {str(e)}"]

    def is_azure_strategy(self) -> bool:
        """Check if current strategy is Azure."""
        return self.get_current_strategy() == ContentSafetyStrategy.AZURE

    def is_nemo_strategy(self) -> bool:
        """Check if current strategy is NeMo."""
        return self.get_current_strategy() == ContentSafetyStrategy.NEMO


# Global instance
content_safety_strategy_service = ContentSafetyStrategyService()
