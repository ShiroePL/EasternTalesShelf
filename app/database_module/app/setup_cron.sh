#!/bin/bash

# Setup cron job for weekly metadata update
# This script is run when the container starts

echo "Setting up weekly metadata update cron job..."

# Create cron job that runs every Sunday at 3 AM
CRON_SCHEDULE="0 3 * * 0"
CRON_COMMAND="cd /app && /usr/local/bin/python weekly_metadata_update.py >> /var/log/weekly_metadata_update.log 2>&1"

# Add cron job to crontab
(crontab -l 2>/dev/null | grep -v "weekly_metadata_update.py"; echo "$CRON_SCHEDULE $CRON_COMMAND") | crontab -

# Create log file if it doesn't exist
touch /var/log/weekly_metadata_update.log

echo "Cron job installed successfully!"
echo "Schedule: Every Sunday at 3:00 AM"
echo "Log file: /var/log/weekly_metadata_update.log"

# Display current crontab
echo -e "\nCurrent crontab:"
crontab -l
