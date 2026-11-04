# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    HF_HOME=/opt/models \
    HF_HUB_DISABLE_TELEMETRY=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-ind tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.12.22 /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

# Model diunduh saat build: runtime berjalan offline dan tidak menghubungi layanan luar.
ARG EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
ARG NER_MODEL=cahya/bert-base-indonesian-NER
RUN .venv/bin/python -c "import sys; from sentence_transformers import SentenceTransformer; \
from transformers import pipeline; SentenceTransformer(sys.argv[1]); pipeline('token-classification', model=sys.argv[2])" \
    "$EMBEDDING_MODEL" "$NER_MODEL"
ENV EMBEDDING_MODEL=$EMBEDDING_MODEL NER_MODEL=$NER_MODEL HF_HUB_OFFLINE=1 PATH=/app/.venv/bin:$PATH

# Tes di dalam image (termasuk OCR Tesseract asli): docker build --target test services/nlp
FROM base AS test
RUN uv sync --frozen
COPY tests ./tests
RUN .venv/bin/pytest -q -p no:cacheprovider

FROM base AS runtime
RUN useradd --system --uid 10001 app
USER app
EXPOSE 8000
# --no-access-log: access log uvicorn memuat IP klien. --proxy-headers memakai FORWARDED_ALLOW_IPS.
CMD ["uvicorn", "--factory", "silsilah.ingest.app:create_app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--no-access-log", "--workers", "1"]
