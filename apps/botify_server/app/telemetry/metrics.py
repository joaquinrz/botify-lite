"""
Metrics instrumentation setup for the application.

This module configures OpenTelemetry metrics collection, including
custom metrics for API performance and OpenAI SDK interactions.
"""

import logging
from typing import Dict, Optional

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

from ..core.config import settings

# Global meter provider
_meter_provider = None

# Global meter for application metrics
_meter = None

# Logger for metrics module
logger = logging.getLogger(__name__)


def setup_metrics() -> None:
    """
    Set up OpenTelemetry metrics collection.
    
    Configures a meter provider and exports metrics to the OpenTelemetry Collector.
    """
    global _meter_provider, _meter
    
    if not settings.telemetry_enabled:
        logger.info("Telemetry is disabled. Skipping metrics setup.")
        return
    
    try:
        # Create resource with service information
        resource = Resource.create({
            SERVICE_NAME: settings.service_name,
            "service.version": "0.1.0",  # TODO: Extract from app version
            "deployment.environment": os.environ.get("ENVIRONMENT", "development")
        })
        
        # Configure OTLP exporter for metrics
        otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(
                endpoint=otlp_endpoint,
                insecure=True  # Disable TLS/SSL since collector doesn't use it
            ),
            export_interval_millis=30000  # Export every 30 seconds
        )
        
        # Create and set meter provider
        _meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader]
        )
        metrics.set_meter_provider(_meter_provider)
        
        # Create primary meter
        _meter = metrics.get_meter(settings.service_name)
        
        # Set up common metrics
        create_common_metrics(_meter)
        
        logger.info("OpenTelemetry metrics setup complete")
        
    except Exception as e:
        logger.error(f"Failed to set up OpenTelemetry metrics: {e}")
        # Fallback to no-op metrics
        _meter_provider = None
        _meter = metrics.get_meter(settings.service_name)


def create_common_metrics(meter) -> Dict[str, any]:
    """
    Create common application metrics.
    
    Args:
        meter: The OpenTelemetry meter to use
        
    Returns:
        Dictionary of metric instruments
    """
    if not meter:
        return {}
    
    # Dictionary to store metric instruments
    metric_instruments = {}
    
    # API request metrics
    metric_instruments["http_requests_total"] = meter.create_counter(
        name="http_requests_total",
        description="Total number of HTTP requests",
        unit="1"
    )
    
    metric_instruments["http_request_duration"] = meter.create_histogram(
        name="http_request_duration_seconds",
        description="HTTP request duration in seconds",
        unit="s"
    )
    
    metric_instruments["openai_api_tokens"] = meter.create_counter(
        name="openai_api_tokens_total",
        description="Total tokens consumed by OpenAI API",
        unit="1"
    )
    
    metric_instruments["openai_api_latency"] = meter.create_histogram(
        name="openai_api_latency_seconds",
        description="OpenAI API latency in seconds",
        unit="s"
    )
    
    # Content safety metrics
    metric_instruments["content_safety_requests"] = meter.create_counter(
        name="content_safety_requests_total",
        description="Total content safety API requests",
        unit="1"
    )
    
    metric_instruments["content_safety_latency"] = meter.create_histogram(
        name="content_safety_latency_seconds",
        description="Content safety API latency in seconds",
        unit="s"
    )
    
    return metric_instruments


def get_meter() -> Optional[metrics.Meter]:
    """
    Get the application meter.
    
    Returns:
        The OpenTelemetry meter for the application
    """
    return _meter


# Optional import at module level to avoid circular imports
import os
