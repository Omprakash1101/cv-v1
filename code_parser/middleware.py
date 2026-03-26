import logging
from django.http import JsonResponse

logger = logging.getLogger(__name__)

class HideStackTraceMiddleware:
    """
    Prevents stack traces from being exposed to users.
    Logs full error internally.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)

        except Exception as e:
            # Log full stack trace
            logger.exception("Internal Server Error")

            # Return safe response
            return JsonResponse({
                "error": "Something went wrong. Please try again later."
            }, status=500)