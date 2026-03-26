#!/bin/bash

# Manual trigger for weekly metadata update
# Run this script to manually update manga metadata without waiting for the cron schedule

echo "=========================================="
echo "Manual Metadata Update Trigger"
echo "=========================================="
echo ""

# Check if running in Docker container
if [ -f /.dockerenv ]; then
    echo "Running inside Docker container..."
    cd /app
    doppler run -- python weekly_metadata_update.py
else
    echo "Running outside Docker container..."
    cd "$(dirname "$0")"
    python weekly_metadata_update.py
fi

echo ""
echo "=========================================="
echo "Update completed!"
echo "=========================================="
