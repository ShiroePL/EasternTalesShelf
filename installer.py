import tkinter as tk
import subprocess
import os
import re
import threading
import winreg
from installer_gui_elements import PythonInstallerApp


class PythonInstaller:
    def __init__(self, root):
        # Initialize GUI using the class from installer_gui.py
        self.gui = PythonInstallerApp(root)

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
            self.update_output("No Python installation found. Please install Python 3.10 or higher to proceed.")
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

    def start_installation(self):
        if self.selected_python_path:
            self.gui.output_text.delete("1.0", "end")
            self.update_output(f"Starting installation with {self.selected_python_path}...\n")
            threading.Thread(target=self.run_installation).start()

    def run_installation(self):
        try:
            command = [self.selected_python_path, "install.py"]
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
        self.gui.output_text.insert("end", message)
        self.gui.output_text.see("end")


if __name__ == "__main__":
    root = tk.Tk()
    # Make tkinter look sharper by setting DPI awareness
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)  # Set DPI awareness for Windows
    except:
        pass
    
    installer = PythonInstaller(root)
    root.mainloop()