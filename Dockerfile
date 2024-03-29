# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables that persist in the container
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev ffmpeg && \
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

# Adjust the CMD to reflect the new structure and execute the app
CMD ["gunicorn", "--bind", "0.0.0.0:80", "--workers", "4", "app.app:app"]
