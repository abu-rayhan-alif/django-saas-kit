"""SAAS-702 — DRF rate limiting."""

from __future__ import annotations

import copy
import json

import pytest
from apps.common.exceptions import saas_exception_handler
from apps.common.throttling import LoginRateThrottle
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import RequestFactory, override_settings
from rest_framework import status
from rest_framework.exceptions import Throttled
from rest_framework.settings import api_settings
from rest_framework.views import APIView

TOKEN_URL = "/api/v1/auth/token/"
USER_LIST_URL = "/api/v1/users/list/"


def _post_token(client, username: str, password: str):
    return client.post(
        TOKEN_URL,
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )


def _rest_framework_with_rates(settings, **rate_overrides):
    rf = copy.deepcopy(settings.REST_FRAMEWORK)
    rf["DEFAULT_THROTTLE_RATES"] = {**rf["DEFAULT_THROTTLE_RATES"], **rate_overrides}
    return rf


@pytest.fixture
def auth_user(db):
    return get_user_model().objects.create_user(
        username="throttleuser",
        password="StrongPass123!",
        email="throttle@example.com",
        is_staff=True,
    )


def test_login_rate_throttle_class_enforces_limit(settings):
    """Scoped login throttle blocks after N attempts (same IP)."""
    rf = _rest_framework_with_rates(settings, login="2/minute")
    with override_settings(REST_FRAMEWORK=rf):
        api_settings.reload()
        cache.clear()

        request = RequestFactory().post(TOKEN_URL)
        request.user = AnonymousUser()
        throttle = LoginRateThrottle()
        view = APIView()
        view.throttle_scope = "login"

        assert throttle.allow_request(request, view) is True
        assert throttle.allow_request(request, view) is True
        assert throttle.allow_request(request, view) is False


@pytest.mark.django_db
def test_login_throttle_returns_429(api_client, auth_user, with_throttling):
    """Sixth login within a minute exceeds the default 5/minute limit."""
    for _ in range(5):
        response = _post_token(api_client, auth_user.username, "StrongPass123!")
        assert response.status_code == status.HTTP_200_OK

    response = _post_token(api_client, auth_user.username, "StrongPass123!")
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    body = response.json()
    assert body["error"] == "throttled"
    assert body["details"] == {}


@pytest.mark.django_db
def test_authenticated_user_throttle_returns_429(api_client, auth_user, settings, with_throttling):
    """Authenticated list requests exceed a lowered user rate limit."""
    rf = _rest_framework_with_rates(settings, user="2/minute", login="100/minute")
    with override_settings(REST_FRAMEWORK=rf):
        api_settings.reload()
        cache.clear()

        login = _post_token(api_client, auth_user.username, "StrongPass123!")
        access = login.json()["access"]
        headers = {"HTTP_AUTHORIZATION": f"Bearer {access}"}

        for _ in range(2):
            response = api_client.get(USER_LIST_URL, **headers)
            assert response.status_code == status.HTTP_200_OK

        response = api_client.get(USER_LIST_URL, **headers)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert response.json()["error"] == "throttled"


def test_throttled_exception_uses_unified_envelope():
    exc = Throttled(detail="Request was throttled. Expected available in 60 seconds.")
    response = saas_exception_handler(exc, {})

    assert response is not None
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.data["error"] == "throttled"
    assert response.data["details"] == {}


def test_default_throttle_rates_configured(settings):
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert rates["login"] == "5/minute"
    assert rates["user"] == "100/minute"
    assert rates["anon"] == "20/minute"
