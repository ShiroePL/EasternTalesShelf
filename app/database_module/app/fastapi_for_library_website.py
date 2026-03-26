import logging
import traceback
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import subprocess
from datetime import datetime

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create a logger object
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://shiropc.bun-ladon.ts.net"],  # Update this to the specific origins you want to allow or "*" for all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.post("/sync")
async def run_script():
    current_time = datetime.now()  # Get the current date and time
    logger.info(f"---Running sync script at {current_time}---")  # Log the date and time
    try:
        subprocess.run(["python", "update_only_manga.py"], check=True)
        logger.info(f"---Update Script executed successfully at {current_time}---")

        return {"status": "success", "message": "Script executed successfully"}
    except subprocess.CalledProcessError as e:
        logger.error(f"---Script execution failed at {current_time}---")
        logger.error(str(e))
        logger.error(traceback.format_exc())  # Log the full traceback
        return {"status": "failed", "message": "Script failed"}


@app.post("/weekly-metadata-update")
async def run_weekly_metadata_update(background_tasks: BackgroundTasks):
    """
    Trigger the weekly metadata update manually.
    Runs in the background to avoid timeout issues.
    """
    current_time = datetime.now()
    logger.info(f"---Weekly metadata update triggered at {current_time}---")
    
    def run_update():
        try:
            logger.info("Starting weekly metadata update...")
            result = subprocess.run(
                ["python", "weekly_metadata_update.py"],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("Weekly metadata update completed successfully")
            logger.info(f"Output: {result.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Weekly metadata update failed: {e}")
            logger.error(f"Error output: {e.stderr}")
            logger.error(traceback.format_exc())
    
    # Add the task to background tasks
    background_tasks.add_task(run_update)
    
    return {
        "status": "started",
        "message": "Weekly metadata update started in background. Check logs for progress.",
        "started_at": current_time.isoformat()
    }


@app.get("/weekly-metadata-update/status")
async def get_weekly_update_status():
    """
    Get the status of the last weekly metadata update from the log file.
    """
    try:
        with open("/var/log/weekly_metadata_update.log", "r") as f:
            # Read last 100 lines
            lines = f.readlines()[-100:]
            return {
                "status": "success",
                "log_excerpt": "".join(lines)
            }
    except FileNotFoundError:
        return {
            "status": "not_found",
            "message": "No update has been run yet"
        }
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# Optional: Add more routes as needed
