import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv, find_dotenv

# Try to load from .env file if it exists (for local development)
# In production Docker environment, env vars are provided directly
load_dotenv(find_dotenv(usecwd=True))


class Settings(BaseSettings):
    """Configuration settings for the CLI application."""
    
    # Server connection settings
    api_base_url: str = Field(
        default=os.getenv("API_BASE_URL", "http://localhost:8000"),
        description="Backend API base URL"
    )
    
    # Chat history settings
    history_file: str = Field(
        default=os.getenv("CHAT_HISTORY_FILE", "./chat_history.txt"),
        description="File path for storing chat history"
    )
    
    # Streaming settings
    use_streaming: bool = Field(
        default=os.getenv("USE_STREAMING", "true").lower() == "true",
        description="Whether to use streaming mode for chat"
    )


# Create instance of settings to be used throughout the application
settings = Settings()