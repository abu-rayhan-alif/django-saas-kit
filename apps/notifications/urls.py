from django.urls import path

from apps.notifications.views import MarkNotificationReadView, NotificationListView

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("<uuid:pk>/read/", MarkNotificationReadView.as_view(), name="notification-mark-read"),
]
