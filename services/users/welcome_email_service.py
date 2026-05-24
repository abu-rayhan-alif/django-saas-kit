"""Welcome email use-case — no Celery or HTTP dependencies."""

from django.contrib.auth import get_user_model

from services.common import EmailService
from services.exceptions import ValidationServiceError

User = get_user_model()


class WelcomeEmailService:
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

        EmailService.send(
            subject="Welcome to Django SaaS Kit",
            to=user.email,
            template_html="emails/welcome.html",
            template_txt="emails/welcome.txt",
            context=context,
        )
        return f"welcome_sent:{user_id}"
