"""Unit tests for EmailService.send()."""

from __future__ import annotations

import pytest
from django.core import mail
from services.common import EmailService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SUBJECT = "Test Subject"
RECIPIENT = "alice@example.com"
HTML_TEMPLATE = "emails/welcome.html"
TXT_TEMPLATE = "emails/welcome.txt"
CONTEXT = {"user_name": "Alice", "email": RECIPIENT}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEmailServiceSend:
    """EmailService.send() — happy-path and validation tests."""

    def test_send_with_both_templates_delivers_one_message(self, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

        EmailService.send(
            subject=SUBJECT,
            to=RECIPIENT,
            template_html=HTML_TEMPLATE,
            template_txt=TXT_TEMPLATE,
            context=CONTEXT,
        )

        assert len(mail.outbox) == 1

    def test_correct_subject_and_recipient(self, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

        EmailService.send(
            subject=SUBJECT,
            to=RECIPIENT,
            template_html=HTML_TEMPLATE,
            template_txt=TXT_TEMPLATE,
            context=CONTEXT,
        )

        msg = mail.outbox[0]
        assert msg.subject == SUBJECT
        assert msg.to == [RECIPIENT]

    def test_from_email_defaults_to_settings(self, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        settings.DEFAULT_FROM_EMAIL = "noreply@example.com"

        EmailService.send(
            subject=SUBJECT,
            to=RECIPIENT,
            template_html=HTML_TEMPLATE,
            template_txt=TXT_TEMPLATE,
            context=CONTEXT,
        )

        assert mail.outbox[0].from_email == "noreply@example.com"

    def test_custom_from_email_is_respected(self, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

        EmailService.send(
            subject=SUBJECT,
            to=RECIPIENT,
            template_html=HTML_TEMPLATE,
            template_txt=TXT_TEMPLATE,
            context=CONTEXT,
            from_email="custom@example.com",
        )

        assert mail.outbox[0].from_email == "custom@example.com"

    def test_html_alternative_is_attached(self, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

        EmailService.send(
            subject=SUBJECT,
            to=RECIPIENT,
            template_html=HTML_TEMPLATE,
            template_txt=TXT_TEMPLATE,
            context=CONTEXT,
        )

        msg = mail.outbox[0]
        # EmailMultiAlternatives stores alternatives as (content, mimetype) tuples.
        html_parts = [content for content, mime in msg.alternatives if mime == "text/html"]
        assert html_parts, "Expected an HTML alternative to be attached"
        assert "Alice" in html_parts[0]

    def test_plain_text_body_is_rendered(self, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

        EmailService.send(
            subject=SUBJECT,
            to=RECIPIENT,
            template_html=HTML_TEMPLATE,
            template_txt=TXT_TEMPLATE,
            context=CONTEXT,
        )

        assert "Alice" in mail.outbox[0].body

    def test_list_of_recipients_is_accepted(self, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        recipients = ["alice@example.com", "bob@example.com"]

        EmailService.send(
            subject=SUBJECT,
            to=recipients,
            template_txt=TXT_TEMPLATE,
            context=CONTEXT,
        )

        assert mail.outbox[0].to == recipients

    def test_txt_only_sends_without_html_alternative(self, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

        EmailService.send(
            subject=SUBJECT,
            to=RECIPIENT,
            template_txt=TXT_TEMPLATE,
            context=CONTEXT,
        )

        msg = mail.outbox[0]
        assert msg.body  # plain text present
        assert not msg.alternatives  # no HTML part

    def test_html_only_sends_with_empty_text_body(self, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

        EmailService.send(
            subject=SUBJECT,
            to=RECIPIENT,
            template_html=HTML_TEMPLATE,
            context=CONTEXT,
        )

        msg = mail.outbox[0]
        assert msg.body == ""
        html_parts = [c for c, m in msg.alternatives if m == "text/html"]
        assert html_parts

    def test_raises_value_error_when_no_template_given(self):
        with pytest.raises(ValueError, match="At least one of template_html or template_txt"):
            EmailService.send(subject=SUBJECT, to=RECIPIENT)
