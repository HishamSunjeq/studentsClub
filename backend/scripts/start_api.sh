#!/usr/bin/env bash
set -euo pipefail

# Apply pending DB migrations on boot. Cheap no-op when up-to-date.
# Set RUN_MIGRATIONS=0 to skip (e.g. when running migrations as a separate
# job in production deployments).
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    echo "[start_api] applying migrations..."
    alembic upgrade head
fi

if [ "${APP_ENV:-development}" = "development" ]; then
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
    exec gunicorn app.main:app \
        -k uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:8000 \
        --workers "${WORKERS:-4}" \
        --timeout 120 \
        --access-logfile - \
        --error-logfile -
fi
