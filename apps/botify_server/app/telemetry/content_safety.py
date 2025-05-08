"""
Content Safety Telemetry Module

This module provides specialized telemetry functions for content safety features.
It encapsulates the complexity of telemetry instrumentation to keep the service
code clean and focused on business logic.
"""

import functools
import time
from typing import Dict, Any, List, Optional, Callable

import structlog
from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode

from .traces import get_tracer
from .metrics import get_meter
from ..core.config import settings

logger = structlog.get_logger(__name__)

# Pre-defined metric names for consistency
METRICS = {
    "incident_duration": "content_safety_incident_duration_seconds"
}


def trace_content_safety(
    message_length: int,
    is_safe: bool,
    detected_terms: List[str],
    span: Optional[Span] = None
) -> None:
    """
    Record content safety details in the current span.
    
    Args:
        message_length: Length of the checked message
        is_safe: Whether the content was determined to be safe
        detected_terms: List of detected safety issues
        span: Optional span to use (uses current span if None)
    """
    if span is None:
        span = trace.get_current_span()
        if not span:
            return
    
    # Record basic attributes
    span.set_attribute("message.length", message_length)
    span.set_attribute("content.is_safe", is_safe)
    span.set_attribute("content.detected_issues", len(detected_terms))
    
    # Record specific incident types
    if detected_terms:
        span.set_attribute("content.detected_terms", ", ".join(detected_terms))
        
        # Add span events for specific incidents
        if "jailbreak" in detected_terms:
            span.add_event("jailbreak_detected", {"timestamp": time.time()})
        
        # Track other harmful content types
        harmful_terms = [term for term in detected_terms 
                        if term != "jailbreak" and term != "Content safety service error"]
        if harmful_terms:
            span.add_event("harmful_content_detected", {
                "categories": ", ".join(harmful_terms),
                "category_count": len(harmful_terms),
                "timestamp": time.time()
            })


def record_content_safety_metrics(
    duration: float,
    is_safe: bool,
    detected_terms: List[str]
) -> None:
    """
    Record metrics for content safety incidents.
    
    Args:
        duration: Duration of the check in seconds
        is_safe: Whether the content was determined to be safe
        detected_terms: List of detected safety issues
    """
    # Skip if no issues detected or telemetry is disabled
    if not detected_terms or not settings.telemetry_enabled:
        return
    
    meter = get_meter()
    if not meter:
        return
    
    # Get current span details for correlation
    span_id = None
    trace_id = None
    current_span = trace.get_current_span()
    if current_span:
        span_context = current_span.get_span_context()
        if span_context:
            span_id = f"{span_context.span_id:016x}"
            trace_id = f"{span_context.trace_id:032x}"
    
    # Create incident histogram (used to connect metrics to traces via exemplars)
    incident_histogram = meter.create_histogram(
        METRICS["incident_duration"],
        description="Duration of content safety incident detection",
        unit="s"
    )
    
    # Record metrics for each incident type
    record_incident_metrics(
        "jailbreak", detected_terms, is_safe, duration, 
        incident_histogram, span_id, trace_id
    )
    
    # Record other harmful content types
    harmful_terms = [term for term in detected_terms 
                    if term != "jailbreak" and term != "Content safety service error"]
    
    for category in harmful_terms:
        record_incident_metrics(
            category, None, is_safe, duration,
            incident_histogram, span_id, trace_id,
            incident_type="harmful_content"
        )


def record_incident_metrics(
    category: str,
    detected_terms: Optional[List[str]],
    is_safe: bool,
    duration: float, 
    histogram,
    span_id: Optional[str],
    trace_id: Optional[str],
    incident_type: str = None
) -> None:
    """
    Record metrics for a specific safety incident.
    
    Args:
        category: The specific category of incident
        detected_terms: List of detected terms (for filtering)
        is_safe: Whether the content was determined to be safe
        duration: Duration of the check in seconds
        histogram: The histogram instrument to use
        span_id: Optional span ID for correlation
        trace_id: Optional trace ID for correlation
        incident_type: Type of incident (defaults to category name)
    """
    # Skip if this category wasn't detected
    if detected_terms is not None and category not in detected_terms:
        return
    
    # Use provided incident type or default to category
    incident_type = incident_type or category
    
    # Create attributes for this incident
    attributes = {
        "service": settings.service_name,
        "incident_type": incident_type,
        "category": category,
        "is_safe": str(is_safe)
    }
    
    # Add trace correlation if available
    if span_id and trace_id:
        attributes["span_id"] = span_id
        attributes["trace_id"] = trace_id
    
    # Record metrics
    histogram.record(duration, attributes)


def get_traced_content_safety_decorator(
    span_name: str = "content_safety.check",
    log_message: bool = True
) -> Callable:
    """
    Factory function that creates a content safety telemetry decorator.
    
    Args:
        span_name: Name for the span
        log_message: Whether to log message info
        
    Returns:
        A decorator function that adds telemetry to a content safety function
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract message from args or kwargs
            message = None
            if len(args) > 1:
                message = args[1]  # Assuming first arg is self, second is message
            elif "message" in kwargs:
                message = kwargs["message"]
            
            message_length = len(message) if message else 0
            
            # Start timing
            start_time = time.time()
            
            # Get tracer
            tracer = get_tracer()
            
            # Create span with initial attributes
            with tracer.start_as_current_span(
                span_name, 
                attributes={
                    "message.length": message_length,
                    "service.name": settings.service_name
                }
            ) as span:
                try:
                    # Call the function
                    result = await func(*args, **kwargs)
                    
                    # Extract result info
                    is_safe = result.get("is_safe", False)
                    detected_terms = result.get("detected_terms", [])
                    
                    # Add telemetry
                    duration = time.time() - start_time
                    
                    # Record trace data
                    trace_content_safety(message_length, is_safe, detected_terms, span)
                    
                    # Record metrics
                    record_content_safety_metrics(duration, is_safe, detected_terms)
                    
                    # Log the result
                    if log_message:
                        logger.info(
                            "content_safety.result", 
                            is_safe=is_safe, 
                            detected_issues=len(detected_terms)
                        )
                    
                    return result
                    
                except Exception as e:
                    # Record error in span
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    
                    # Log the error
                    logger.error(f"Content safety check failed: {e}")
                    
                    # Re-raise the exception
                    raise
                finally:
                    # Log completion
                    duration = time.time() - start_time
                    logger.info(
                        "content_safety.request.completed",
                        duration_ms=round(duration * 1000, 2)
                    )
        
        return wrapper
    
    return decorator


# Default decorator for backward compatibility
content_safety_telemetry = get_traced_content_safety_decorator()
"""
This decorator adds telemetry to content safety functions.
It traces the function execution, records metrics, and logs results.
"""
