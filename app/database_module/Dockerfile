# Use Alpine as the base image
FROM alpine:3.17.3

# Update package list and install dependencies (including cron for scheduled tasks)
RUN apk update && \
    apk add --no-cache bash python3 py3-pip curl iptables iproute2 openrc dcron gnupg dos2unix && \
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

# Fix line endings for shell scripts (Windows CRLF -> Linux LF) and make executable
RUN dos2unix /app/setup_cron.sh /app/start.sh /app/run_weekly_update.sh && \
    chmod +x /app/setup_cron.sh /app/start.sh /app/run_weekly_update.sh

# Command to start both cron and FastAPI app with Doppler secrets injection
CMD ["/bin/bash", "/app/start.sh"]
