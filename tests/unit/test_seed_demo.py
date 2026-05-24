import json

import pytest
from apps.rbac.models import RoleChoices, UserTenantRole
from apps.tenants.models import Tenant
from django.contrib.auth import get_user_model
from django.core.management import call_command
from examples.demo_config import DEMO_ADMIN, TENANT1_ID, TENANT2_ID
from services.rbac import RBACService

User = get_user_model()

TOKEN_URL = "/api/v1/auth/token/"
RBAC_LIST_URL = "/api/v1/rbac/{tenant_id}/roles/"


@pytest.mark.django_db
class TestSeedDemoCommand:
    def test_seed_demo_creates_two_tenants(self):
        call_command("seed_demo")

        assert Tenant.objects.filter(pk__in=[TENANT1_ID, TENANT2_ID]).count() == 2
        tenant1 = Tenant.objects.get(slug="tenant1")
        tenant2 = Tenant.objects.get(slug="tenant2")
        assert tenant1.id == TENANT1_ID
        assert tenant2.id == TENANT2_ID

    def test_seed_demo_creates_admin_user(self):
        call_command("seed_demo")

        user = User.objects.get(username=DEMO_ADMIN.username)
        assert user.email == DEMO_ADMIN.email
        assert user.check_password(DEMO_ADMIN.password)
        assert RBACService.get_role(user, Tenant.objects.get(slug="tenant1")) == RoleChoices.ADMIN

    def test_seed_demo_is_idempotent(self):
        call_command("seed_demo")
        call_command("seed_demo")

        assert Tenant.objects.filter(pk__in=[TENANT1_ID, TENANT2_ID]).count() == 2
        assert User.objects.filter(username=DEMO_ADMIN.username).count() == 1
        assert UserTenantRole.objects.count() == 1


@pytest.mark.django_db
def test_demo_user_can_obtain_jwt_and_list_roles(api_client):
    call_command("seed_demo")

    token_resp = api_client.post(
        TOKEN_URL,
        data=json.dumps(
            {"username": DEMO_ADMIN.username, "password": DEMO_ADMIN.password},
        ),
        content_type="application/json",
    )
    assert token_resp.status_code == 200
    access = token_resp.json()["access"]

    list_resp = api_client.get(
        RBAC_LIST_URL.format(tenant_id=TENANT1_ID),
        HTTP_AUTHORIZATION=f"Bearer {access}",
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1


@pytest.mark.django_db
def test_openapi_schema_includes_demo_login_example(api_client):
    import json

    call_command("seed_demo")
    resp = api_client.get("/api/schema/?format=json")
    schema = json.loads(resp.content)

    token_post = schema["paths"]["/api/v1/auth/token/"]["post"]
    examples = token_post["requestBody"]["content"]["application/json"]["examples"]
    demo_example = next(
        (
            ex
            for ex in examples.values()
            if ex.get("value", {}).get("username") == DEMO_ADMIN.username
        ),
        None,
    )
    assert (
        demo_example is not None
    ), f"Demo login example missing from schema keys: {list(examples.keys())}"
    assert demo_example["value"]["password"] == DEMO_ADMIN.password
    assert "seed_demo" in demo_example.get("description", "").lower()
