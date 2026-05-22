#!/bin/sh
set -e

echo "Waiting for database..."
python - <<'PY'
import os
import sys
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE", "config.settings.prod"))

import django

django.setup()

from django.db import connection
from django.db.utils import OperationalError

for attempt in range(1, 31):
    try:
        connection.ensure_connection()
        print("Database is ready.")
        break
    except OperationalError:
        if attempt == 30:
            print("Database connection failed after 30 attempts.", file=sys.stderr)
            sys.exit(1)
        print(f"Database unavailable (attempt {attempt}/30), retrying...")
        time.sleep(1)
PY

echo "Running migrations..."
python manage.py migrate --noinput

if [ "${RUN_COLLECTSTATIC}" = "true" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

exec "$@"
