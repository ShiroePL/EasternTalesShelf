# Navigate to the directory containing this script
cd $PSScriptRoot

# Activate the virtual environment
& .\venv\Scripts\Activate

# Run the application with terminal output visible
doppler run -- python -m app.app

# Keep the PowerShell window open
Read-Host -Prompt "Press Enter to exit"

# Deactivate virtual environment after the script completes
deactivate
