import requests
import logging
from app.config import fastapi_updater_server_IP

def perform_sync_with_fastapi():
    """
    Connects to the FastAPI server to trigger a sync.
    Returns a tuple (success, data).
    """
    try:
        url = f"http://{fastapi_updater_server_IP}:8057/sync"
        logging.info(f"Connecting to FastAPI at: {url}")
        response = requests.post(url, timeout=10)

        if response.status_code == 200:
            logging.info("Synced successfully with FastAPI")
            try:
                return True, response.json()
            except ValueError:
                return True, {} # Return empty dict if no json
        else:
            logging.error(f"Failed to sync with FastAPI. Status code: {response.status_code}")
            return False, None
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while connecting to FastAPI: {str(e)}")
        return False, None
