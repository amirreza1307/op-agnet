FROM python:3.12-slim AS builder

WORKDIR /app

ENV PIP_INDEX_URL=https://pypi.org/simple \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


FROM python:3.12-slim

WORKDIR /app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONPATH="/app/src" \
    MPLCONFIGDIR=/tmp/matplotlib

COPY --from=builder /opt/venv /opt/venv
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY .env.example ./.env.example

RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app /tmp

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=5).read()" || exit 1

CMD ["sh", "-c", "gunicorn -w ${GUNICORN_WORKERS:-1} -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 180 --graceful-timeout 30 --keep-alive 75 src.app:app"]
