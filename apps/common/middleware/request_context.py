"""
HTTP request context — unique ``request_id`` per request (SAAS-601).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

import structlog
from django.http import HttpRequest, HttpResponse

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware:
    """
    Bind a unique ``request_id`` for the lifetime of each request.

    - Accepts incoming ``X-Request-ID`` from clients/gateways
    - Echoes ``X-Request-ID`` on the response
    - Clears structlog contextvars after the response
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        request.request_id = request_id  # type: ignore[attr-defined]

        try:
            response = self.get_response(request)
        finally:
            structlog.contextvars.clear_contextvars()

        response[REQUEST_ID_HEADER] = request_id
        return response
