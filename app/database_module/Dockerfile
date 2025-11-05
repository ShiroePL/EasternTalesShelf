# Use Alpine as the base image
FROM alpine:3.17.3

# Update package list and install dependencies (including cron for scheduled tasks)
RUN apk update && \
    apk add --no-cache bash python3 py3-pip curl iptables iproute2 openrc dcron && \
    apk add build-base python3-dev libffi-dev

# Install Doppler CLI for secrets management
RUN curl -Ls https://cli.doppler.com/install.sh | sh

# Ensure openrc can run in Docker (you might remove this if openrc isn't needed)
RUN mkdir -p /run/openrc && \
    touch /run/openrc/softlevel

# Copy your FastAPI application and other necessary files
COPY ./app /app

# Set the working directory
WORKDIR /app

# Copy the requirements file and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Make the cron setup script executable
RUN chmod +x /app/setup_cron.sh

# Create a startup script that runs both cron and the FastAPI app
RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'doppler run -- /app/setup_cron.sh' >> /app/start.sh && \
    echo 'crond -b -l 2' >> /app/start.sh && \
    echo 'echo "Cron daemon started in background"' >> /app/start.sh && \
    echo 'exec doppler run -- uvicorn fastapi_for_library_website:app --host 0.0.0.0 --port 8057' >> /app/start.sh && \
    chmod +x /app/start.sh

# Command to start both cron and FastAPI app with Doppler secrets injection
CMD ["/app/start.sh"]
