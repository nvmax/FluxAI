"""
LoRA Editor Application
This module implements the main application class for the LoRA Editor using MVC pattern.
"""
import tkinter as tk
import logging
from ttkthemes import ThemedTk
from pathlib import Path
import sys

# Import MVC components
from models.lora_model import LoraModel
from views.main_view import MainView
from controllers.main_controller import MainController

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LoraEditorApp:
    """Main application class for the LoRA Editor"""

    def __init__(self, root: ThemedTk):
        """Initialize the application with the root window"""
        self.root = root
        self.model = None
        self.view = None
        self.controller = None

        # Configure the root window
        self.root.title("LoRA Configuration Editor")
        self.root.geometry("1400x925")
        self.root.minsize(1200, 800)

        # Initialize MVC components
        self._init_mvc()

    def _init_mvc(self):
        """Initialize the Model-View-Controller components"""
        try:
            # Create model
            self.model = LoraModel()

            # Create view
            self.view = MainView(self.root)

            # Create controller
            self.controller = MainController(self.model, self.view)

            logger.info("MVC components initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing MVC components: {e}")
            tk.messagebox.showerror("Error", f"Failed to initialize application: {str(e)}")

    def run(self):
        """Run the application main loop"""
        try:
            # Center the window on the screen
            self.center_window()

            # Start the main loop
            self.root.mainloop()
        except Exception as e:
            logger.error(f"Error running application: {e}")
            tk.messagebox.showerror("Error", f"Application error: {str(e)}")

    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
