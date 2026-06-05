"""Celery task tests for billing dunning and Stripe webhook processing."""

from __future__ import annotations

from datetime import timedelta

import pytest
from apps.billing.tasks import (
    handle_stripe_event,
    send_dunning_email,
    send_trial_ending_email,
)
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone

User = get_user_model()
pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture()
def billing_setup():
    from apps.billing.models import Plan, Subscription
    from apps.rbac.models import RoleChoices, UserTenantRole
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(name="Dunning Co", slug="dunning", schema_name="dunning")
    plan = Plan.objects.create(slug="starter", name="Starter")
    subscription = Subscription.objects.create(
        tenant=tenant,
        plan=plan,
        stripe_customer_id="cus_dunning_test",
        stripe_subscription_id="sub_dunning_test",
        grace_period_end=timezone.now() + timedelta(days=3),
        trial_end=timezone.now() + timedelta(days=2),
    )
    owner = User.objects.create_user(
        username="billingowner",
        email="billingowner@example.com",
        password="SecurePass123!",
    )
    UserTenantRole.objects.create(user=owner, tenant=tenant, role=RoleChoices.OWNER)
    return tenant, owner, subscription


def test_handle_stripe_event_processes_payment_failed(billing_setup):
    tenant, _owner, subscription = billing_setup
    from apps.billing.models import Subscription

    event_data = {"object": {"subscription": subscription.stripe_subscription_id}}
    result = handle_stripe_event.delay("evt_test_001", "invoice.payment_failed", event_data)

    assert result.successful()
    assert result.result == "stripe_event:processed:evt_test_001"
    subscription.refresh_from_db()
    assert subscription.status == Subscription.Status.PAST_DUE


def test_send_dunning_email_sends_to_owner(billing_setup):
    tenant, owner, _subscription = billing_setup

    result = send_dunning_email.delay(str(tenant.pk))

    assert result.successful()
    assert result.result == f"dunning:sent:{tenant.pk}"
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [owner.email]
    assert tenant.name in mail.outbox[0].subject


def test_send_dunning_email_without_owner_returns_no_owner(billing_setup):
    tenant, owner, _subscription = billing_setup
    from apps.rbac.models import UserTenantRole

    UserTenantRole.objects.filter(user=owner, tenant=tenant).delete()

    result = send_dunning_email.delay(str(tenant.pk))

    assert result.successful()
    assert result.result == f"dunning:no_owner:{tenant.pk}"
    assert len(mail.outbox) == 0


def test_send_trial_ending_email_sends_to_owner(billing_setup):
    tenant, owner, _subscription = billing_setup

    result = send_trial_ending_email.delay(str(tenant.pk), days_remaining=2)

    assert result.successful()
    assert result.result == f"trial_ending:sent:{tenant.pk}"
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [owner.email]
    assert "trial" in mail.outbox[0].subject.lower()


def test_send_trial_ending_email_without_owner_returns_no_owner(billing_setup):
    tenant, owner, _subscription = billing_setup
    from apps.rbac.models import UserTenantRole

    UserTenantRole.objects.filter(user=owner, tenant=tenant).delete()

    result = send_trial_ending_email.delay(str(tenant.pk))

    assert result.successful()
    assert result.result == f"trial_ending:no_owner:{tenant.pk}"
    assert len(mail.outbox) == 0
