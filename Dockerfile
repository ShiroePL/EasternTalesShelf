# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables that persist in the container
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Provide image metadata and description
LABEL org.opencontainers.image.description="🐉 Eastern Tales Shelf - A Flask-based web application for managing and enjoying Korean manhwas and Japanese novels. Utilizes Gunicorn for serving, Doppler for secure environment management, and Docker Compose for deployment simplicity. Crafted with 💖 by ShiroePL."

# Install system dependencies and Doppler CLI
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev ffmpeg curl gnupg && \
    curl -Ls https://cli.doppler.com/install.sh | sh && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory to /app. This is the root of your project inside the container.
WORKDIR /app

# Set environment variable to ensure Python recognizes the correct root for imports
ENV PYTHONPATH=/app

# Copy the requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your entire app folder into /app, maintaining the structure
COPY . .

# Adjust PYTHONPATH if necessary
ENV PYTHONPATH=/app

# Use Doppler to inject secrets and run Gunicorn to serve your app
CMD ["doppler", "run", "--", "gunicorn", "--bind", "0.0.0.0:80", "--workers", "4", "app.app:app"]
