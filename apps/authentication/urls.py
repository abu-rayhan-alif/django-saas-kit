from django.urls import path
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenRefreshView,
)

from apps.authentication.social_views import SocialAuthView
from apps.authentication.two_factor_views import (
    TwoFactorCompleteView,
    TwoFactorDisableView,
    TwoFactorSetupView,
    TwoFactorVerifyEnableView,
)
from apps.authentication.views import (
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ThrottledTokenObtainPairView,
)

urlpatterns = [
    # JWT
    path("token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),
    # Registration & password reset
    path("register/", RegisterView.as_view(), name="auth_register"),
    path("password/reset/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path(
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    # Social OAuth
    path("social/", SocialAuthView.as_view(), name="social_auth"),
    # Two-Factor Authentication (TOTP)
    path("2fa/setup/", TwoFactorSetupView.as_view(), name="2fa_setup"),
    path("2fa/enable/", TwoFactorVerifyEnableView.as_view(), name="2fa_enable"),
    path("2fa/disable/", TwoFactorDisableView.as_view(), name="2fa_disable"),
    path("2fa/complete/", TwoFactorCompleteView.as_view(), name="2fa_complete"),
]
