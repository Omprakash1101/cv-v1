from rest_framework.views import exception_handler
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    # Log full error
    logger.exception("DRF Exception", exc_info=exc)

    if response is not None:
        response.data = {
            "error": "Request failed. Please contact support."
        }

    return response