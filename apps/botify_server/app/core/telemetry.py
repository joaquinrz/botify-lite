import logging
import os
from typing import Optional

from traceloop.sdk import Traceloop
from traceloop.sdk.instruments import Instruments

# OpenTelemetry imports for logs
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

logger = logging.getLogger(__name__)

# Global variable to hold the logger provider for shutdown
_logger_provider: Optional[LoggerProvider] = None


def init_telemetry(
    service_name: str,
    enabled: bool = False,
    log_level: str = "INFO"
) -> None:
    """Initialize OpenTelemetry telemetry including traces and logs.

    Args:
        service_name (str): The name of the service for telemetry.
        enabled (bool, optional): Whether to enable telemetry. Defaults to False.
        log_level (str, optional): The log level to capture. Defaults to "INFO".
    """
    global _logger_provider
    
    if not enabled:
        logger.info("Telemetry is disabled")
        return
    
    logger.warning(f"Initializing OpenTelemetry telemetry for service: {service_name}")
    
    # Get OTLP endpoint from environment or use default
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "otelcol:4317")
    
    try:
        # 1. Initialize Traceloop for traces
        Traceloop.init(
            app_name=service_name,
            disable_batch=True,
            instruments={Instruments.OPENAI},
        )
        
        # 2. Initialize OpenTelemetry logs
        # Create a resource with common attributes
        resource = Resource.create({
            "service.name": service_name,
            "service.instance.id": os.uname().nodename
        })
        
        # Create a LoggerProvider
        _logger_provider = LoggerProvider(resource=resource)
        set_logger_provider(_logger_provider)
        

        logger.info(f"Using gRPC protocol for OpenTelemetry logs with endpoint: {otlp_endpoint}")
        otlp_log_exporter = OTLPLogExporter(endpoint=otlp_endpoint, insecure=True)
        
        # Add a BatchLogRecordProcessor to the LoggerProvider
        _logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(otlp_log_exporter)
        )
        
        # Convert log level string to numeric level
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Create a LoggingHandler
        handler = LoggingHandler(level=numeric_level, logger_provider=_logger_provider)

        root = logging.getLogger()
        root.setLevel(numeric_level)
        root.addHandler(handler)

        # also attach to Uvicorn/FastAPI loggers so HTTP request logs flow through OTLP
        for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
            lg = logging.getLogger(name)
            lg.setLevel(numeric_level)
            lg.addHandler(handler)
        
        logger.info(f"OpenTelemetry log collection initialized with level: {log_level}")
        
    except Exception as e:
        logger.error(f"Failed to initialize telemetry: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


def shutdown_telemetry():
    """Shutdown OpenTelemetry telemetry, ensuring all logs are flushed."""
    global _logger_provider
    
    if _logger_provider:
        logger.info("Shutting down OpenTelemetry telemetry...")
        try:
            _logger_provider.shutdown()
            logger.info("OpenTelemetry telemetry shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down telemetry: {e}")