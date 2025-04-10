import os
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
from dotenv import load_dotenv, find_dotenv

# Try to load from .env file if it exists (for local development)
# In production Docker environment, env vars are provided directly
load_dotenv(find_dotenv(usecwd=True))

class Settings(BaseSettings):
    """Configuration settings for the application."""
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
        default=os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview"),
        description="Azure OpenAI API version"
    )
    
    # Model settings
    model_name: str = Field(
        default=os.getenv("AZURE_OPENAI_MODEL_NAME", "gpt-4o-mini"),
        description="Model deployment name in Azure"
    )
    
    # Vector store ID for file search
    vector_store_id: str = Field(
        default=os.getenv("AZURE_OPENAI_VECTOR_STORE_ID", ""),
        description="Vector store ID for file search"
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
    
    model_config = ConfigDict(case_sensitive=False)


# Create instance of settings to be used throughout the application
settings = Settings()