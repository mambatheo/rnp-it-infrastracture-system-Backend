## Backend-only Dockerfile (no frontend)
## Frontend is a separate repo — built and served by its own container.
##
## Usage (from /opt/itinfra/backend/ on the server):
##   docker compose build
##   docker compose run --rm web python manage.py migrate --noinput
##   docker compose up -d

# ── Stage 1: install Python dependencies ──────────────────────────────────────
FROM python:3.12.7-slim AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      libpq-dev \
      curl \
      ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and normalize encoding (Windows may save as UTF-16)
COPY requirements.txt /app/requirements.txt

RUN python - << 'PY'
import io, os
src = "requirements.txt"
with open(src, "rb") as f:
    raw = f.read()
data = None
for enc in ("utf-8", "utf-16", "utf-16-le", "utf-16-be"):
    try:
        data = raw.decode(enc).replace("\r\n", "\n")
        break
    except UnicodeDecodeError:
        continue
if data is None:
    data = raw.decode("utf-8", errors="replace")
with io.open(src, "w", encoding="utf-8") as f:
    f.write(data)
PY

RUN pip install --upgrade pip && pip install -r requirements.txt


# ── Stage 2: Runtime image (Django + Gunicorn + Celery) ───────────────────────
FROM python-base AS runtime

WORKDIR /app

# Non-root user for security
RUN useradd -ms /bin/bash django

# Copy backend project source
COPY . /app/

# Collect Django static files at build time
# Dummy SECRET_KEY is only used here — overridden at runtime via .env
RUN SECRET_KEY=docker-build-only-dummy-key \
    DATABASE_URL=sqlite:////tmp/build.db \
    python manage.py collectstatic --noinput --clear

# Ensure media directory exists and is writable by the django user
RUN mkdir -p /app/media && chown -R django:django /app/media

USER django

ENV GUNICORN_BIND=0.0.0.0:8000 \
    GUNICORN_WORKERS=3 \
    GUNICORN_TIMEOUT=300

EXPOSE 8000

# Default = web server. docker-compose overrides CMD for worker and beat.
CMD ["sh", "-c", "gunicorn itinfra.wsgi:application --bind ${GUNICORN_BIND} --workers ${GUNICORN_WORKERS} --timeout ${GUNICORN_TIMEOUT}"]
