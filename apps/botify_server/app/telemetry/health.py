"""
Health checks for telemetry components.

This module provides functions to check the health of telemetry components
at runtime, including connectivity to the OpenTelemetry Collector.
"""

import logging
import os
import socket
import time
from typing import Dict, Any, Tuple
from urllib.parse import urlparse

from ..core.config import settings

# Logger for health checks
logger = logging.getLogger(__name__)


def check_telemetry_health() -> Dict[str, Any]:
    """
    Check the health of telemetry components.
    
    Returns:
        Dictionary with health status information
    """
    if not settings.telemetry_enabled:
        return {
            "telemetry_enabled": False,
            "status": "disabled",
            "components": {}
        }
    
    health_info = {
        "telemetry_enabled": True,
        "status": "healthy",
        "components": {}
    }
    
    # Check OpenTelemetry Collector connectivity
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    collector_status, collector_details = _check_otlp_endpoint(otlp_endpoint)
    health_info["components"]["otlp_collector"] = {
        "status": collector_status,
        "endpoint": otlp_endpoint,
        "details": collector_details
    }
    
    # If collector is not available, mark overall status as degraded
    if collector_status != "healthy":
        health_info["status"] = "degraded"
    
    # Log level check
    health_info["components"]["logging"] = {
        "status": "healthy",
        "level": settings.telemetry_log_level
    }
    
    return health_info


def _check_otlp_endpoint(endpoint: str) -> Tuple[str, Dict[str, Any]]:
    """
    Check connectivity to the OpenTelemetry Collector.
    
    Args:
        endpoint: The OTLP endpoint URL
        
    Returns:
        Tuple of (status, details)
    """
    if not endpoint:
        return "unknown", {"reason": "No OTLP endpoint configured"}
    
    try:
        # Handle endpoints in the format "hostname:port" without a scheme
        if "://" not in endpoint:
            # Split by colon to extract host and port
            parts = endpoint.split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 4317  # Default to 4317 if no port
        else:
            # Parse the endpoint URL with scheme
            parsed_url = urlparse(endpoint)
            host = parsed_url.hostname
            port = parsed_url.port or (4317 if parsed_url.scheme == "http" else 4318)
        
        if not host:
            return "unknown", {"reason": "Invalid OTLP endpoint URL"}
        
        # Try to connect to the host:port
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)  # 2 second timeout
        result = sock.connect_ex((host, port))
        connection_time = time.time() - start_time
        sock.close()
        
        if result == 0:
            return "healthy", {"connection_time_ms": round(connection_time * 1000, 2)}
        else:
            return "unhealthy", {
                "reason": f"Failed to connect to {host}:{port}",
                "error_code": result
            }
            
    except Exception as e:
        return "unhealthy", {"reason": str(e), "exception": e.__class__.__name__}
