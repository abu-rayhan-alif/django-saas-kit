"""
Celery trace context propagation (SAAS-601).

When a task is published from an HTTP request, the active ``request_id`` is
copied into Celery message headers as ``trace_id``. Workers bind ``trace_id``
into structlog contextvars for the duration of the task.
"""

from __future__ import annotations

import uuid

import structlog
from celery import signals

TRACE_ID_HEADER = "trace_id"


@signals.before_task_publish.connect
def inject_trace_id(headers: dict | None = None, **kwargs) -> None:
    """Propagate ``request_id`` from the current context as ``trace_id``."""
    if headers is None:
        return
    context = structlog.contextvars.get_contextvars()
    trace_id = context.get("request_id") or context.get("trace_id")
    if trace_id:
        headers[TRACE_ID_HEADER] = trace_id


@signals.task_prerun.connect
def bind_task_trace_id(task_id: str, task, *args, **kwargs) -> None:
    """Bind ``trace_id`` for worker log lines."""
    headers = getattr(task.request, "headers", None) or {}
    trace_id = headers.get(TRACE_ID_HEADER)
    if not trace_id:
        trace_id = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(trace_id=trace_id)


@signals.task_postrun.connect
def clear_task_trace_id(task_id: str, task, *args, **kwargs) -> None:
    structlog.contextvars.clear_contextvars()
