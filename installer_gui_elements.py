from pathlib import Path
from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage, ttk, BooleanVar, StringVar

class PythonInstallerApp:
    def __init__(self, root, install_callback):
        self.root = root
        self.root.geometry("1000x700")
        self.root.configure(bg="#24282D")
        self.font_family = "Baloo Bhai 2 SemiBold"
        # Define paths
        self.OUTPUT_PATH = Path(__file__).parent
        self.ASSETS_PATH = self.OUTPUT_PATH / "gui_images"
        # Store the callback function
        self.install_callback = install_callback
        # Create the canvas
        self.canvas = Canvas(
            self.root,
            bg="#24282D",
            height=700,
            width=1000,
            bd=0,
            highlightthickness=0,
            relief="ridge"
        )
        self.canvas.place(x=0, y=0)

        # Create UI elements using the generated design
        self.create_ui_elements()

        


        # Prevent resizing
        self.root.resizable(False, False)

    def for_mariadb_db_fn(self, *args):
        """Callback for when the user changes the MariaDB database radiobutton"""
        if self.db_type_variable.get() == "file":
            # Hide all input fields and related images
            print("Hiding database inputs")

            # Hide entry images
            self.canvas.itemconfig(self.db_password_image_id, state='hidden')
            self.canvas.itemconfig(self.db_username_image_id, state='hidden')
            self.canvas.itemconfig(self.db_hostname_image_id, state='hidden')
            self.canvas.itemconfig(self.db_name_image_id, state='hidden')
            
            # Hide text images above inputs
            self.canvas.itemconfig(self.image_5_id, state='hidden')
            self.canvas.itemconfig(self.image_13_id, state='hidden')
            self.canvas.itemconfig(self.image_14_id, state='hidden')
            self.canvas.itemconfig(self.image_15_id, state='hidden')
            self.canvas.itemconfig(self.image_16_id, state='hidden')

            # Hide entry fields
            self.db_password_input.place_forget()
            self.db_username_input.place_forget()
            self.db_hostname_input.place_forget()
            self.db_name_input.place_forget()

            
        elif self.db_type_variable.get() == "MariaDB":
            # Show all input fields and related images
            print("Showing database inputs")

            # Show entry images
            self.canvas.itemconfig(self.db_password_image_id, state='normal')
            self.canvas.itemconfig(self.db_username_image_id, state='normal')
            self.canvas.itemconfig(self.db_hostname_image_id, state='normal')
            self.canvas.itemconfig(self.db_name_image_id, state='normal')

            # Show text images above inputs
            self.canvas.itemconfig(self.image_5_id, state='normal')
            self.canvas.itemconfig(self.image_13_id, state='normal')
            self.canvas.itemconfig(self.image_14_id, state='normal')
            self.canvas.itemconfig(self.image_15_id, state='normal')
            self.canvas.itemconfig(self.image_16_id, state='normal')

            # Show entry fields
            self.db_password_input.place(x=555.0, y=179.0, width=80.0, height=14.0)
            self.db_username_input.place(x=456.0, y=179.0, width=80.0, height=14.0)
            self.db_hostname_input.place(x=555.0, y=147.0, width=80.0, height=14.0)
            self.db_name_input.place(x=456.0, y=147.0, width=80.0, height=14.0)

           

    def create_db_or_not_fn(self, *args):
        """Callback for when the user changes the 'Create DB' radiobutton"""
        if self.create_db_variable.get() == "No":
            self.canvas.itemconfig(self.image_7_id, state='hidden')
            # Hide db_type radio buttons
            self.db_type_file.place_forget()
            self.db_type_mariadb.place_forget()
            
            # reset radiobutton
            self.db_type_variable.set("file")
            print("Hiding db type")

        elif self.create_db_variable.get() == "Yes":
            self.canvas.itemconfig(self.image_7_id, state='normal')
             # Show db_type radio buttons
            self.db_type_file.place(x=686.0, y=95.0)
            self.db_type_mariadb.place(x=742.0, y=95.0)
            print("Showing db type")


    def relative_to_assets(self, path: str) -> Path:
        return self.ASSETS_PATH / Path(path)

    def create_ui_elements(self):
        

        # Make image an attribute of the class
        self.install_button_image_1 = PhotoImage(
            file=self.relative_to_assets("button_1.png"))
        
        # Use self.install_button_image_1 here
        self.install_button = Button(
            image=self.install_button_image_1,
            borderwidth=0,
            highlightthickness=0,
            command=self.install_callback,
            relief="flat"
        )
        self.install_button.place(
            x=367.0,
            y=216.0,
            width=253.0,
            height=40.0
        )

        self.output_text_img = PhotoImage(
            file=self.relative_to_assets("entry_1.png"))
        self.canvas.create_image(
            500.0,
            465.5,
            image=self.output_text_img
        )

        # Creating the Text widget for logs and overlaying it on the background
        self.output_text = Text(
            bd=0,
            wrap="word",  # Wrap text by word for readability
            padx=10,
            pady=10,
            bg="#212529",  # Background of Text widget matches the dark rectangle
            fg="white",  # Light text color for contrast
            highlightthickness=0,
            font=(self.font_family, 12)  # Use any suitable font and size you prefer
        )
        self.output_text.place(
            x=72.0,
            y=259.0,
            width=856.0,
            height=411.0
        )
        self.output_text.config(state="disabled") # not editable as its for logs


        ###############################################################################################
        
        # Create the Radiobutton widgets style
        style = ttk.Style()
        # Configure the custom radio button style
        style.layout("Custom.TRadiobutton", [
            ("Custom.TRadiobutton.focus", {"children":
                [("Custom.TRadiobutton.indicator", {"side": "left", "sticky": ""}),
                ("Custom.TRadiobutton.padding", {"expand": "1", "sticky": "nswe", "children":
                    [("Custom.TRadiobutton.label", {"sticky": "nswe"})]
                })
                ]
            })
        ])

        style.configure("Custom.TRadiobutton", background="#24282d", foreground="#FFFFFF", font=(self.font_family, 11))
        style.map("Custom.TRadiobutton", background=[("active", "#24282d")])

        # Make images instance variables to avoid garbage collection
        self.normal_image = PhotoImage(file=self.relative_to_assets("orange_unselected.png"))
        self.selected_image = PhotoImage(file=self.relative_to_assets("orange_selected.png"))

        # Ensure images persist in the widget
        style.element_create("Custom.TRadiobutton.indicator", "image", self.normal_image,
                            ("selected", self.selected_image),
                            sticky="", padding=2)


        ###################
        # radio buttons
        
                
          
        # Radio button for db creation
        self.create_db_variable = StringVar()  # Make this an instance variable
        self.create_db_variable.set("No")
        self.create_db_variable.trace("w", self.create_db_or_not_fn)  # Listen for state changes and trigger the function
        self.create_db_yes = ttk.Radiobutton(self.root, text=" Yes", variable=self.create_db_variable, value="Yes", style="Custom.TRadiobutton")
        self.create_db_no = ttk.Radiobutton(self.root, text=" No", variable=self.create_db_variable, value="No", style="Custom.TRadiobutton")

        self.create_db_yes.place(x=249.0, y=95.0)
        self.create_db_no.place(x=304.0, y=95.0)


        # New Radio button for db_type
        self.db_type_variable = StringVar()  # New variable for the type of database
        self.db_type_variable.set("file")  # Default to 'file'
        self.db_type_variable.trace("w", self.for_mariadb_db_fn) 
        # Add tracing for db_type, if needed
        # self.db_type_variable.trace("w", some_function_to_handle_db_type_change)  # Optional: add a function to handle changes

        self.db_type_file = ttk.Radiobutton(self.root, text=" File", variable=self.db_type_variable, value="file", style="Custom.TRadiobutton")
        self.db_type_mariadb = ttk.Radiobutton(self.root, text=" MariaDB", variable=self.db_type_variable, value="MariaDB", style="Custom.TRadiobutton")

        # Positioning for the new radio buttons
        self.db_type_file.place(x=686.0, y=95.0)
        self.db_type_mariadb.place(x=742.0, y=95.0)






        ###############################################################################################


        

       # Entry 2: Setting up the background image and overlaying the Entry widget
        self.db_password_input_image_2 = PhotoImage(
            file=self.relative_to_assets("entry_2.png"))
        self.db_password_image_id = self.canvas.create_image(595.0, 187.0, image=self.db_password_input_image_2)

        self.db_password_input = Entry(
            bd=0,
            bg="#992b28",  # Set the background to match the dark background image
            fg="white",  # Light text color for readability
            font=(self.font_family, 12),  # Use a suitable font and size
            highlightthickness=0,
            insertbackground="#A8E1F6"  # Set the cursor color to match the text color
        )
        

        # Entry 3: Setting up the background image and overlaying the Entry widget
        self.db_username_input_image_3 = PhotoImage(
            file=self.relative_to_assets("entry_3.png"))
        self.db_username_image_id = self.canvas.create_image(496.0, 187.0, image=self.db_username_input_image_3)

        self.db_username_input = Entry(
            bd=0,
            bg="#992b28",  # Set the background to match the dark background image
            fg="white",  # Light text color for readability
            font=(self.font_family, 12),  # Use a suitable font and size
            highlightthickness=0,
            insertbackground="#A8E1F6"  # Set the cursor color to match the text color
        )
        

        # Entry 4: Setting up the background image and overlaying the Entry widget
        self.db_hostname_input_image_4 = PhotoImage(
            file=self.relative_to_assets("entry_4.png"))
        self.db_hostname_image_id = self.canvas.create_image(595.0, 155.0, image=self.db_hostname_input_image_4)

        self.db_hostname_input = Entry(
            bd=0,
            bg="#992b28",  # Set the background to match the dark background image
            fg="white",  # Light text color for readability
            font=(self.font_family, 12),  # Use a suitable font and size
            highlightthickness=0,
            insertbackground="#A8E1F6"  # Set the cursor color to match the text color
        )
        

        # Entry 5: Setting up the background image and overlaying the Entry widget
        self.db_name_input_image_5 = PhotoImage(
            file=self.relative_to_assets("entry_5.png"))
        
        self.db_name_image_id = self.canvas.create_image(496.0, 155.0, image=self.db_name_input_image_5)

        self.db_name_input = Entry(
            bd=0,
            bg="#992b28",  # Set the background to match the dark background image
            fg="white",  # Light text color for readability
            font=(self.font_family, 12),  # Use a suitable font and size
            highlightthickness=0,
            insertbackground="#A8E1F6"  # Set the cursor color to match the text color
        )
        
        

        # Setting up the background image
        self.username_input_img = PhotoImage(
            file=self.relative_to_assets("entry_6.png"))
        self.canvas.create_image(
            345.0,
            184.0,
            image=self.username_input_img
        )

        # Creating the Entry widget for user input and overlaying it on the background
        self.username_input = Entry(
            bd=0,
            bg="#992b28",  # Set the background to match or be transparent on the dark background image
            fg="white",  # Light text color for readability
            font=(self.font_family, 12),  # Use a suitable font and size
            highlightthickness=0,
            insertbackground="#A8E1F6"  # Set the cursor color to be consistent with the text color
        )
        self.username_input.place(
            x=258.0,
            y=174.0,
            width=177.0,
            height=22.0
        )


        self.image_ids = {}

        # Create a list of image data, image name, x, and y coordinates
        image_data = [
            ("image_1.png", 694.0, 684.0),
            ("image_2.png", 133.0, 242.0),
            ("image_3.png", 133.0, 219.0),
            ("image_4.png", 829.0, 191.0),
            ("image_5.png", 496.0, 110.0),
            ("image_6.png", 424.0, 85.0),
            ("image_7.png", 747.0, 81.0),
            ("image_8.png", 500.0, 39.0),
            ("image_9.png", 344.0, 150.0),
            ("image_10.png", 976.0, 677.0),
            ("image_11.png", 927.0, 70.0),
            ("image_12.png", 133.0, 107.0),
            ("image_13.png", 594.0, 209.0),
            ("image_14.png", 496.0, 132.0),
            ("image_15.png", 595.0, 132.0),
            ("image_16.png", 496.0, 209.0)
        ]

        # Create images and store their IDs in a dictionary
        for index, (file_name, x, y) in enumerate(image_data, start=1):
            image_attr = f"image_image_{index}"
            image_id_attr = f"image_{index}_id"
            setattr(self, image_attr, PhotoImage(file=self.relative_to_assets(file_name)))
            image_id = self.canvas.create_image(x, y, image=getattr(self, image_attr))
            setattr(self, image_id_attr, image_id)
            self.image_ids[image_id_attr] = image_id

                

        # Initially hide all entries and images as 'Create DB' is set to 'No'
        self.for_mariadb_db_fn(self)
        self.create_db_or_not_fn(self)

    # Getter method for DB name
    def get_db_name(self):
        return self.db_name_input.get()

    # Getter method for DB name
    def get_db_name(self):
        return self.db_password_input.get()

    # Getter method for Username
    def get_username(self):
        return self.db_username_input.get()
    
    def get_username(self):
        return self.username_input.get()


if __name__ == "__main__":
    window = Tk()
    app = PythonInstallerApp(window)
    window.mainloop()