"""EmailService — thin wrapper around Django's email stack.

Usage::

    EmailService.send(
        subject="Welcome!",
        to="user@example.com",
        template_html="emails/welcome.html",
        template_txt="emails/welcome.txt",
        context={"user_name": "Alice"},
    )

Both *template_html* and *template_txt* are optional individually, but at
least one must be supplied.  When both are given the message is sent as
``multipart/alternative`` (plain-text fallback + HTML).
"""

from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


class EmailService:
    """Application-level email helper.

    Keeps all ``send_mail`` / ``EmailMultiAlternatives`` boilerplate in one
    place so callers never have to import Django mail primitives directly.
    """

    @staticmethod
    def send(
        subject: str,
        to: str | list[str],
        *,
        template_html: str | None = None,
        template_txt: str | None = None,
        context: dict | None = None,
        from_email: str | None = None,
    ) -> None:
        """Send a templated email.

        Args:
            subject: Email subject line.
            to: Recipient address or list of addresses.
            template_html: Django template path for the HTML body (optional).
            template_txt: Django template path for the plain-text body (optional).
            context: Template rendering context (default: empty dict).
            from_email: Sender address; falls back to ``DEFAULT_FROM_EMAIL``.

        Raises:
            ValueError: If neither *template_html* nor *template_txt* is given.
        """
        if not template_html and not template_txt:
            raise ValueError(
                "At least one of template_html or template_txt must be provided."
            )

        ctx = context or {}
        sender = from_email or settings.DEFAULT_FROM_EMAIL
        recipients = [to] if isinstance(to, str) else list(to)

        # Render plain-text body (used as the primary text part).
        text_body = render_to_string(template_txt, ctx) if template_txt else ""

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=sender,
            to=recipients,
        )

        if template_html:
            html_body = render_to_string(template_html, ctx)
            msg.attach_alternative(html_body, "text/html")

        msg.send(fail_silently=False)
