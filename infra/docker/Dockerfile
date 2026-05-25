# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12

# ── Builder: install Python dependencies ──────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/production.txt ./requirements/
RUN pip install --prefix=/install -r requirements/production.txt

# ── Runtime: lean production image ────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR ${APP_HOME}

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system app \
    && adduser --system --ingroup app app

COPY --from=builder /install /usr/local
COPY . .
COPY infra/docker/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh \
    && mkdir -p staticfiles media \
    && chown -R app:app ${APP_HOME}

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["sh", "-c", "gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers ${GUNICORN_WORKERS:-4} \
  --worker-class ${GUNICORN_WORKER_CLASS:-gthread} \
  --threads ${GUNICORN_THREADS:-2} \
  --timeout ${GUNICORN_TIMEOUT:-120} \
  --graceful-timeout 30 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --access-logfile - \
  --error-logfile -"]

# ── Celery worker ─────────────────────────────────────────────────────────────
FROM runtime AS celery-worker

CMD ["sh", "-c", "celery -A config worker \
  --loglevel=info \
  --concurrency=${CELERY_CONCURRENCY:-4} \
  --max-tasks-per-child=1000"]

# ── Celery beat scheduler ─────────────────────────────────────────────────────
FROM runtime AS celery-beat

CMD ["celery", "-A", "config", "beat", \
     "--loglevel=info", \
     "--scheduler=django_celery_beat.schedulers:DatabaseScheduler"]

# ── Development: includes dev server command ──────────────────────────────────
FROM runtime AS development

ENV DJANGO_SETTINGS_MODULE=config.settings.local

USER root
COPY requirements/local.txt ./requirements/
RUN pip install -r requirements/local.txt
USER app

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
