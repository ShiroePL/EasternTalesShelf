FROM python:3.10-slim

# Set environment variables early
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set working directory early (light operation)
WORKDIR /app

# Install system dependencies and Doppler CLI
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev ffmpeg curl gnupg && \
    curl -Ls https://cli.doppler.com/install.sh | sh && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies separately
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code last
COPY . .

# Label (best placed last, doesn't affect build performance)
LABEL org.opencontainers.image.description="🐉 Eastern Tales Shelf - A Flask-based web application for managing and enjoying Korean manhwas and Japanese novels. Utilizes Gunicorn for serving, Doppler for secure environment management, and Docker Compose for deployment simplicity. Crafted with 💖 by ShiroePL."

CMD ["doppler", "run", "--", "gunicorn", "--bind", "0.0.0.0:80", "--workers", "4", "app.app:app"]
