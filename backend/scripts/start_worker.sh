#!/usr/bin/env bash
set -euo pipefail

exec celery -A app.workers.celery_app worker \
    --loglevel=info \
    --concurrency="${WORKER_CONCURRENCY:-4}" \
    -Q uploads,ai,embeddings,celery
