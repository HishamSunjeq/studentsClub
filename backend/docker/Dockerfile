FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        tesseract-ocr \
        libtesseract-dev \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.5.14

# Put the venv outside /app so docker-compose bind mounts can't mask it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# ── Development stage ─────────────────────────────────────────────────────────
FROM base AS dev

COPY pyproject.toml uv.lock* ./
RUN uv sync

COPY . .

RUN chmod +x scripts/*.sh

# ── Production stage ──────────────────────────────────────────────────────────
FROM base AS prod

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev

COPY app ./app
COPY scripts ./scripts
COPY alembic.ini ./

RUN chmod +x scripts/*.sh

CMD ["./scripts/start_api.sh"]
