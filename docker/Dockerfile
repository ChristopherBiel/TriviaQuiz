# Use a slim base image for better compatibility with binary wheels
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    python -m pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY . .

# Download self-hosted assets (fonts + Tailwind) for GDPR compliance.
# These are not committed to git; they are fetched fresh on each image build.
RUN python scripts/download_assets.py

EXPOSE 5600

RUN useradd -u 5678 -m appuser
USER appuser

CMD ["gunicorn", "--bind", "0.0.0.0:5600", "wsgi:app"]
