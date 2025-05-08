"""
Structured logging setup for the application.

This module configures JSON-formatted structured logging that integrates
with OpenTelemetry for trace context propagation.
"""

import logging
import sys
import os
from typing import Any, Dict, Optional

import structlog
from opentelemetry import trace
from opentelemetry.trace import get_current_span, INVALID_SPAN
from opentelemetry.trace.span import format_trace_id, format_span_id

# Import OpenTelemetry logging components
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

from ..core.config import settings


def add_trace_context_processor(_, __, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Structlog processor that adds trace context from the current active span.
    
    Args:
        event_dict: The log event dictionary
        
    Returns:
        Updated event dictionary with trace context
    """
    try:
        current_span = get_current_span()
        if current_span != INVALID_SPAN:
            trace_id = current_span.get_span_context().trace_id
            span_id = current_span.get_span_context().span_id
            
            if trace_id:
                event_dict["trace_id"] = format_trace_id(trace_id)
            if span_id:
                event_dict["span_id"] = format_span_id(span_id)
    except Exception:
        # Silently fail if we can't get trace context
        pass
    
    return event_dict


def setup_logging() -> None:
    """
    Set up structured logging for the application.
    
    Configures structlog with JSON formatting and OpenTelemetry trace context.
    """
    # Default logging config for all cases
    # This ensures Uvicorn logs are always visible regardless of telemetry settings
    logging.basicConfig(
        level=getattr(logging, settings.telemetry_log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # If telemetry is disabled, we're done
    if not settings.telemetry_enabled:
        return

    log_level = getattr(logging, settings.telemetry_log_level)
    
    # Create resource for logs
    resource = Resource.create({
        SERVICE_NAME: settings.service_name,
        "service.version": "0.1.0",
        "deployment.environment": os.environ.get("ENVIRONMENT", "development")
    })
    
    # Set up OpenTelemetry log provider and exporter
    logger_provider = LoggerProvider(resource=resource)
    
    # Configure OTLP log exporter
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    log_exporter = OTLPLogExporter(
        endpoint=otlp_endpoint,
        insecure=True  # Disable TLS/SSL since collector doesn't use it
    )
    
    # Add log processor to the provider
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(log_exporter)
    )
    
    # Create a handler for OpenTelemetry
    otel_handler = LoggingHandler(
        level=log_level, 
        logger_provider=logger_provider
    )
    
    # Configure standard logging
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create console handler for development mode
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Custom formatter that replaces "uvicorn.error" with "uvicorn.server" for display only
    class UvicornServerFormatter(logging.Formatter):
        def format(self, record):
            # Replace uvicorn.error with uvicorn.server in the display name
            if record.name == "uvicorn.error":
                old_name = record.name
                record.name = "uvicorn.server"
                result = super().format(record)
                record.name = old_name
                return result
            return super().format(record)
    
    console_formatter = UvicornServerFormatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Always add console handler in development mode, regardless of telemetry
    environment = os.environ.get("ENVIRONMENT", "development")
    print(f"Current environment: {environment}")  # Debugging line
    
    # Always add the console handler and the OpenTelemetry handler
    root_logger.addHandler(console_handler)
    root_logger.addHandler(otel_handler)
    
    # Set up Uvicorn loggers to prevent duplication
    # We need to configure Uvicorn's loggers to work with both console and OpenTelemetry
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        logger = logging.getLogger(logger_name)
        logger.propagate = False  # Prevent propagation to root logger
        logger.setLevel(log_level)
        logger.handlers.clear()   # Remove default handlers
        
        # Add both console and OpenTelemetry handlers for Uvicorn
        # This ensures logs appear in both the container console and in telemetry
        logger.addHandler(console_handler)
        logger.addHandler(otel_handler)
    
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        add_trace_context_processor,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.EventRenamer("message"),
    ]

    processors.append(structlog.processors.JSONRenderer())
    
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name, typically the module name
        
    Returns:
        A structured logger instance
    """
    return structlog.get_logger(name)
