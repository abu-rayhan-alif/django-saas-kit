"""DRF rate limiting (SAAS-702)."""

from rest_framework.settings import api_settings
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle


class LoginRateThrottle(ScopedRateThrottle):
    """``POST /api/v1/auth/token/`` — requires ``throttle_scope = "login"`` on the view."""

    scope = "login"

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES.get(self.scope, "5/minute")


class RegisterRateThrottle(ScopedRateThrottle):
    """``POST /api/v1/auth/register/`` — 3 attempts per hour per IP."""

    scope = "register"

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES.get(self.scope, "3/hour")


class PasswordResetRateThrottle(ScopedRateThrottle):
    """``POST /api/v1/auth/password/reset/`` — 5 attempts per hour per IP."""

    scope = "password_reset"

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES.get(self.scope, "5/hour")


class AnonRateThrottle(SimpleRateThrottle):
    """Anonymous clients — reads live rates from settings."""

    scope = "anon"

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class UserRateThrottle(SimpleRateThrottle):
    """Authenticated users — reads live rates from settings."""

    scope = "user"

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }
