from django.urls import path

from apps.users.views import MeView, ProfileView, UserCreateView, UserListView

urlpatterns = [
    path("", UserListView.as_view(), name="user-list"),
    path("list/", UserListView.as_view(), name="user-list-alt"),
    path("create/", UserCreateView.as_view(), name="user-create"),
    path("me/", MeView.as_view(), name="user-me"),
    path("me/profile/", ProfileView.as_view(), name="user-profile"),
]
