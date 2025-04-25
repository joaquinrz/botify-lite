"""
Telemetry decorators for instrumenting functions and methods.

This module provides decorators that can be used to add telemetry
to any function or method without modifying its implementation.
"""

import functools
import time
import inspect
from typing import Any, Callable, Dict, Optional

import structlog
from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode

from .traces import get_tracer
from .metrics import get_meter
from ..core.config import settings

logger = structlog.get_logger(__name__)


def traced(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
    record_exception: bool = True,
    record_duration: bool = True
):
    """
    Decorator to add OpenTelemetry tracing to a function or method.
    
    Args:
        name: Optional name for the span. If not provided, uses function name.
        attributes: Optional attributes to add to the span.
        record_exception: Whether to record exceptions in the span.
        record_duration: Whether to record the function duration in the span.
        
    Returns:
        Decorated function with tracing.
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get span name (either provided or based on function name)
            span_name = name or f"{func.__module__}.{func.__qualname__}"
            
            # Get tracer
            tracer = get_tracer()
            
            # Start timing if needed
            start_time = time.time() if record_duration else None
            
            # Create a span for this operation
            with tracer.start_as_current_span(span_name) as span:
                # Add any provided attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                # Add function signature info to span
                span.set_attribute("function.name", func.__qualname__)
                span.set_attribute("function.module", func.__module__)
                
                # Try to extract self/cls argument for class methods
                if args and len(args) > 0 and hasattr(args[0], "__class__"):
                    span.set_attribute("class.name", args[0].__class__.__name__)
                
                try:
                    # Call the original function
                    result = await func(*args, **kwargs)
                    
                    # Record result attributes if result is a dict
                    if isinstance(result, dict):
                        for key, value in result.items():
                            # Only record primitive types
                            if isinstance(value, (bool, int, float, str)):
                                span.set_attribute(f"result.{key}", value)
                    
                    # Record duration if requested
                    if record_duration and start_time:
                        duration = time.time() - start_time
                        span.set_attribute("duration_seconds", duration)
                    
                    return result
                    
                except Exception as e:
                    # Record exception in span if requested
                    if record_exception:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    
                    # Re-raise the exception
                    raise
                
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Get span name (either provided or based on function name)
            span_name = name or f"{func.__module__}.{func.__qualname__}"
            
            # Get tracer
            tracer = get_tracer()
            
            # Start timing if needed
            start_time = time.time() if record_duration else None
            
            # Create a span for this operation
            with tracer.start_as_current_span(span_name) as span:
                # Add any provided attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                # Add function signature info to span
                span.set_attribute("function.name", func.__qualname__)
                span.set_attribute("function.module", func.__module__)
                
                # Try to extract self/cls argument for class methods
                if args and len(args) > 0 and hasattr(args[0], "__class__"):
                    span.set_attribute("class.name", args[0].__class__.__name__)
                
                try:
                    # Call the original function
                    result = func(*args, **kwargs)
                    
                    # Record result attributes if result is a dict
                    if isinstance(result, dict):
                        for key, value in result.items():
                            # Only record primitive types
                            if isinstance(value, (bool, int, float, str)):
                                span.set_attribute(f"result.{key}", value)
                    
                    # Record duration if requested
                    if record_duration and start_time:
                        duration = time.time() - start_time
                        span.set_attribute("duration_seconds", duration)
                    
                    return result
                    
                except Exception as e:
                    # Record exception in span if requested
                    if record_exception:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    
                    # Re-raise the exception
                    raise
        
        # Return the appropriate wrapper based on whether the function is async or not
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def metered(
    counter_name: Optional[str] = None,
    histogram_name: Optional[str] = None,
    attributes_func: Optional[Callable[..., Dict[str, Any]]] = None
):
    """
    Decorator to add OpenTelemetry metrics to a function or method.
    
    Args:
        counter_name: Optional name for request counter. If not provided, no counter is recorded.
        histogram_name: Optional name for duration histogram. If not provided, no histogram is recorded.
        attributes_func: Optional function to extract attributes from function args and result.
        
    Returns:
        Decorated function with metrics.
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Skip if telemetry is disabled
            if not settings.telemetry_enabled:
                return await func(*args, **kwargs)
            
            # Get meter
            meter = get_meter()
            if not meter:
                return await func(*args, **kwargs)
            
            # Start timing
            start_time = time.time()
            
            try:
                # Call the original function
                result = await func(*args, **kwargs)
                
                # Extract attributes if provided
                attributes = {}
                if attributes_func:
                    attributes = attributes_func(result=result, *args, **kwargs)
                
                # Record counter if name provided
                if counter_name:
                    counter = meter.create_counter(counter_name)
                    counter.add(1, attributes)
                
                # Record histogram if name provided
                if histogram_name:
                    duration = time.time() - start_time
                    histogram = meter.create_histogram(histogram_name)
                    histogram.record(duration, attributes)
                
                return result
                
            except Exception:
                # Record counter with error attribute if name provided
                if counter_name:
                    counter = meter.create_counter(counter_name)
                    error_attributes = {"error": "true"}
                    if attributes_func:
                        error_attributes.update(attributes_func(error=True, *args, **kwargs))
                    counter.add(1, error_attributes)
                
                # Re-raise the exception
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Skip if telemetry is disabled
            if not settings.telemetry_enabled:
                return func(*args, **kwargs)
            
            # Get meter
            meter = get_meter()
            if not meter:
                return func(*args, **kwargs)
            
            # Start timing
            start_time = time.time()
            
            try:
                # Call the original function
                result = func(*args, **kwargs)
                
                # Extract attributes if provided
                attributes = {}
                if attributes_func:
                    attributes = attributes_func(result=result, *args, **kwargs)
                
                # Record counter if name provided
                if counter_name:
                    counter = meter.create_counter(counter_name)
                    counter.add(1, attributes)
                
                # Record histogram if name provided
                if histogram_name:
                    duration = time.time() - start_time
                    histogram = meter.create_histogram(histogram_name)
                    histogram.record(duration, attributes)
                
                return result
                
            except Exception:
                # Record counter with error attribute if name provided
                if counter_name:
                    counter = meter.create_counter(counter_name)
                    error_attributes = {"error": "true"}
                    if attributes_func:
                        error_attributes.update(attributes_func(error=True, *args, **kwargs))
                    counter.add(1, error_attributes)
                
                # Re-raise the exception
                raise
        
        # Return the appropriate wrapper based on whether the function is async or not
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def content_safety_telemetry(func):
    """
    Special-purpose decorator for content safety methods.
    
    This combines tracing and metrics specifically for content safety methods,
    including tracking of safety incidents like jailbreak attempts and harmful content.
    
    Note: This decorator is now kept for backward compatibility.
    For new code, use the content_safety module directly.
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function with content safety telemetry
    """
    # Import here to avoid circular imports
    from .content_safety import content_safety_telemetry as new_decorator
    return new_decorator(func)
