import logging

from traceloop.sdk import Traceloop
from traceloop.sdk.instruments import Instruments

logger = logging.getLogger(__name__)


def init_telemetry(
    service_name: str,
    enabled: bool = False
) -> None:
    """Initialize OpenLLMetry telemetry.

    Args:
        service_name (str): The name of the service for telemetry.
        enabled (bool, optional): Whether to enable telemetry. Defaults to False.
    """
    if not enabled:
        logger.info("Telemetry is disabled")
        return
    
    logger.warning(f"Initializing OpenLLMetry telemetry for service: {service_name}")
    

    try:        
        Traceloop.init(
                app_name=service_name,
                disable_batch=True,
                instruments={Instruments.OPENAI},
            )
        
    except Exception as e:
        logger.error(f"Failed to initialize telemetry: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")