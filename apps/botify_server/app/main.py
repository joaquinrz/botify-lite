import logging
import time
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router as chat_router
from .core.config import settings
from .telemetry.logging import setup_logging
from .telemetry.metrics import setup_metrics
from .telemetry.traces import setup_tracing

# Set up structured logging first
setup_logging()

# Get logger for this module
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Botify Assistant API",
    description="FastAPI server for Botify Assistant interactions",
    version="0.1.0"
)

# Set up telemetry
setup_metrics()
setup_tracing(app)  # Pass app to enable FastAPI auto-instrumentation

# Add middleware for request timing and logging
@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    start_time = time.time()
    
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        logger.exception("Request failed")
        raise
    finally:
        # Calculate request duration
        duration = time.time() - start_time
        
        # Add processing time header
        if response:
            response.headers["X-Process-Time"] = str(duration)
        
        # Extract path pattern (normalize dynamic routes)
        path = request.url.path
        for route in app.routes:
            if hasattr(route, 'path_regex') and route.path_regex and route.path_regex.match(path):
                path = route.path
                break
        
        # Log request information with normalized path
        logger.info(
            "Request processed",
            extra={
                "method": request.method,
                "path": path,
                "status_code": status_code if 'status_code' in locals() else 500,
                "duration_ms": round(duration * 1000, 2)
            }
        )
    
    return response

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
    
    # Log application startup
    logger.info(
        f"Starting Botify Server on {settings.host}:{settings.port}",
        extra={
            "telemetry_enabled": settings.telemetry_enabled,
            "log_level": settings.telemetry_log_level
        }
    )
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )