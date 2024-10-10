import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading
import os
import re
import sqlite3
import winreg
from installer_gui_elements import PythonInstallerApp
from take_full_manga_list_sqllite_tkinter import start_backup
import concurrent.futures

DARK_BG = "#2D2D2D"
DARK_TEXT = "#EAEAEA"
DARK_SIDEBAR = "#404040"
DARK_BUTTON_BG = "#5C5C5C"
DARK_BUTTON_FG = "#EAEAEA"

color_map = {
    "\033[31m": 'red',
    "\033[32m": 'green',
    "\033[33m": 'yellow',
    "\033[34m": 'blue',
    "\033[35m": 'magenta',
    "\033[36m": 'cyan',
    "\033[37m": 'white',
    "\033[0m": 'white',  # Reset to default
}

database_path = 'app/anilist_db.db'

def check_database_exists():
    return os.path.exists(database_path)

def validate_database_structure():
    try:
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            # Example: Check for a specific table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='your_table_name';")
            return bool(cursor.fetchone())
    except sqlite3.Error as e:
        print(f"Database validation error: {e}")
        return False

class PythonInstaller:
    def __init__(self, root):
        # Initialize GUI using the class from installer_gui.py
        self.gui = PythonInstallerApp(root, self.run_installation)
         
        # Store Python paths
        self.python_paths = {}
        self.selected_python_path = None

        # Scan for Python versions on startup
        self.scan_for_python_versions()

       



    def scan_for_python_versions(self):
        found_python_paths = []

        # Check common locations
        self.check_common_python_locations(found_python_paths)
        # Check Windows registry
        self.check_python_in_registry(found_python_paths)

        # Determine the Python version to use
        if found_python_paths:
            for python_path in found_python_paths:
                python_version = self.extract_python_version(python_path)
                if python_version:
                    self.python_paths[python_version] = python_path

            if "Python 3.10" in self.python_paths:
                self.selected_python_path = self.python_paths["Python 3.10"]
            elif "Python 3.11" in self.python_paths:
                self.selected_python_path = self.python_paths["Python 3.11"]
            else:
                self.update_output("Python 3.10 or higher is required. Please install Python 3.10 or 3.11 to proceed.")
                return

            self.gui.install_button.configure(state="normal")
        else:
            self.gui.install_button.configure(state="disabled")

    def check_common_python_locations(self, found_python_paths):
        common_paths = [
            r"C:\Python310\python.exe",
            r"C:\Python311\python.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Python\Python310\python.exe"),
            os.path.expanduser(r"~\AppData\Local\Programs\Python\Python311\python.exe")
        ]
        for path in common_paths:
            if os.path.exists(path):
                found_python_paths.append(path)

    def check_python_in_registry(self, found_python_paths):
        python_key_path = r"SOFTWARE\Python\PythonCore"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, python_key_path) as python_key:
                for i in range(winreg.QueryInfoKey(python_key)[0]):
                    version_key = winreg.EnumKey(python_key, i)
                    with winreg.OpenKey(python_key, version_key) as subkey:
                        install_path = winreg.QueryValue(subkey, "InstallPath")
                        python_exe = os.path.join(install_path, "python.exe")
                        if os.path.exists(python_exe):
                            found_python_paths.append(python_exe)
        except OSError:
            pass

    def extract_python_version(self, python_path):
        match = re.search(r"Python(\d)(\d{2})", python_path)
        if match:
            major, minor = match.groups()
            return f"Python {major}.{minor}"
        return None
    

    

    


    def run_requirements_installation_process(self):
        try:
            command = [self.selected_python_path, "install_requirements.py"]
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            for stdout_line in iter(process.stdout.readline, ""):
                self.update_output(stdout_line)

            for stderr_line in iter(process.stderr.readline, ""):
                self.update_output(f"ERROR: {stderr_line}")

            process.stdout.close()
            process.stderr.close()
            process.wait()
            self.update_output("Installation Complete!\n")
        except Exception as e:
            self.update_output(f"Error: {str(e)}\n")

    

    
    def update_output(self, message):
        self.gui.output_text.configure(state='normal')
        tag_name = None  # Initialize tag_name to None

        # Split message by ANSI codes and process each part
        for part in re.split('(\033\[\d+m)', message):
            color_code = color_map.get(part, None)
            if color_code:  # If part is a color code, update tag_name
                tag_name = color_code
                self.gui.output_text.tag_configure(tag_name, foreground=color_code)
            elif tag_name:  # If part is text and tag_name is set, insert with color
                self.gui.output_text.insert(tk.END, part, tag_name)
            else:  # If part is text but no color tag is set, insert without color
                self.gui.output_text.insert(tk.END, part)

        self.gui.output_text.insert(tk.END, "\n")  # Ensure newline at the end
        self.gui.output_text.configure(state='disabled')
        self.gui.output_text.see(tk.END)

    def start_backup_fn(self):
        self.update_output("Running backup function...\n")

        # Define the path to the virtual environment Python interpreter
        venv_python = os.path.join("venv", "Scripts", "python.exe") if os.name == "nt" else os.path.join("venv", "bin", "python")

        # Taking the values from the GUI
        values = self.gui.get_all_values()

        input_value = values['username_or_id']
        db_type = values['db_type_radiobutton']

        if not input_value:
            tk.messagebox.showerror("Error", "You need to enter a value!")
            return

        # Run the backup in a separate thread
        threading.Thread(target=self._run_backup_process, args=(venv_python, input_value, db_type), daemon=True).start()

    def _run_backup_process(self, venv_python, input_value, db_type):
        try:
            command = [venv_python, "take_full_manga_list_sqllite_tkinter.py", "--input_value", input_value, "--db_type", db_type]
            
            # Copy the current environment and set the encoding to UTF-8
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'

            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
            )

            # Read stdout and stderr as bytes and then decode manually
            for stdout_line in iter(process.stdout.readline, b""):
                decoded_line = stdout_line.decode('utf-8', errors='replace')
                self.update_output(decoded_line.strip())

            for stderr_line in iter(process.stderr.readline, b""):
                decoded_line = stderr_line.decode('utf-8', errors='replace')
                self.update_output(f"ERROR: {decoded_line.strip()}")

            process.stdout.close()
            process.stderr.close()
            process.wait()

            if process.returncode == 0:
                self.update_output("Backup process completed successfully.\n")
            else:
                self.update_output(f"Backup process failed with return code {process.returncode}.\n")

        except Exception as e:
            self.update_output(f"Error during backup process: {str(e)}\n")


            


    def run_installation(self):
        ## taking the values from the GUI
        values = self.gui.get_all_values()
        print(f"Values: {values}")

        if self.selected_python_path:
            self.update_output(f"Starting installation with {self.selected_python_path}...\n")

            ## Check if 'venv' directory already exists
            if os.path.exists("venv"):
                self.update_output("Virtual environment already exists. Skipping installation.\n")
                print("Virtual environment already exists. Skipping installation.\n")
            else:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    # Run the actual installation and wait for it to complete
                    future = executor.submit(self.run_requirements_installation_process)
                    concurrent.futures.wait([future])

                self.update_output("Successfully installed requirements in virtual environment\n")
                print("Successfully installed requirements in virtual environment.\n")

            ## we makng ifs if user chose to crate db, and what type , file or mariadb

            if values['create_db_radiobutton'] == 'Yes':
                self.update_output("You chose to create a database.\n")

                if values['db_type_radiobutton'] == 'file':
                    self.update_output("We will create a file database. SQllite\n")
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future_backup = executor.submit(self.start_backup_fn)
                        concurrent.futures.wait([future_backup])
                        
                    self.update_output("Database created.\n")
                else:
                    self.update_output("We will create a MariaDB database.\n")
                    self.update_output("Database created.\n")
                
            else:
                self.update_output("You chose not to create a database.\n")
                
            

            

        else:
            self.update_output("No Python installation found. Please install Python 3.10 or higher to proceed.")
            self.gui.install_button.configure(state="disabled")

        


if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)  # Set DPI awareness for Windows
    except:
        pass

    installer = PythonInstaller(root)
    root.mainloop()