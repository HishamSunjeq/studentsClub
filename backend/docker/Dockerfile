FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        tesseract-ocr \
        libtesseract-dev \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.5.14

WORKDIR /app

# ── Development stage ─────────────────────────────────────────────────────────
FROM base AS dev

COPY pyproject.toml uv.lock* ./
RUN uv sync

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ── Production stage ──────────────────────────────────────────────────────────
FROM base AS prod

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev

COPY app ./app
COPY scripts ./scripts
COPY alembic.ini ./

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN chmod +x scripts/*.sh

CMD ["./scripts/start_api.sh"]
