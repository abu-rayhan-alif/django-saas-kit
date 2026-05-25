from django.urls import path

from apps.users.views import UserCreateView, UserListView

urlpatterns = [
    path("", UserListView.as_view(), name="user-list"),
    path("list/", UserListView.as_view(), name="user-list-alt"),
    path("create/", UserCreateView.as_view(), name="user-create"),
]
