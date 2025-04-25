"""
Distributed tracing setup for the application.

This module configures OpenTelemetry tracing with custom instrumentors
and sampling strategies to optimize telemetry collection.
"""

import logging
import os
from contextlib import contextmanager
from typing import Optional, Dict, Any, Iterator, Callable

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.sdk.trace.sampling import (
    ParentBasedTraceIdRatio,
    TraceIdRatioBased,
    ALWAYS_ON,
    ALWAYS_OFF
)

# Instrumentors
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from ..core.config import settings

# Logger for tracing module
logger = logging.getLogger(__name__)

# Global tracer provider
_tracer_provider = None

# Global tracer for application traces
_tracer = None


def setup_tracing(app=None) -> None:
    """
    Set up OpenTelemetry tracing.
    
    Configures a tracer provider and exports traces to the OpenTelemetry Collector.
    
    Args:
        app: Optional FastAPI application to instrument
    """
    global _tracer_provider, _tracer
    
    if not settings.telemetry_enabled:
        logger.info("Telemetry is disabled. Skipping tracing setup.")
        return
    
    try:
        # Create resource with service information
        resource = Resource.create({
            SERVICE_NAME: settings.service_name,
            "service.version": "0.1.0",  # TODO: Extract from app version
            "deployment.environment": os.environ.get("ENVIRONMENT", "development")
        })
        
        # Determine sampling rate based on environment
        # Higher sampling in dev/staging, lower in production
        environment = os.environ.get("ENVIRONMENT", "development")
        sampling_rate = _get_sampling_rate(environment)
        
        # Create sampler - parent based with trace ID ratio
        if sampling_rate >= 1.0:
            sampler = ALWAYS_ON
        elif sampling_rate <= 0.0:
            sampler = ALWAYS_OFF
        else:
            sampler = ParentBasedTraceIdRatio(
                root=TraceIdRatioBased(sampling_rate)
            )
        
        # Configure OTLP exporter for traces
        otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        
        # Ensure the endpoint uses the correct protocol (insecure HTTP for gRPC)
        # OTLP exporter uses gRPC by default for traces
        span_processor = BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=otlp_endpoint,
                insecure=True  # Disable TLS/SSL since collector doesn't use it
            )
        )
        
        # Create and set tracer provider
        _tracer_provider = TracerProvider(
            resource=resource,
            sampler=sampler
        )
        _tracer_provider.add_span_processor(span_processor)
        trace.set_tracer_provider(_tracer_provider)
        
        # Create primary tracer
        _tracer = trace.get_tracer(settings.service_name)
        
        # Set up instrumentation for common libraries
        _setup_instrumentation(app)
        
        logger.info(f"OpenTelemetry tracing setup complete with sampling rate {sampling_rate}")
        
    except Exception as e:
        logger.error(f"Failed to set up OpenTelemetry tracing: {e}")
        # Fallback to no-op tracer
        _tracer_provider = None
        _tracer = trace.get_tracer(settings.service_name)


def _get_sampling_rate(environment: str) -> float:
    """
    Determine the appropriate sampling rate based on environment.
    
    Args:
        environment: The current deployment environment
        
    Returns:
        Sampling rate between 0.0 and 1.0
    """
    # Get sampling rate from environment variable if set
    env_sampling_rate = os.environ.get("OTEL_TRACES_SAMPLER_ARG")
    if env_sampling_rate:
        try:
            return float(env_sampling_rate)
        except (ValueError, TypeError):
            pass
    
    # Default sampling rates by environment
    if environment == "production":
        return 0.1  # Sample 10% of traces in production
    elif environment == "staging":
        return 0.5  # Sample 50% of traces in staging
    else:
        return 1.0  # Sample all traces in development


def _setup_instrumentation(app=None) -> None:
    """
    Set up auto-instrumentation for common libraries.
    
    Args:
        app: Optional FastAPI application to instrument
    """
    # Instrument FastAPI if app is provided
    if app:
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=_tracer_provider,
            excluded_urls="^/health$,^/metrics$",  # Exclude health and metrics endpoints
        )
    
    # Instrument other libraries
    RequestsInstrumentor().instrument(tracer_provider=_tracer_provider)
    AioHttpClientInstrumentor().instrument(tracer_provider=_tracer_provider)
    LoggingInstrumentor().instrument(tracer_provider=_tracer_provider)
    
    logger.debug("Library auto-instrumentation complete")


def get_tracer() -> trace.Tracer:
    """
    Get the application tracer.
    
    Returns:
        The OpenTelemetry tracer for the application
    """
    if _tracer is None:
        return trace.get_tracer(settings.service_name)
    return _tracer


@contextmanager
def create_span(name: str, context: Optional[Dict[str, Any]] = None, kind: Optional[trace.SpanKind] = None) -> Iterator[trace.Span]:
    """
    Create a new span as a context manager.
    
    Args:
        name: The name of the span
        context: Optional attributes to set on the span
        kind: Optional span kind (client, server, etc.)
        
    Yields:
        The created span
    """
    tracer = get_tracer()
    ctx = {}
    if context:
        ctx.update(context)
    
    with tracer.start_as_current_span(name, kind=kind, attributes=ctx) as span:
        try:
            yield span
        except Exception as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            span.record_exception(e)
            raise
