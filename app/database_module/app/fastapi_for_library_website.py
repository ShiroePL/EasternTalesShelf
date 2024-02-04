from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import subprocess
from datetime import datetime  # Import datetime module


app = FastAPI()



@app.post("/sync")
async def run_script():
    current_time = datetime.now()  # Get the current date and time
    print(f"---Running script at {current_time}---")  # Print the date and time
    try:
        subprocess.run(["python", "update_only_manga.py"], check=True)
        print(f"---Script executed successfully at {current_time}---")
        return {"status": "success", "message": "Script executed successfully"}
    except subprocess.CalledProcessError as e:
        print(f"---Script execution failed at {current_time}---")
        return {"status": "error", "message": str(e)}

# Optional: Add more routes as needed

# If you're using Uvicorn to run the app, don't forget to start it with:
# uvicorn your_app_module:app --host 0.0.0.0 --port 8000
# Replace `your_app_module` with the name of your Python file containing the FastAPI app
