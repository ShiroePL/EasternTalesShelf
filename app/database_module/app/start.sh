#!/bin/bash

# Ensure proper line endings and permissions (in case dos2unix didn't run)
dos2unix /app/setup_cron.sh 2>/dev/null || sed -i 's/\r$//' /app/setup_cron.sh
chmod +x /app/setup_cron.sh

# Setup cron job
doppler run -- bash /app/setup_cron.sh

# Start cron daemon in background
crond -b -l 2

echo "Cron daemon started in background"

# Start FastAPI server (foreground)
exec doppler run -- uvicorn fastapi_for_library_website:app --host 0.0.0.0 --port 8057
