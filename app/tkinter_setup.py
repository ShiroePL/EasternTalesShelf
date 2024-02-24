import tkinter as tk
from tkinter import scrolledtext
from subprocess import Popen, PIPE
import threading
from take_full_manga_list_sqllite import start_backup
import re
import os
import sqlite3

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
database_path = 'anilist_db.db'

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



class App:
    def __init__(self, root):
        # Initialization and setup...
        if not check_database_exists() or not validate_database_structure():
            self.setup_database_ui()
        else:
            self.setup_flask_config_ui()
        

        self.root = root
        self.root.title("One-Click Installer")
        self.root.configure(bg=DARK_BG)

        # Sidebar for inputs
        self.sidebar = tk.Frame(self.root, width=200, bg=DARK_SIDEBAR, height=500, relief='sunken', borderwidth=2)
        self.sidebar.pack(expand=False, fill='y', side='left', anchor='nw')

        # Terminal-like output
        self.output = scrolledtext.ScrolledText(self.root, bg=DARK_BG, fg=DARK_TEXT)
        self.output.pack(expand=True, fill='both', side='right')
        self.output.configure(font='Consolas 10')  # Set a more terminal-like font

        self.choice_var = tk.StringVar(value="1")  # Default to "1" for ID
        self.input_var = tk.StringVar()
        # Input fields
        self.setup_input_fields()
        

        
    def setup_input_fields(self):
        # Radio buttons for choosing between ID and Name
        tk.Radiobutton(self.sidebar, text="ID", variable=self.choice_var, value="1", bg=DARK_SIDEBAR, fg=DARK_TEXT).pack(anchor='w')
        tk.Radiobutton(self.sidebar, text="Name", variable=self.choice_var, value="2", bg=DARK_SIDEBAR, fg=DARK_TEXT).pack(anchor='w')

        # Shared Entry field for input
        self.input_entry = tk.Entry(self.sidebar, bg=DARK_BG, fg=DARK_TEXT, insertbackground=DARK_TEXT, textvariable=self.input_var)
        self.input_entry.pack()

        # Start button
        start_button = tk.Button(self.sidebar, text="Start", command=self.start_backup, bg=DARK_BUTTON_BG, fg=DARK_BUTTON_FG)
        start_button.pack(pady=10)

    def start_backup(self):
        id_or_name = self.choice_var.get()  # "1" for ID, "2" for name
        if input_value := self.input_var.get().strip():
            # Call the start_backup function in a new thread to keep the UI responsive
            threading.Thread(target=lambda: self.run_backup_function(id_or_name, input_value), daemon=True).start()
        else:
            tk.messagebox.showerror("Error", "You need to enter a value!")

    def run_backup_function(self, id_or_name, input_value):
        # Modify this to call start_backup with a logger function
        try:
            # Pass a lambda or wrapper function as the logger argument
            start_backup(id_or_name, input_value, self.print_to_terminal)
            self.print_to_terminal("Backup process completed successfully.\n")
        except Exception as e:
            self.print_to_terminal(f"Error during backup process: {e}\n")


    def print_to_terminal(self, message):
        def cmd():
            self.output.configure(state='normal')
            tag_name = None  # Initialize tag_name to None

            # Split message by ANSI codes and process each part
            for part in re.split('(\033\[\d+m)', message):
                color_code = color_map.get(part, None)
                if color_code:  # If part is a color code, update tag_name
                    tag_name = color_code
                    self.output.tag_configure(tag_name, foreground=color_code)
                elif tag_name:  # If part is text and tag_name is set, insert with color
                    self.output.insert(tk.END, part, tag_name)
                else:  # If part is text but no color tag is set, insert without color
                    self.output.insert(tk.END, part)
                    
            self.output.insert(tk.END, "\n")  # Ensure newline at the end
            self.output.configure(state='disabled')
            self.output.see(tk.END)
        self.root.after(0, cmd)



    def interpret_color_codes(self, message):
        # Example: Extracting and interpreting the color from the message
        # This is a simplified approach; adjust according to your actual color codes and messages
        color_pattern = re.compile(r'\{([A-Z]+)\}')  # Adjust regex based on actual pattern
        if match := color_pattern.search(message):
            color_code = match.group(1)
            color = color_map.get(color_code, 'white')  # Default to white if not found
            clean_message = color_pattern.sub("", message)  # Remove the color code from the message
            return clean_message, color
        return message, None


    def run_backup_script(self):
        # Replace "python start_backup.py" with the actual command you need to run
        process = Popen(["python", "start_backup.py"], stdout=PIPE, stderr=PIPE, text=True)
        for line in process.stdout:
            self.print_to_terminal(line)
        process.stdout.close()
        if return_code := process.wait():
            self.print_to_terminal(f"Error, check the script. Return code: {return_code}\n")


if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()
