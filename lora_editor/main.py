"""
Main entry point for LoRA Editor
"""
import tkinter as tk
import logging
import os
import sys
from pathlib import Path
from ttkthemes import ThemedTk

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

# Use direct import for app.py in the same directory
from app import LoraEditorApp

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main entry point"""
    try:
        # Use themed Tk for better appearance
        root = ThemedTk(theme="equilux")
        root.title("LoRA Configuration Editor")

        # Create and run application
        app = LoraEditorApp(root)
        app.run()
    except Exception as e:
        logger.error(f"Error in main: {e}")
        if hasattr(tk, 'messagebox'):
            tk.messagebox.showerror("Error", f"Application error: {str(e)}")

if __name__ == "__main__":
    main()
