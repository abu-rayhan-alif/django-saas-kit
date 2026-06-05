"""DRF rate limiting (SAAS-702).

Plan-based throttling
---------------------
``TenantPlanThrottle`` respects subscription plan limits.  Add it to a view::

    class MyView(APIView):
        throttle_classes = [TenantPlanThrottle]

Rates are resolved in this order:
1. Per-plan override from ``PLAN_THROTTLE_RATES`` setting, keyed by plan slug.
2. ``THROTTLE_USER_RATE`` default (fallback for unauthenticated or no plan).

Example settings::

    PLAN_THROTTLE_RATES = {
        "free":       "60/minute",
        "starter":    "300/minute",
        "pro":        "1000/minute",
        "enterprise": "10000/minute",
    }
"""

from rest_framework.settings import api_settings
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle


class LoginRateThrottle(ScopedRateThrottle):
    scope = "login"

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES.get(self.scope, "5/minute")


class RegisterRateThrottle(ScopedRateThrottle):
    scope = "register"

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES.get(self.scope, "3/hour")


class PasswordResetRateThrottle(ScopedRateThrottle):
    scope = "password_reset"

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES.get(self.scope, "5/hour")


class AnonRateThrottle(SimpleRateThrottle):
    """Anonymous clients."""

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
    """Authenticated users."""

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


# ---------------------------------------------------------------------------
# Plan-based throttling
# ---------------------------------------------------------------------------


def _resolve_plan_rate(request):
    """Return the throttle rate for the tenant's plan, or None to use default."""
    from django.conf import settings as django_settings

    plan_rates = getattr(django_settings, "PLAN_THROTTLE_RATES", {})
    if not plan_rates:
        return None

    tenant = getattr(request, "tenant", None)
    if not tenant:
        return None

    try:
        subscription = tenant.subscription
        plan_slug = subscription.plan.slug if subscription.plan else ""
    except Exception:
        return None

    return plan_rates.get(plan_slug)


class TenantPlanThrottle(SimpleRateThrottle):
    """
    Throttle authenticated requests based on the tenant's subscription plan.

    Unauthenticated requests fall through to ``AnonRateThrottle``.
    Authenticated requests on tenants without a matching plan use the default user rate.

    Configure per-plan rates in settings::

        PLAN_THROTTLE_RATES = {
            "free":       "60/minute",
            "starter":    "300/minute",
            "pro":        "1000/minute",
            "enterprise": "10000/minute",
        }
    """

    scope = "plan"

    def get_rate(self):
        from django.conf import settings as django_settings

        return api_settings.DEFAULT_THROTTLE_RATES.get(
            "user",
            getattr(django_settings, "THROTTLE_USER_RATE", "100/minute"),
        )

    def allow_request(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return True  # let AnonRateThrottle handle it

        plan_rate = _resolve_plan_rate(request)
        self.rate = plan_rate if plan_rate is not None else self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return None
        tenant = getattr(request, "tenant", None)
        tenant_id = str(tenant.pk) if tenant else "no_tenant"
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"{request.user.pk}:{tenant_id}",
        }
