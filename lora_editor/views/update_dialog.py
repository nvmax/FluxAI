"""
Dialog for displaying LoRA update information
"""
import tkinter as tk
from tkinter import ttk
import webbrowser
import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

class UpdateDialog(tk.Toplevel):
    """Dialog for displaying LoRA update information"""

    def __init__(self, parent, update_info: Dict[str, Any], download_callback: Optional[Callable] = None):
        """
        Initialize the update dialog

        Args:
            parent: The parent window
            update_info: Dictionary containing update information
            download_callback: Optional callback function for downloading the update
        """
        super().__init__(parent)
        self.parent = parent
        self.update_info = update_info
        self.download_callback = download_callback

        # Flag to track if an update was downloaded
        self.update_downloaded = False

        self.title("LoRA Update Available")
        self.geometry("600x400")
        self.minsize(500, 300)
        self.resizable(True, True)

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self._create_widgets()

        # Center the dialog
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'+{x}+{y}')

    def _create_widgets(self):
        """Create the dialog widgets"""
        # Main frame
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Model information
        model_name = self.update_info.get('model_name', 'Unknown')
        ttk.Label(main_frame, text=f"Update Available for: {model_name}",
                 font=('TkDefaultFont', 12, 'bold')).pack(pady=(0, 10), anchor=tk.W)

        # Version information
        latest_version = self.update_info.get('latest_version', {})
        version_name = latest_version.get('name', 'Unknown')
        created_at = latest_version.get('created_at', 'Unknown date')

        version_frame = ttk.Frame(main_frame)
        version_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(version_frame, text="Version:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Label(version_frame, text=version_name).grid(row=0, column=1, sticky=tk.W)

        ttk.Label(version_frame, text="Released:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Label(version_frame, text=created_at).grid(row=1, column=1, sticky=tk.W)

        # Trained words
        trained_words = latest_version.get('trained_words', [])
        if trained_words:
            ttk.Label(main_frame, text="Trained Words:",
                     font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W, pady=(5, 0))

            words_text = ", ".join(trained_words)
            words_label = ttk.Label(main_frame, text=words_text, wraplength=580)
            words_label.pack(fill=tk.X, pady=(0, 10))

        # Description
        description = latest_version.get('description', '')
        if description:
            ttk.Label(main_frame, text="Description:",
                     font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W, pady=(5, 0))

            # Use Text widget for description to allow scrolling
            desc_frame = ttk.Frame(main_frame)
            desc_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

            desc_text = tk.Text(desc_frame, wrap=tk.WORD, height=8)
            desc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            scrollbar = ttk.Scrollbar(desc_frame, command=desc_text.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            desc_text.config(yscrollcommand=scrollbar.set)

            desc_text.insert(tk.END, description)
            desc_text.config(state=tk.DISABLED)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # View on Civitai button
        model_id = self.update_info.get('model_id')
        if model_id:
            view_button = ttk.Button(button_frame, text="View on Civitai",
                                    command=lambda: webbrowser.open(f"https://civitai.com/models/{model_id}"))
            view_button.pack(side=tk.LEFT, padx=(0, 5))

        # Download button
        if self.download_callback:
            download_button = ttk.Button(button_frame, text="Download Update",
                                        command=self._download_update)
            download_button.pack(side=tk.LEFT, padx=(0, 5))

        # Close button
        close_button = ttk.Button(button_frame, text="Close", command=self.destroy)
        close_button.pack(side=tk.RIGHT)

    def _download_update(self):
        """Download the update"""
        if self.download_callback:
            # Set the flag to indicate that an update was downloaded
            self.update_downloaded = True
            self.download_callback(self.update_info)
            self.destroy()
