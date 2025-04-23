from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import atexit

from .api.routes import router as chat_router
from .core.config import settings
from .core.telemetry import init_telemetry, shutdown_telemetry
from .core.logging import setup_structured_logging, get_logger

# Initialize structured logging first
setup_structured_logging(log_level=settings.telemetry_log_level)

# Get a logger for this module
logger = get_logger(__name__)

# Initialize telemetry
init_telemetry(
    service_name=settings.service_name,
    enabled=settings.telemetry_enabled,
    log_level=settings.telemetry_log_level
)

# Register shutdown handler
atexit.register(shutdown_telemetry)

# Create FastAPI application
app = FastAPI(
    title="Botify Assistant API",
    description="FastAPI server for Botify Assistant interactions",
    version="0.1.0"
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you would specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(chat_router)


@app.get("/")
async def root():
    """Root endpoint to check if the API is running."""
    return {"message": "Botify Assistant API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}


if __name__ == "__main__":
    # This block will be executed if the script is run directly
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )