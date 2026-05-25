"""Unit tests: Billing models and BillingService."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db


@pytest.fixture()
def tenant():
    from apps.tenants.models import Tenant

    return Tenant.objects.create(name="Billed Co", slug="billed", schema_name="billed")


@pytest.fixture()
def subscription(tenant):
    from apps.billing.models import Subscription

    return Subscription.objects.create(
        tenant=tenant,
        stripe_customer_id="cus_test123",
        status=Subscription.Status.ACTIVE,
    )


# ---------------------------------------------------------------------------
# Subscription.is_access_allowed()
# ---------------------------------------------------------------------------


def test_active_subscription_allows_access(subscription):
    assert subscription.is_access_allowed() is True


def test_trialing_subscription_allows_access(subscription):
    from apps.billing.models import Subscription

    subscription.status = Subscription.Status.TRIALING
    assert subscription.is_access_allowed() is True


def test_canceled_subscription_denies_access(subscription):
    from apps.billing.models import Subscription

    subscription.status = Subscription.Status.CANCELED
    assert subscription.is_access_allowed() is False


def test_past_due_within_grace_period_allows_access(subscription):
    from apps.billing.models import Subscription

    subscription.status = Subscription.Status.PAST_DUE
    subscription.grace_period_end = timezone.now() + timedelta(days=3)
    assert subscription.is_access_allowed() is True


def test_past_due_after_grace_period_denies_access(subscription):
    from apps.billing.models import Subscription

    subscription.status = Subscription.Status.PAST_DUE
    subscription.grace_period_end = timezone.now() - timedelta(seconds=1)
    assert subscription.is_access_allowed() is False


def test_past_due_with_no_grace_period_denies_access(subscription):
    from apps.billing.models import Subscription

    subscription.status = Subscription.Status.PAST_DUE
    subscription.grace_period_end = None
    assert subscription.is_access_allowed() is False


# ---------------------------------------------------------------------------
# WebhookEvent idempotency
# ---------------------------------------------------------------------------


def test_webhook_event_unique_constraint():
    from apps.billing.models import WebhookEvent
    from django.db import IntegrityError

    WebhookEvent.objects.create(stripe_event_id="evt_001", event_type="invoice.payment_failed")
    with pytest.raises(IntegrityError):
        WebhookEvent.objects.create(stripe_event_id="evt_001", event_type="invoice.payment_failed")


# ---------------------------------------------------------------------------
# BillingService.process_event()
# ---------------------------------------------------------------------------


def test_payment_failed_sets_past_due_and_grace_period(subscription):
    from apps.billing.models import Subscription
    from services.billing import BillingService

    subscription.stripe_subscription_id = "sub_test001"
    subscription.save()

    event_data = {"object": {"subscription": "sub_test001"}}
    BillingService.process_event("invoice.payment_failed", event_data)

    subscription.refresh_from_db()
    assert subscription.status == Subscription.Status.PAST_DUE
    assert subscription.grace_period_end is not None
    assert subscription.grace_period_end > timezone.now()


def test_payment_succeeded_clears_past_due(subscription):
    from apps.billing.models import Subscription
    from services.billing import BillingService

    subscription.stripe_subscription_id = "sub_test002"
    subscription.status = Subscription.Status.PAST_DUE
    subscription.grace_period_end = timezone.now() + timedelta(days=3)
    subscription.save()

    event_data = {"object": {"subscription": "sub_test002"}}
    BillingService.process_event("invoice.payment_succeeded", event_data)

    subscription.refresh_from_db()
    assert subscription.status == Subscription.Status.ACTIVE
    assert subscription.grace_period_end is None


def test_unknown_event_does_not_raise(subscription):
    from services.billing import BillingService

    BillingService.process_event("unknown.event_type", {})  # must not raise
