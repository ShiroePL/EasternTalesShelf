FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
# ffmpeg with --no-install-recommends to avoid GUI bloat
# curl and gnupg are needed for the Doppler install script
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl gnupg ca-certificates && \
    curl -Ls https://cli.doppler.com/install.sh | sh && \
    apt-get purge -y --auto-remove curl gnupg && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies (caching layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code last
COPY . .

LABEL org.opencontainers.image.description="🐉 Eastern Tales Shelf - A Flask-based web application for managing and enjoying Korean manhwas and Japanese novels. Utilizes Gunicorn for serving, Doppler for secure environment management, and Docker Compose for deployment simplicity. Crafted with 💖 by ShiroePL."

CMD ["doppler", "run", "--", "gunicorn", "--bind", "0.0.0.0:80", "--workers", "4", "app.app:app"]
