import os
import subprocess
import sys
import time

# Define the virtual environment directory
venv_dir = "venv"

def create_virtualenv():
    """Create a virtual environment."""
    print("Step 1: Creating virtual environment...", flush=True)

    # Create the virtual environment
    subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
    print("Virtual environment created.", flush=True)

def install_dependencies():
    """Install dependencies in the virtual environment."""
    print("Step 2: Installing dependencies...", flush=True)

    # Activate the virtual environment and install dependencies
    venv_python = os.path.join(venv_dir, "Scripts", "python.exe" if os.name == "nt" else "bin/python")
    
    # Use the venv Python to install dependencies from requirements.txt
    subprocess.run([venv_python, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    print("Dependencies installed.", flush=True)

def run_installation():
    """Run the installation process."""
    # Step 1: Create virtual environment
    create_virtualenv()

    # Step 2: Install dependencies
    install_dependencies()

    print("Step 3: Finalizing installation...", flush=True)
    time.sleep(1)

if __name__ == "__main__":
    run_installation()
