import os
import logging
from typing import Dict, List, ClassVar
from pydantic import Field, ConfigDict, field_validator, ValidationInfo
from pydantic_settings import BaseSettings
from dotenv import load_dotenv, find_dotenv

# Set up logging
logger = logging.getLogger(__name__)

# Try to load from .env file if it exists (for local development)
# In production Docker environment, env vars are provided directly
load_dotenv(find_dotenv(usecwd=True))

class Settings(BaseSettings):
    """Configuration settings for the application with integrated validation."""
    
    # Service configuration groups to support validation
    OPENAI_REQUIRED: ClassVar[List[str]] = ["azure_openai_endpoint", "azure_openai_api_key", "model_name"]
    CONTENT_SAFETY_REQUIRED: ClassVar[List[str]] = ["content_safety_endpoint", "content_safety_key"]
    VECTOR_STORE_REQUIRED: ClassVar[List[str]] = ["vector_store_id"]  # Optional but validated if vector store features are used
    
    # Azure OpenAI settings
    azure_openai_endpoint: str = Field(
        default=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        description="Azure OpenAI API endpoint URL"
    )
    azure_openai_api_key: str = Field(
        default=os.getenv("AZURE_OPENAI_API_KEY", ""),
        description="Azure OpenAI API key"
    )
    azure_openai_api_version: str = Field(
        default=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        description="Azure OpenAI API version"
    )
    
    # Model settings
    model_name: str = Field(
        default=os.getenv("AZURE_OPENAI_MODEL_NAME", "gpt-4.1-mini-2025-04-14"),
        description="Model deployment name in Azure"
    )
    
    # Vector store ID for file search
    vector_store_id: str = Field(
        default=os.getenv("AZURE_OPENAI_VECTOR_STORE_ID", ""),
        description="Vector store ID for file search"
    )
    
    # Telemetry settings
    telemetry_enabled: bool = Field(
        default=os.getenv("TELEMETRY_ENABLED", "false").lower() == "true",
        description="Whether to enable OpenLLMetry telemetry"
    )
    # Common telemetry settings
    service_name: str = Field(
        default=os.getenv("SERVICE_NAME", "botify-server"),
        description="Service name for telemetry"
    )
    
    # Server settings
    host: str = Field(
        default=os.getenv("SERVER_HOST", "0.0.0.0"),
        description="Server host address"
    )
    port: int = Field(
        default=int(os.getenv("SERVER_PORT", "8000")),
        description="Server port number"
    )
    
    # Azure Content Safety settings
    content_safety_endpoint: str = Field(
        default=os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT", ""),
        description="Azure Content Safety API endpoint URL"
    )
    content_safety_key: str = Field(
        default=os.getenv("AZURE_CONTENT_SAFETY_KEY", ""),
        description="Azure Content Safety API key"
    )
    content_safety_service_name: str = Field(
        default=os.getenv("AZURE_CONTENT_SAFETY_SERVICE_NAME", ""),
        description="Azure Content Safety service name"
    )
    content_safety_api_version: str = Field(
        default="2024-09-01",
        description="Azure Content Safety API version"
    )
    
    model_config = ConfigDict(case_sensitive=False)
    
    @field_validator("*")
    def log_empty_values(cls, v, info: ValidationInfo):
        """Log when important configuration values are missing"""
        if info.field_name in cls.OPENAI_REQUIRED + cls.CONTENT_SAFETY_REQUIRED + cls.VECTOR_STORE_REQUIRED:
            if not v:
                logger.warning(f"Missing configuration: {info.field_name}")
        return v
    
    def validate_service_config(self, service_name: str) -> Dict[str, bool]:
        """
        Validates if all required configuration for a specific service is available.
        
        Args:
            service_name: Name of the service to validate ('openai', 'content_safety', or 'vector_store')
            
        Returns:
            Dict with validation status and any missing settings
        """
        if service_name == "openai":
            required_fields = self.OPENAI_REQUIRED
            is_configured = self._validate_fields(required_fields)
            return {
                "configured": is_configured,
                "missing": self._get_missing_fields(required_fields)
            }
        elif service_name == "content_safety":
            required_fields = self.CONTENT_SAFETY_REQUIRED
            is_configured = self._validate_fields(required_fields)
            return {
                "configured": is_configured,
                "missing": self._get_missing_fields(required_fields)
            }
        elif service_name == "vector_store":
            required_fields = self.VECTOR_STORE_REQUIRED
            is_configured = self._validate_fields(required_fields)
            return {
                "configured": is_configured,
                "missing": self._get_missing_fields(required_fields)
            }
        else:
            logger.error(f"Unknown service: {service_name}")
            return {"configured": False, "missing": ["unknown_service"]}
    
    def _validate_fields(self, fields: List[str]) -> bool:
        """Check if all specified fields have values"""
        for field in fields:
            if not getattr(self, field, ""):
                return False
        return True
    
    def _get_missing_fields(self, fields: List[str]) -> List[str]:
        """Returns a list of field names that are missing or empty"""
        missing = []
        for field in fields:
            if not getattr(self, field, ""):
                missing.append(field)
        return missing


# Create instance of settings to be used throughout the application
settings = Settings()