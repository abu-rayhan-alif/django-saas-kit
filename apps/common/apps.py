from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"

    def ready(self) -> None:
        from django.conf import settings

        from apps.common.logging_config import reconfigure_logging

        reconfigure_logging(json_logs=settings.STRUCTLOG_JSON)

        from apps.common.sentry import init_sentry

        init_sentry()

        # Register Celery signal handlers for trace_id propagation.
        import apps.common.celery_logging  # noqa: F401
