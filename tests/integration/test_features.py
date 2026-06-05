"""Integration tests for feature flag API endpoints."""

from __future__ import annotations

import json

import pytest
from django.contrib.auth import get_user_model
from services.features import FeatureService

FEATURES_URL = "/api/v1/features/"
TOKEN_URL = "/api/v1/auth/token/"

User = get_user_model()


def _post_json(client, url: str, payload: dict):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def _auth_headers(client, user, password: str = "StrongPass123!") -> dict:
    response = _post_json(
        client,
        TOKEN_URL,
        {"username": user.username, "password": password},
    )
    assert response.status_code == 200, response.json()
    access = response.json()["access"]
    return {"HTTP_AUTHORIZATION": f"Bearer {access}"}


@pytest.fixture()
def user(db):
    return User.objects.create_user(
        username="featureuser",
        password="StrongPass123!",
        email="featureuser@example.com",
    )


@pytest.mark.django_db
def test_feature_flags_require_authentication(api_client):
    response = api_client.get(FEATURES_URL)
    assert response.status_code == 401


@pytest.mark.django_db
def test_list_feature_flags_for_tenant(api_client, user):
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.get(slug="test")
    FeatureService.set_for_tenant(tenant, "advanced_analytics", is_enabled=True)

    headers = _auth_headers(api_client, user)
    response = api_client.get(FEATURES_URL, **headers)

    assert response.status_code == 200
    data = response.json()
    assert data["advanced_analytics"] is True
    assert "api_access" in data


@pytest.mark.django_db
def test_feature_flag_detail_endpoint(api_client, user):
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.get(slug="test")
    FeatureService.set_for_tenant(tenant, "bulk_export", is_enabled=True)

    headers = _auth_headers(api_client, user)
    response = api_client.get(f"{FEATURES_URL}bulk_export/", **headers)

    assert response.status_code == 200
    assert response.json() == {"flag_name": "bulk_export", "enabled": True}
