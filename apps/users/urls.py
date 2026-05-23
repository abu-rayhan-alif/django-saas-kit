from django.urls import path

from apps.users.views import UserCreateView, UserListView

urlpatterns = [
    path("", UserCreateView.as_view(), name="user-create"),
    path("list/", UserListView.as_view(), name="user-list"),
]
