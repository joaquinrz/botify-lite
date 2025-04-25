"""
Standardized logging configuration for the Botify server.

This module provides a consistent approach to structured logging
across the entire application, making logs easier to search, filter,
and visualize in dashboards.
"""
import logging
import sys
import structlog
from typing import Dict, Any, Optional


def setup_structured_logging(log_level: str = "INFO") -> None:
    """
    Set up structured logging for the entire application.
    
    Args:
        log_level: The minimum log level to record (DEBUG, INFO, WARNING, ERROR)
    """
    # Convert string log level to numeric value
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure structlog with reasonable defaults for structured logging
    structlog.configure(
        processors=[
            # Add log level as a key-value pair
            structlog.stdlib.add_log_level,
            # Add the name of the logger to the log entry
            structlog.stdlib.add_logger_name,
            # Add timestamp in ISO format
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S.%f"),
            # If log level is DEBUG, include current call stack
            structlog.processors.StackInfoRenderer(),
            # If exception, include the exception info
            structlog.processors.format_exc_info,
            # Convert to key-value format
            structlog.processors.JSONRenderer(),
        ],
        # Use standard library's LoggerFactory
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Wrapper class for logger instances
        wrapper_class=structlog.stdlib.BoundLogger,
        # Cache logger instances for performance
        cache_logger_on_first_use=True,
    )
    
    # Set up the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove any existing handlers to avoid duplicates
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)
    
    # Create and add a handler for console output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    root_logger.addHandler(console_handler)
    
    # Set the log level for various library loggers
    configure_library_loggers(numeric_level)
    
    # Set up Uvicorn log configuration to use structured logging
    # This will be picked up when Uvicorn starts
    configure_uvicorn_logging()


def configure_uvicorn_logging():
    """
    Configure Uvicorn logging to use structured format.
    """
    # This function prepares settings that will be picked up by Uvicorn
    # when it configures its logging
    
    # Use structlog's ProcessorFormatter to format Uvicorn logs
    formatter = structlog.stdlib.ProcessorFormatter(
        # These processors will be applied to non-structlog log records
        foreign_pre_chain=[
            # Add log level and logger name
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            # Extract useful information from uvicorn logs
            extract_uvicorn_info,
            # Add timestamp
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S.%f"),
        ],
        # The final processor to convert to JSON
        processor=structlog.processors.JSONRenderer(),
    )
    
    # Create handler with the formatter
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    # Configure Uvicorn loggers to use our handler
    for name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        logger = logging.getLogger(name)
        # Remove any existing handlers
        for h in logger.handlers:
            logger.removeHandler(h)
        # Add our structured handler
        logger.addHandler(handler)
        # Don't propagate to avoid duplicate logs
        logger.propagate = False


def extract_uvicorn_info(logger, log_method, event_dict):
    """
    Extract useful information from Uvicorn logs and format them consistently.
    """
    # Extract client info from access logs
    record = event_dict.get("_record")
    if record and hasattr(record, "args") and isinstance(record.args, tuple) and len(record.args) >= 3:
        if hasattr(record, "name") and record.name == "uvicorn.access":
            # This is an access log
            # Format: (client_addr, method, full_path, http_version, status_code)
            if len(record.args) >= 5:
                client_addr, method, path, _, status_code = record.args[:5]
                event_dict.update({
                    "http.client_ip": client_addr,
                    "http.method": method,
                    "http.path": path,
                    "http.status_code": status_code
                })
            
            # Extract request time if available
            if len(record.args) >= 6:
                request_time = record.args[5]
                event_dict["http.duration_ms"] = request_time * 1000  # Convert to ms
    
    return event_dict


def configure_library_loggers(log_level: int) -> None:
    """
    Configure loggers for third-party libraries to ensure consistent logging.
    
    Args:
        log_level: The numeric log level to set
    """
    # Common HTTP client libraries
    http_libs = [
        # Standard HTTP clients
        "requests", "urllib3", "httpx", "aiohttp", "aiohttp.client",
        # OpenAI SDK specific loggers
        "openai", "openai._base_client"
    ]
    
    # Set appropriate levels for all HTTP client libraries
    for lib in http_libs:
        lib_logger = logging.getLogger(lib)
        lib_logger.setLevel(log_level)
        # Clear any handlers they might have added
        lib_logger.handlers = []
        # Let them use the root logger's handlers
        lib_logger.propagate = True
    
    # Configure FastAPI/Uvicorn loggers
    for name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
        lg = logging.getLogger(name)
        lg.setLevel(log_level)
        lg.handlers = []
        lg.propagate = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger with the given name.
    
    Args:
        name: The name of the logger, typically __name__
        
    Returns:
        A structured logger instance
    """
    return structlog.get_logger(name)


def log_request_response(
    logger: structlog.stdlib.BoundLogger,
    method: str,
    url: str,
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None,
    request_body: Optional[Dict[str, Any]] = None,
    response_body: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
) -> None:
    """
    Log an HTTP request and response in a standardized format.
    
    Args:
        logger: The logger instance to use
        method: HTTP method (GET, POST, etc.)
        url: The URL that was requested
        status_code: HTTP status code of the response
        duration_ms: Request duration in milliseconds
        request_body: Optional dictionary of request data
        response_body: Optional dictionary of response data
        error: Optional error message if the request failed
    """
    # Create the log entry with consistent fields
    log_data = {
        "http.method": method,
        "http.url": url,
    }
    
    # Add optional fields if provided
    if status_code is not None:
        log_data["http.status_code"] = status_code
    
    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms
    
    # Include request/response data if debug level
    if request_body is not None:
        log_data["http.request"] = request_body
    
    if response_body is not None:
        log_data["http.response"] = response_body
    
    if error:
        log_data["error"] = error
        logger.error("http.request.error", **log_data)
    else:
        logger.info("http.request", **log_data)
