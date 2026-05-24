"""REST API views for the notifications app."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardPagination
from apps.notifications.serializers import NotificationSerializer
from services.exceptions import ValidationServiceError
from services.notifications import NotificationService


class NotificationListView(APIView):
    """
    GET /api/v1/notifications/

    Return the authenticated user's notifications (all, newest first),
    paginated with StandardPagination.

    Query parameters
    ----------------
    unread_only=true  -- filter to unread notifications only.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="List notifications for the authenticated user",
        responses={200: NotificationSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        unread_only = request.query_params.get("unread_only", "").lower() == "true"

        if unread_only:
            qs = NotificationService.list_unread(request.user)
        else:
            qs = NotificationService.list_all(request.user)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = NotificationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class MarkNotificationReadView(APIView):
    """
    PATCH /api/v1/notifications/{id}/read/

    Mark a single notification as read. The notification must belong to the
    authenticated user; otherwise 404 is returned.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="Mark a notification as read",
        responses={200: NotificationSerializer, 404: None},
    )
    def patch(self, request: Request, pk: str) -> Response:
        try:
            notification = NotificationService.mark_read(pk, request.user)
        except ValidationServiceError as exc:
            return Response(
                {"error": "not_found", "message": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(NotificationSerializer(notification).data)
