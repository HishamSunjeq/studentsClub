#!/usr/bin/env bash
set -euo pipefail

exec celery -A app.workers.celery_app beat --loglevel=info
