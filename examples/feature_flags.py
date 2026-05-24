"""
Feature flag usage examples — SAAS-903.

This module shows the three ways to check flags in Django SaaS Kit using
django-waffle.  It is *examples-only* code: not imported by the application,
not mounted in urls.py, and not tested.  Copy the patterns you need.

See docs/feature-flags.md for the full guide.
"""

from __future__ import annotations

import waffle
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


# ---------------------------------------------------------------------------
# 1. Flag check inside a DRF view
# ---------------------------------------------------------------------------


class DashboardView(APIView):
    """
    Example: serve different payloads based on the ``new_dashboard`` flag.

    Mount with:
        path("api/v1/dashboard/", DashboardView.as_view(), name="dashboard"),
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        if waffle.flag_is_active(request, "new_dashboard"):
            # New experience — returned when the flag is on for this user.
            return Response(
                {
                    "version": "v2",
                    "layout": "new_dashboard",
                    "message": "You are on the new dashboard.",
                }
            )

        # Legacy experience — default when the flag is off.
        return Response(
            {
                "version": "v1",
                "layout": "classic",
                "message": "You are on the classic dashboard.",
            }
        )


# ---------------------------------------------------------------------------
# 2. Flag check in a plain function / service
# ---------------------------------------------------------------------------


def get_dashboard_config(request: Request) -> dict:
    """
    Use flag_is_active anywhere you have access to the request object.
    """
    if waffle.flag_is_active(request, "new_dashboard"):
        return {"theme": "redesign", "sidebar": True}
    return {"theme": "classic", "sidebar": False}


# ---------------------------------------------------------------------------
# 3. Switch check (no request needed — global on/off toggle)
# ---------------------------------------------------------------------------


def process_export(data: list) -> list:
    """
    waffle.switch_is_active() does not need a request — use it for
    background tasks and management commands.
    """
    if waffle.switch_is_active("async_export"):
        # kick off a Celery task
        pass
    return data


# ---------------------------------------------------------------------------
# 4. Sample check (percentage rollout — no request needed)
# ---------------------------------------------------------------------------


def should_run_experiment() -> bool:
    """
    waffle.sample_is_active() returns True for a random percentage of calls.
    Configure the percentage in /admin/waffle/sample/.
    """
    return waffle.sample_is_active("checkout_experiment")
