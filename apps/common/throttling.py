"""DRF rate limiting (SAAS-702)."""

from rest_framework.settings import api_settings
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle


class LoginRateThrottle(ScopedRateThrottle):
    """
    ``POST /api/v1/auth/token/`` — requires ``throttle_scope = "login"`` on the view.
    """

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]


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
