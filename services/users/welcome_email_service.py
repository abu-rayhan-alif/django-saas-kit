"""Welcome email use-case — no Celery or HTTP dependencies."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string

from services.exceptions import ValidationServiceError

User = get_user_model()


class WelcomeEmailService:
    # TODO: Add your business logic here

    @staticmethod
    def send_to_user(user_id: int) -> str:
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist as exc:
            raise ValidationServiceError(f"User {user_id} not found.") from exc

        context = {
            "user_name": user.get_full_name() or user.username,
            "email": user.email,
        }
        body = render_to_string("emails/welcome.txt", context)

        send_mail(
            subject="Welcome to Django SaaS Kit",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return f"welcome_sent:{user_id}"
