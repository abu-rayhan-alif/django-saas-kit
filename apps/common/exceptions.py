"""
Unified error envelope for the Django SaaS Kit API.

Every error response is returned in the same JSON shape:

    {
        "error":   "validation_error",
        "message": "Email is required.",
        "details": {}
    }

Wire-up in settings::

    REST_FRAMEWORK = {
        "EXCEPTION_HANDLER": "apps.common.exceptions.saas_exception_handler",
    }

And in config/urls.py::

    from apps.common.exceptions import handler404, handler500
"""

from __future__ import annotations

import logging
import re
from typing import Any

from django.http import HttpRequest, JsonResponse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _flatten_detail(detail: Any) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        for item in detail:
            msg = _flatten_detail(item)
            if msg:
                return msg
        return "Invalid input."
    if isinstance(detail, dict):
        for key, value in detail.items():
            msg = _flatten_detail(value)
            if msg:
                return f"{key}: {msg}"
    return str(detail) if detail else "An error occurred."


def _serialise_detail(detail: Any) -> Any:
    if isinstance(detail, list):
        return [_serialise_detail(d) for d in detail]
    if isinstance(detail, dict):
        return {k: _serialise_detail(v) for k, v in detail.items()}
    return str(detail)


# ---------------------------------------------------------------------------
# DRF exception handler
# ---------------------------------------------------------------------------


def saas_exception_handler(exc: Exception, context: dict) -> Response | None:
    """
    Custom DRF EXCEPTION_HANDLER.
    Wraps every exception in the unified error envelope.
    """
    response = drf_exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled exception during request processing", exc_info=exc)
        try:
            import sentry_sdk  # noqa: PLC0415

            if sentry_sdk.is_initialized():
                sentry_sdk.capture_exception(exc)
        except Exception:  # noqa: BLE001
            pass
        return Response(
            {
                "error": "server_error",
                "message": "An unexpected error occurred.",
                "details": {},
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    error_code: str = getattr(exc, "default_code", None) or _camel_to_snake(
        type(exc).__name__
    )
    detail = getattr(exc, "detail", None)

    if isinstance(exc, ValidationError):
        message = "Invalid input."
        raw = _serialise_detail(detail) if detail is not None else {}
        details: Any = {"non_field_errors": raw} if isinstance(raw, list) else raw
    else:
        message = _flatten_detail(detail) if detail is not None else str(exc)
        details = {}

    response.data = {
        "error": error_code,
        "message": message,
        "details": details,
    }
    return response


# ---------------------------------------------------------------------------
# Django non-DRF handlers
# ---------------------------------------------------------------------------


def handler404(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:  # noqa: ARG001
    return JsonResponse(
        {
            "error": "not_found",
            "message": "The requested resource was not found.",
            "details": {},
        },
        status=404,
    )


def handler500(request: HttpRequest) -> JsonResponse:
    return JsonResponse(
        {
            "error": "server_error",
            "message": "An unexpected error occurred.",
            "details": {},
        },
        status=500,
    )
