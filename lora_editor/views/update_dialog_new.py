"""
Dialog for displaying LoRA update information
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
import logging
import os
import re
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
        self.downloading = False

        self.title("LoRA Update Available")
        self.geometry("600x450")
        self.minsize(500, 350)
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

            # Create a text widget with hyperlink support
            desc_text = tk.Text(desc_frame, wrap=tk.WORD, height=8, padx=5, pady=5)
            desc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            scrollbar = ttk.Scrollbar(desc_frame, command=desc_text.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            desc_text.config(yscrollcommand=scrollbar.set)

            # Configure tags for hyperlinks
            desc_text.tag_configure("hyperlink", foreground="blue", underline=1)
            desc_text.tag_bind("hyperlink", "<Enter>", lambda e: desc_text.config(cursor="hand2"))
            desc_text.tag_bind("hyperlink", "<Leave>", lambda e: desc_text.config(cursor=""))

            # Process HTML content
            self._insert_html_content(desc_text, description)

            # Make the text widget read-only
            desc_text.config(state=tk.DISABLED)

        # Download destination frame
        dest_frame = ttk.Frame(main_frame)
        dest_frame.pack(fill=tk.X, pady=(10, 5))

        ttk.Label(dest_frame, text="Download to:").pack(side=tk.LEFT, padx=(0, 5))

        # Get the default LoRA folder from the update info
        self.lora_folder = self.update_info.get('lora_folder', '')

        self.dest_var = tk.StringVar(value=self.lora_folder)
        dest_entry = ttk.Entry(dest_frame, textvariable=self.dest_var, width=40)
        dest_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        browse_button = ttk.Button(dest_frame, text="Browse", command=self._browse_folder)
        browse_button.pack(side=tk.RIGHT)

        # Progress frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(5, 10))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                          mode='determinate', length=100)
        self.progress_bar.pack(fill=tk.X)

        # Status label
        self.status_var = tk.StringVar(value="Ready to download")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        status_label.pack(anchor=tk.W, pady=(2, 0))

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
            self.download_button = ttk.Button(button_frame, text="Download Update",
                                           command=self._download_update)
            self.download_button.pack(side=tk.LEFT, padx=(0, 5))

        # Close button
        self.close_button = ttk.Button(button_frame, text="Close", command=self.destroy)
        self.close_button.pack(side=tk.RIGHT)

    def _browse_folder(self):
        """Browse for a folder to save the download"""
        folder = filedialog.askdirectory(initialdir=self.dest_var.get())
        if folder:
            self.dest_var.set(folder)

    def _download_update(self):
        """Download the update"""
        if self.downloading:
            return

        # Get the destination folder
        dest_folder = self.dest_var.get()
        if not dest_folder:
            messagebox.showerror("Error", "Please select a destination folder")
            return

        # Make sure the folder exists
        if not os.path.isdir(dest_folder):
            try:
                os.makedirs(dest_folder, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create folder: {e}")
                return

        # Update UI state
        self.downloading = True
        self.download_button.config(state=tk.DISABLED)
        self.close_button.config(state=tk.DISABLED)
        self.status_var.set("Starting download...")

        # Start the download
        if self.download_callback:
            # Add destination folder to update info
            download_info = dict(self.update_info)
            download_info['destination_folder'] = dest_folder
            download_info['progress_callback'] = self._update_progress
            download_info['completion_callback'] = self._download_complete

            # Call the download callback
            self.download_callback(download_info)

    def _update_progress(self, progress: float):
        """Update the progress bar"""
        # Check if the dialog still exists
        try:
            # Check if the window still exists
            self.winfo_exists()
        except tk.TclError:
            logger.warning("Update dialog was closed during download")
            return

        try:
            # Update progress bar (0-100)
            self.progress_var.set(progress * 100)

            # Update status text
            percent = int(progress * 100)
            self.status_var.set(f"Downloading... {percent}%")

            # Update the UI
            self.update_idletasks()
        except tk.TclError as e:
            logger.error(f"Error updating progress: {e}")

    def _download_complete(self, file_path: Optional[str]):
        """Handle download completion"""
        self.downloading = False

        # Check if the dialog still exists
        try:
            # Check if the window still exists
            self.winfo_exists()
        except tk.TclError:
            logger.warning("Update dialog was closed before download completed")
            return

        if file_path:
            # Download succeeded
            try:
                self.progress_var.set(100)
                self.status_var.set(f"Download complete: {os.path.basename(file_path)}")

                # Enable close button if it still exists
                if hasattr(self, 'close_button') and self.close_button.winfo_exists():
                    self.close_button.config(state=tk.NORMAL)

                # Change download button to "Open Folder" if it still exists
                if hasattr(self, 'download_button') and self.download_button.winfo_exists():
                    self.download_button.config(text="Open Folder", state=tk.NORMAL,
                                             command=lambda: os.startfile(os.path.dirname(file_path)))

                # Show success message
                messagebox.showinfo("Download Complete",
                                  f"Successfully downloaded {os.path.basename(file_path)}")
            except tk.TclError as e:
                logger.error(f"Error updating UI after download: {e}")
        else:
            # Download failed
            try:
                self.progress_var.set(0)
                self.status_var.set("Download failed")

                # Re-enable buttons if they still exist
                if hasattr(self, 'download_button') and self.download_button.winfo_exists():
                    self.download_button.config(state=tk.NORMAL)
                if hasattr(self, 'close_button') and self.close_button.winfo_exists():
                    self.close_button.config(state=tk.NORMAL)

                # Show error message
                messagebox.showerror("Download Failed",
                                   "Failed to download the update. Please try again or use the browser option.")
            except tk.TclError as e:
                logger.error(f"Error updating UI after failed download: {e}")

    def _insert_html_content(self, text_widget, html_content):
        """Process HTML content and insert it into the text widget with proper formatting"""
        try:
            # Current position in the text widget
            position = "1.0"

            # Process the HTML content
            # First, handle paragraph tags
            paragraphs = re.split(r'</?p>', html_content)
            paragraphs = [p for p in paragraphs if p.strip()]

            for i, paragraph in enumerate(paragraphs):
                # Skip empty paragraphs
                if not paragraph.strip():
                    continue

                # Process links in this paragraph
                while '<a' in paragraph and '</a>' in paragraph:
                    # Find the link
                    link_start = paragraph.find('<a')
                    link_end = paragraph.find('</a>') + 4
                    link_html = paragraph[link_start:link_end]

                    # Extract the URL and text
                    href_match = re.search(r'href="([^"]+)"', link_html)
                    if href_match:
                        url = href_match.group(1)
                        # Get the link text
                        link_text_match = re.search(r'>([^<]+)<', link_html)
                        if link_text_match:
                            link_text = link_text_match.group(1)

                            # Insert text before the link
                            before_link = paragraph[:link_start].strip()
                            if before_link:
                                text_widget.insert(position, before_link)
                                position = text_widget.index("end-1c")

                            # Insert the link with the hyperlink tag
                            text_widget.insert(position, link_text, ("hyperlink", f"link-{url}"))
                            # Bind the click event to open the URL
                            text_widget.tag_bind(f"link-{url}", "<Button-1>",
                                               lambda e, url=url: webbrowser.open(url))
                            position = text_widget.index("end-1c")

                            # Update paragraph to continue processing
                            paragraph = paragraph[link_end:]
                        else:
                            # No link text found, just insert the text and move on
                            text_widget.insert(position, paragraph[:link_end])
                            position = text_widget.index("end-1c")
                            paragraph = paragraph[link_end:]
                    else:
                        # No URL found, just insert the text and move on
                        text_widget.insert(position, paragraph[:link_end])
                        position = text_widget.index("end-1c")
                        paragraph = paragraph[link_end:]

                # Insert any remaining text in this paragraph
                if paragraph.strip():
                    text_widget.insert(position, paragraph)
                    position = text_widget.index("end-1c")

                # Add a newline between paragraphs (except for the last one)
                if i < len(paragraphs) - 1:
                    text_widget.insert(position, "\n\n")
                    position = text_widget.index("end-1c")

        except Exception as e:
            logger.error(f"Error processing HTML content: {e}")
            # If there's an error, just insert the raw content
            text_widget.delete("1.0", tk.END)
            text_widget.insert("1.0", html_content)
