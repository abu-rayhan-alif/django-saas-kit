from django.urls import path
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenRefreshView,
)

from apps.authentication.views import (
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ThrottledTokenObtainPairView,
)

urlpatterns = [
    path("token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),
    path("register/", RegisterView.as_view(), name="auth_register"),
    path("password/reset/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path(
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
]
