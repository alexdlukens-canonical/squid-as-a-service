"""Custom exception handling for Terrasquid API."""
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Format all 4xx/5xx responses into standard error envelope."""
    response = exception_handler(exc, context)

    if response is not None:
        error_code = getattr(exc, "default_code", "error")
        message = str(exc.detail) if hasattr(exc, "detail") else str(exc)
        field_errors = {}

        if isinstance(exc.detail, dict):
            field_errors = {
                k: v[0] if isinstance(v, list) else str(v)
                for k, v in exc.detail.items()
            }
            if not message or message == str({}):
                message = "Validation failed."

        error_payload = {
            "error": error_code,
            "message": message,
        }
        if field_errors or response.status_code in (400, 409):
            error_payload["field_errors"] = field_errors

        response.data = error_payload
    else:
        # Handle non-DRF exceptions (500)
        response = Response(
            {
                "error": "internal_error",
                "message": str(exc) if str(exc) else "Internal server error.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response


class ConfigValidationError(APIException):
    """Raised when Squid configuration validation fails."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Squid configuration validation failed."
    default_code = "config_validation_failed"
