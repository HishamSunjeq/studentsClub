#!/usr/bin/env bash
set -euo pipefail

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
