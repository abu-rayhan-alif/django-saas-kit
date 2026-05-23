from django.urls import path

from apps.users.views import UserCreateView

urlpatterns = [
    path("", UserCreateView.as_view(), name="user-create"),
]
