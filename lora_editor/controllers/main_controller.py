"""
Main Controller - Handles the business logic for the LoRA Editor
"""
import tkinter as tk
import logging
import threading
from typing import Dict, Any, List, Optional
import os
import webbrowser
from datetime import datetime
from lora_database import LoraHistoryEntry

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from models.lora_model import LoraModel
from views.main_view import MainView
from dialogs.entry_dialog import EntryDialog
from views.update_dialog_new import UpdateDialog
from lora_database import LoraHistoryEntry
from downloaders.civitai_downloader import CivitAIDownloader
from downloaders.huggingface_downloader import HuggingFaceDownloader

logger = logging.getLogger(__name__)

class MainController:
    """Main controller class for the LoRA Editor"""

    def __init__(self, model: LoraModel, view: MainView):
        """Initialize the controller with model and view"""
        self.model = model
        self.view = view

        # Initialize downloaders
        self.civitai_downloader = CivitAIDownloader()
        self.huggingface_downloader = HuggingFaceDownloader()

        # Bind UI events to controller methods
        self._bind_events()

        # Initialize UI with data
        self._initialize_ui()

    def _bind_events(self):
        """Bind UI events to controller methods"""
        # Bind checkbox and search events
        self.view.bind_show_inactive_changed(self.refresh_tree)
        self.view.bind_search_changed(self.filter_treeview)
        self.view.bind_default_lora_changed(self.update_default_lora)

        # Bind tree events
        self.view.bind_tree_double_click(self.on_double_click)
        self.view.bind_tree_reordered(self.sync_database_order)

        # Bind button events
        self.view.bind_button("add_entry", self.add_entry)
        self.view.bind_button("edit_entry", self.edit_entry)
        self.view.bind_button("delete_entry", self.delete_entry)
        self.view.bind_button("de_/_active", self.toggle_active)
        self.view.bind_button("save", self.save_config)
        self.view.bind_button("refresh_files", self.refresh_lora_files)
        self.view.bind_button("Check Updates", self.check_all_for_updates)
        self.view.bind_button("reset_lora", self.reset_lora)

        # Bind other UI events
        self.view.bind_browse_button(self.select_folder)
        self.view.bind_civitai_button(self.download_from_civitai)
        self.view.bind_hf_button(self.download_from_huggingface)

        # Set navigation commands
        nav_commands = {
            'up': self.move_up,
            'down': self.move_down,
            'up_five': self.move_up_five,
            'down_five': self.move_down_five
        }
        self.view.set_nav_commands(nav_commands)

        # Bind menu commands
        self.view.bind_menu_command("File", "Save Configuration", self.save_config)
        self.view.bind_menu_command("Edit", "Add New LoRA", self.add_entry)
        self.view.bind_menu_command("Edit", "Edit Selected LoRA", self.edit_entry)
        self.view.bind_menu_command("Edit", "Delete Selected LoRA", self.delete_entry)
        self.view.bind_menu_command("Updates", "Check Selected for Updates", self.check_for_updates)
        self.view.bind_menu_command("Updates", "Check All for Updates", self.check_all_for_updates)

        # Bind context menu commands
        self.view.bind_context_menu_command("Check for Updates", self.check_for_updates)

    def _initialize_ui(self):
        """Initialize the UI with data from the model"""
        # Set folder path
        self.view.set_folder_path(self.model.lora_folder)

        # Set default LoRA
        default_lora = self.model.get_default_lora()
        if default_lora:
            self.view.set_default_lora(default_lora)

        # Refresh LoRA files
        self.refresh_lora_files()

        # Load tree data
        self.load_tree()

        # Set status
        self.view.set_status("Ready")

    def load_tree(self, select_id=None):
        """Load LoRA entries into the treeview

        Args:
            select_id: Optional ID of the entry to select after loading
        """
        try:
            # Clear existing items
            self.view.clear_tree()

            # Get entries from model
            include_inactive = self.view.show_inactive_var.get()
            entries = self.model.get_all_loras(include_inactive=include_inactive)

            # Add debug logging
            logger.debug(f"Got {len(entries)} entries from database")
            if len(entries) > 0:
                logger.debug(f"First entry: {entries[0].id}, {entries[0].display_name}")

            # Sort entries by display_order to show the correct order after moves
            entries_by_display_order = sorted(entries, key=lambda e: e.display_order)
            logger.debug(f"Sorted {len(entries_by_display_order)} entries by display_order")

            # Add entries to tree in display_order order
            id_to_item = {}
            for entry in entries_by_display_order:
                item = self.view.add_tree_item(entry)
                id_to_item[entry.id] = item

            # Select the specified item if provided
            if select_id is not None and select_id in id_to_item:
                self.view.tree.selection_set(id_to_item[select_id])
                # Ensure the selected item is visible
                self.view.tree.see(id_to_item[select_id])

            self.view.set_status(f"Loaded {len(entries)} LoRA entries")
        except Exception as e:
            logger.error(f"Error loading tree: {e}")
            self.view.set_status("Error loading LoRA entries")
            self.view.show_message("Error", f"Failed to load LoRA entries: {str(e)}", "error")

    def refresh_tree(self, select_id=None):
        """Refresh the treeview with current data

        Args:
            select_id: Optional ID of the entry to select after refresh
        """
        self.load_tree(select_id)

    def filter_treeview(self):
        """Filter the treeview based on search term"""
        search_term = self.view.search_var.get().lower()

        # Clear and reload the tree
        self.view.clear_tree()

        # Get entries from model
        include_inactive = self.view.show_inactive_var.get()
        entries = self.model.get_all_loras(include_inactive=include_inactive)

        # Sort entries by display_order to show the correct order after moves
        entries_by_display_order = sorted(entries, key=lambda e: e.display_order)

        # Filter and add entries to tree in display_order order
        filtered_count = 0
        for entry in entries_by_display_order:

            # Check if search term is in any of the entry fields
            if (search_term in entry.display_name.lower() or
                search_term in entry.file_name.lower() or
                search_term in entry.trigger_words.lower() or
                search_term in entry.url.lower()):
                self.view.add_tree_item(entry)
                filtered_count += 1

        self.view.set_status(f"Found {filtered_count} matching entries")

    def select_folder(self):
        """Open folder selection dialog and update folder path"""
        folder = self.view.ask_folder()
        if folder:
            if self.model.set_lora_folder(folder):
                self.view.set_folder_path(folder)
                self.refresh_lora_files()
                self.view.set_status(f"Selected folder: {folder}")
            else:
                self.view.show_message("Error", "Invalid folder selected", "error")

    def refresh_lora_files(self):
        """Refresh the list of available LoRA files"""
        lora_files = self.model.refresh_lora_files()
        self.view.update_available_loras(lora_files)

        # Update default LoRA if it exists in the available files
        default_lora = self.model.get_default_lora()
        if default_lora in lora_files:
            self.view.set_default_lora(default_lora)

        self.view.set_status(f"Found {len(lora_files)} LoRA files")

    def add_entry(self):
        """Add a new LoRA entry"""
        lora_files = self.model.available_lora_files
        if not lora_files:
            self.view.show_message("Warning", "Please select a folder with LoRA files first", "warning")
            return

        # Create initial values dict
        initial_values = {
            "name": "",
            "file": "",
            "weight": "1.0",
            "add_prompt": "",
            "url": ""
        }

        dialog = EntryDialog(
            self.view.root,
            "Add LoRA Entry",
            initial=initial_values,
            available_files=lora_files
        )

        if dialog.result:
            # Convert dialog result to LoraHistoryEntry
            entry = LoraHistoryEntry(
                file_name=dialog.result["file"],
                display_name=dialog.result["name"],
                trigger_words=dialog.result["add_prompt"],
                weight=float(dialog.result["weight"]),
                url=dialog.result["url"],
                is_active=True
            )

            # Add to model
            if self.model.add_lora(entry):
                self.refresh_tree()
                self.view.set_status(f"Added new entry: {entry.display_name}")
            else:
                self.view.show_message("Error", "Failed to add entry", "error")

    def edit_entry(self):
        """Edit the selected LoRA entry"""
        selected = self.view.get_selected_items()
        if not selected:
            self.view.show_message("Warning", "Please select an entry to edit", "warning")
            return

        # Get the first selected item
        item_id = selected[0]
        values = self.view.get_item_values(item_id)

        # Get the entry from the model
        entry_id = values[0]  # ID is the first column
        entry = self.model.get_lora_by_id(entry_id)

        if not entry:
            self.view.show_message("Error", f"Entry with ID {entry_id} not found", "error")
            return

        # Create initial values for dialog
        initial_values = {
            "name": entry.display_name,
            "file": entry.file_name,
            "weight": str(entry.weight),
            "add_prompt": entry.trigger_words,
            "url": entry.url
        }

        dialog = EntryDialog(
            self.view.root,
            "Edit LoRA Entry",
            initial=initial_values,
            available_files=self.model.available_lora_files
        )

        if dialog.result:
            # Update entry with new values
            entry.display_name = dialog.result["name"]
            entry.file_name = dialog.result["file"]
            entry.weight = float(dialog.result["weight"])
            entry.trigger_words = dialog.result["add_prompt"]
            entry.url = dialog.result["url"]

            # Update in model
            if self.model.update_lora(entry):
                self.refresh_tree()
                self.view.set_status(f"Updated entry: {entry.display_name}")
            else:
                self.view.show_message("Error", "Failed to update entry", "error")

    def delete_entry(self):
        """Delete the selected LoRA entries"""
        selected = self.view.get_selected_items()
        if not selected:
            self.view.show_message("No Selection", "Please select entries to delete", "warning")
            return

        # Confirm deletion
        count = len(selected)
        if not self.view.ask_yes_no("Confirm Delete", f"Delete {count} selected entries?"):
            return

        # Delete each selected entry
        deleted_count = 0
        for item_id in selected:
            values = self.view.get_item_values(item_id)
            entry_id = values[0]  # ID is the first column

            if self.model.delete_lora(entry_id):
                deleted_count += 1

        self.refresh_tree()
        self.view.set_status(f"Deleted {deleted_count} entries")

    def toggle_active(self):
        """Toggle the active status of selected entries"""
        selected = self.view.get_selected_items()
        if not selected:
            self.view.show_message("Warning", "Please select entries to toggle", "warning")
            return

        # Toggle each selected entry
        toggled_count = 0
        for item_id in selected:
            values = self.view.get_item_values(item_id)
            entry_id = values[0]  # ID is the first column

            if self.model.toggle_active(entry_id):
                toggled_count += 1

        self.refresh_tree()
        self.view.set_status(f"Toggled {toggled_count} entries")

    def save_config(self):
        """Save the current configuration to file"""
        # Export active entries to config
        self.model.export_active_loras_to_config()

        # Save to file
        if self.model.save_config():
            self.view.set_status("Configuration saved successfully")
        else:
            self.view.show_message("Error", "Failed to save configuration", "error")

    def reset_lora(self):
        """Reset the LoRA database to default state"""
        if not self.view.ask_yes_no("Confirm Reset", "This will delete all LoRA entries. Continue?"):
            return

        if self.model.reset_lora_database():
            self.refresh_tree()
            self.view.set_status("LoRA database reset to default state")
        else:
            self.view.show_message("Error", "Failed to reset LoRA database", "error")

    def move_up(self):
        """Move the selected entry up in the list"""
        self._move_entry("up")

    def move_down(self):
        """Move the selected entry down in the list"""
        self._move_entry("down")

    def move_up_five(self):
        """Move the selected entry up five positions"""
        self._move_entry("up", 5)

    def move_down_five(self):
        """Move the selected entry down five positions"""
        self._move_entry("down", 5)

    def check_for_updates(self, entry_id: int = None):
        """Check for updates for the selected LoRA"""
        logger.info("Check for updates menu item clicked")

        # Initialize item_id to None
        item_id = None

        # If no entry_id is provided, get it from the selected item
        if entry_id is None:
            selected = self.view.get_selected_items()
            if not selected:
                self.view.show_message("No Selection", "Please select a LoRA to check for updates", "warning")
                return

            # Get the first selected item
            item_id = selected[0]
            values = self.view.get_item_values(item_id)
            entry_id = int(values[0])  # ID is the first column
            lora_name = values[2] if len(values) > 2 else "Unknown"  # Name is the third column
        else:
            # Get the LoRA name from the database
            lora = self.model.db.get_lora_by_id(entry_id)
            lora_name = lora.display_name if lora else "Unknown"

        logger.info(f"Checking for updates for LoRA ID {entry_id} ({lora_name})")

        # Show a loading message and start progress
        self.view.set_status(f"Checking for updates for {lora_name}...")
        self.view.start_progress()

        # Run the update check in a separate thread
        threading.Thread(target=self._check_for_updates_thread, args=(entry_id, item_id), daemon=True).start()

    def _check_for_updates_thread(self, lora_id: int, item_id: str = None):
        """Thread function to check for updates"""
        try:
            logger.info(f"Starting update check thread for LoRA ID {lora_id}")
            has_update, update_info = self.model.check_for_updates(lora_id)
            logger.info(f"Update check result: has_update={has_update}, info={update_info}")

            # Update the UI in the main thread
            self.view.root.after(0, lambda: self._handle_update_result(has_update, update_info, lora_id))

            # Stop the progress indicator
            self.view.root.after(0, lambda: self.view.stop_progress())
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            import traceback
            logger.error(traceback.format_exc())
            try:
                self.view.root.after(0, lambda: self.view.set_status(f"Error checking for updates: {str(e)}"))
                self.view.root.after(0, lambda: self.view.stop_progress())
            except Exception as e2:
                logger.error(f"Error updating UI after exception: {e2}")

    def _handle_update_result(self, has_update: bool, update_info: Optional[Dict[str, Any]], lora_id: int):
        """Handle the result of the update check"""
        if has_update and update_info:
            logger.info(f"Update available for LoRA ID {lora_id}")

            # Get the LoRA name
            lora = self.model.db.get_lora_by_id(lora_id)
            lora_name = lora.display_name if lora else "Unknown"

            # Update the status bar
            self.view.set_status(f"Update available for {lora_name}")

            # Update the database to mark this LoRA as having an update
            self.model.db.update_lora_update_status(lora_id, True)

            # Update the UI to show this LoRA has an update
            self.view.update_lora_status(lora_id, "Update Available")

            # Highlight the item
            self.view.highlight_item_by_id(lora_id)

            # Add the LoRA folder to the update info
            update_info['lora_folder'] = self.model.get_lora_folder()

            # Add a flag to the update_info to indicate that this LoRA has an update
            update_info['has_update'] = True

            # Store the lora_id in the update_info for reference
            update_info['lora_id'] = lora_id

            # Show the update dialog - pass the root window as parent
            dialog = UpdateDialog(self.view.root, update_info, self._download_update)

            # Wait for the dialog to be destroyed
            self.view.root.wait_window(dialog)

            # After the dialog is closed, make sure the status is still "Update Available"
            # unless the update was downloaded
            if not hasattr(dialog, 'update_downloaded') or not dialog.update_downloaded:
                self.view.update_lora_status(lora_id, "Update Available")
                self.view.highlight_item_by_id(lora_id)
        else:
            lora = self.model.db.get_lora_by_id(lora_id)
            if lora:
                self.view.set_status(f"No updates available for {lora.display_name}")
                self.view.show_message("No Updates", f"No updates available for {lora.display_name}", "info")

                # Update the UI to show this LoRA is current
                self.view.update_lora_status(lora_id, "Current")
            else:
                self.view.set_status("No updates available")
                self.view.show_message("No Updates", "No updates available", "info")

    def _download_update(self, update_info: Dict[str, Any]):
        """Download the update"""
        # Extract info from the update_info dict
        latest_version = update_info.get('latest_version', {})
        download_url = latest_version.get('download_url')
        version_name = latest_version.get('name')
        model_id = update_info.get('model_id')
        created_at = latest_version.get('created_at')
        progress_callback = update_info.get('progress_callback')
        completion_callback = update_info.get('completion_callback')
        trained_words = latest_version.get('trained_words', [])

        # Get destination folder if provided
        destination_folder = update_info.get('destination_folder')

        if not download_url:
            self.view.show_message("Error", "No download URL available", "error")
            if completion_callback:
                completion_callback(None)
            return

        # If no destination folder provided, use the default LoRA folder
        if not destination_folder:
            destination_folder = self.model.get_lora_folder()

        # Show status message
        self.view.set_status(f"Downloading update for {version_name}...")

        # Import the download utility
        from utils.download import download_file_async
        from dialogs.entry_dialog import EntryDialog

        # Start the download
        def download_complete(file_path):
            """Handle download completion"""
            if file_path:
                logger.info(f"Download complete: {file_path}")

                # Update the last_updated field in the database for this LoRA
                if model_id and created_at:
                    # Find all LoRAs with this model ID in their URL
                    loras = self.model.db.get_lora_history(include_inactive=True)
                    for lora in loras:
                        if lora.url and str(model_id) in lora.url:
                            # Get the file name from the download path
                            file_name = os.path.basename(file_path)
                            logger.info(f"Updating LoRA {lora.id}: {lora.display_name} - Date: {created_at}, File: {file_name}")

                            # Show dialog with existing values
                            dialog_data = {
                                "name": lora.display_name,
                                "file": file_name,
                                "weight": lora.weight,
                                "add_prompt": lora.trigger_words if lora.trigger_words else " ".join(trained_words),
                                "url": lora.url
                            }
                            
                            # Get list of available files for the combobox
                            available_files = [f for f in os.listdir(destination_folder) if f.endswith('.safetensors')]
                            
                            dialog = EntryDialog(self.view.root, "Update LoRA", dialog_data, available_files)
                            if dialog.result:
                                # Create a new entry with the same ID to preserve order
                                updated_lora = LoraHistoryEntry(
                                    file_name=dialog.result["file"],
                                    display_name=dialog.result["name"],
                                    trigger_words=dialog.result["add_prompt"],
                                    weight=float(dialog.result["weight"]),
                                    url=dialog.result["url"],
                                    is_active=lora.is_active,
                                    id=lora.id,  # Keep the same ID
                                    display_order=lora.display_order,  # Keep the same display_order
                                    last_updated=created_at,
                                    has_update=False
                                )

                                try:
                                    # Update the database with the new entry
                                    updated_lora = self.model.db.update_lora(updated_lora)
                                    if not updated_lora:
                                        raise Exception("Failed to update LoRA in database")

                                    # Update the UI to show this LoRA is current
                                    self.view.update_lora_status(updated_lora.id, "Current")

                                    # Clear and re-add all items to update the view
                                    self.view.clear_tree()
                                    loras = self.model.db.get_lora_history()
                                    for lora_entry in loras:
                                        self.view.add_tree_item(lora_entry)

                                    # Show version info in status bar
                                    self.view.set_status(f"Updated {updated_lora.display_name} to version {version_name}")
                                    
                                    # Close any open dialogs
                                    for widget in self.view.root.winfo_children():
                                        if isinstance(widget, tk.Toplevel) and widget.winfo_exists():
                                            widget.destroy()
                                except Exception as e:
                                    logger.error(f"Error updating LoRA: {e}")
                                    self.view.show_message("Error", f"Failed to update LoRA: {e}", "error")
                                    return
                            else:
                                # User cancelled, delete the downloaded file
                                try:
                                    os.remove(file_path)
                                    logger.info(f"Deleted downloaded file after cancel: {file_path}")
                                except Exception as e:
                                    logger.error(f"Error deleting file after cancel: {e}")

                # Call the completion callback if provided
                if completion_callback:
                    completion_callback(file_path)
            else:
                logger.error("Download failed")
                self.view.set_status("Download failed")

                # Call the completion callback if provided
                if completion_callback:
                    completion_callback(None)

        # Let the downloader handle the filename from Content-Disposition
        download_file_async(download_url, destination_folder, None, progress_callback, download_complete)

    def check_all_for_updates(self):
        """Check all LoRAs for updates"""
        # Show a loading message
        self.view.set_status("Checking all LoRAs for updates...")
        self.view.start_progress()

        # Run the update check in a separate thread
        threading.Thread(target=self._check_all_for_updates_thread, daemon=True).start()

    def _check_all_for_updates_thread(self):
        """Thread function to check all LoRAs for updates"""
        try:
            # Get all LoRAs with Civitai URLs
            loras = self.model.db.get_lora_history(include_inactive=True)
            loras_with_urls = [lora for lora in loras if lora.url and 'civitai.com' in lora.url]

            total_count = len(loras_with_urls)
            updates_found = {}

            # Update status bar with progress
            self.view.root.after(0, lambda: self.view.set_status(f"Checking LoRAs for updates (0/{total_count})..."))

            # Check each LoRA for updates
            for i, lora in enumerate(loras_with_urls):
                # Update progress in the UI
                progress_msg = f"Checking LoRAs for updates ({i+1}/{total_count})..."
                self.view.root.after(0, lambda msg=progress_msg: self.view.set_status(msg))

                # Check for updates
                has_update, update_info = self.model.check_for_updates(lora.id)

                if has_update and update_info:
                    updates_found[lora.id] = update_info

                    # Update the UI to show this LoRA has an update
                    self.view.root.after(0, lambda id=lora.id: self.view.update_lora_status(id, "Update Available"))

            # Update the UI in the main thread with final results
            self.view.root.after(0, lambda: self._handle_all_updates_result(updates_found))
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            import traceback
            logger.error(traceback.format_exc())
            try:
                self.view.root.after(0, lambda: self.view.set_status(f"Error checking for updates: {str(e)}"))
                self.view.root.after(0, lambda: self.view.stop_progress())
            except Exception as e2:
                logger.error(f"Error updating UI after exception: {e2}")

    def _handle_all_updates_result(self, updates: Dict[int, Dict[str, Any]]):
        """Handle the result of checking all LoRAs for updates"""
        # Stop the progress indicator
        self.view.stop_progress()

        if updates:
            update_count = len(updates)
            logger.info(f"Found {update_count} updates")
            self.view.set_status(f"Found {update_count} updates")

            # Show a message with the number of updates
            self.view.show_message("Updates Available",
                                 f"Found {update_count} updates. right-click on any LoRA marked 'Update Available' to see details.",
                                 "info")

            # Highlight the LoRAs with updates and update their status
            for lora_id in updates:
                self.view.highlight_item_by_id(lora_id)
                self.view.update_lora_status(lora_id, "Update Available")
        else:
            self.view.set_status("No updates available")
            self.view.show_message("No Updates", "All LoRAs are up to date", "info")

    def _move_entry(self, direction: str, steps: int = 1):
        """Move the selected entry in the specified direction"""
        selected = self.view.get_selected_items()
        if not selected:
            logger.warning("No item selected for move operation")
            return

        # Get the first selected item
        item_id = selected[0]
        values = self.view.get_item_values(item_id)
        entry_id = int(values[0])  # ID is the first column

        logger.debug(f"Moving entry ID {entry_id} {direction} {steps} steps")

        # Move in model
        if self.model.move_lora(entry_id, direction, steps):
            logger.debug(f"Successfully moved entry ID {entry_id}")
            # Remember the entry ID to reselect after refresh
            logger.debug(f"Refreshing tree after moving entry ID {entry_id}")
            self.refresh_tree(entry_id)
            # Show success message
            self.view.set_status(f"Moved item {direction}")

            # Save the changes to the config file
            if self.model.save_config():
                logger.debug("Saved configuration after move")
            else:
                logger.warning("Failed to save configuration after move")
        else:
            logger.warning(f"Failed to move entry ID {entry_id}")
            # Show error message to the user
            if direction == "up":
                self.view.set_status("Cannot move up further")
            elif direction == "down":
                self.view.set_status("Cannot move down further")
            else:
                self.view.set_status("Failed to move item")

    def sync_database_order(self):
        """Sync the database order with the treeview order"""
        try:
            # Get all items in the current order
            items = self.view.tree.get_children()

            # Create a mapping of ID to display order
            id_to_order = {}
            for i, item in enumerate(items):
                values = self.view.get_item_values(item)
                entry_id = int(values[0])  # ID is the first column
                id_to_order[entry_id] = i

            # Get all entries sorted by ID
            entries = self.model.get_all_loras(include_inactive=True)
            entries = sorted(entries, key=lambda e: e.id)

            # Update display order in database while keeping IDs in order
            for entry in entries:
                if entry.id in id_to_order:
                    entry.display_order = id_to_order[entry.id]
                    self.model.update_lora(entry)

            # Get the currently selected item before refreshing
            selected_items = self.view.get_selected_items()
            selected_id = None
            if selected_items:
                values = self.view.get_item_values(selected_items[0])
                selected_id = int(values[0])  # ID is the first column

            # Refresh the tree to show entries in ID order, preserving selection
            self.refresh_tree(selected_id)
            self.view.set_status("Database order synchronized")
        except Exception as e:
            logger.error(f"Error syncing database order: {e}")
            self.view.set_status("Failed to sync database order")

    def update_default_lora(self):
        """Update the default LoRA in the configuration"""
        try:
            selected = self.view.get_default_lora()
            if selected:
                self.model.set_default_lora(selected)
                self.view.set_status(f"Set default LoRA to: {selected}")
        except Exception as e:
            logger.error(f"Error updating default LoRA: {e}")
            self.view.set_status("Failed to update default LoRA")

    def on_double_click(self, event):
        """Handle double-click on treeview item"""
        # Get the selected item
        selected = self.view.get_selected_items()
        if not selected:
            return

        # Get the item values
        item_id = selected[0]
        values = self.view.get_item_values(item_id)

        # Check if this LoRA has an update available
        if len(values) > 7 and values[7] == "Update Available":
            # This LoRA has an update, show the update dialog
            entry_id = int(values[0])  # ID is the first column
            # Call check_for_updates directly - it will handle showing the dialog
            self.check_for_updates(entry_id)
        else:
            # Normal double-click behavior - edit the entry
            self.edit_entry()

    def download_from_civitai(self):
        """Download a LoRA from CivitAI"""
        url = self.view.civitai_url_var.get().strip()
        if not url:
            self.view.show_message("Warning", "Please enter a CivitAI URL", "warning")
            return

        if not self.model.lora_folder:
            self.view.show_message("Warning", "Please select a LoRA folder first", "warning")
            return

        # Start download in a separate thread
        self.view.set_status(f"Downloading from CivitAI: {url}")
        self.view.set_progress(0)

        thread = threading.Thread(
            target=self._download_from_civitai_thread,
            args=(url,)
        )
        thread.daemon = True
        thread.start()

    def _download_from_civitai_thread(self, url: str):
        """Thread function for downloading from CivitAI"""
        try:
            result = self.civitai_downloader.download(
                url,
                self.model.lora_folder,
                progress_callback=self._update_progress
            )

            if result:
                file_name, trigger_words, weight = result

                # Update UI in main thread
                self.view.root.after(0, lambda: self._on_download_complete(file_name, url, trigger_words, weight))
            else:
                self.view.root.after(0, lambda: self.view.show_message(
                    "Error", "Failed to download from CivitAI", "error"))
        except Exception as e:
            logger.error(f"Error downloading from CivitAI: {e}")
            self.view.root.after(0, lambda: self.view.show_message(
                "Error", f"Download error: {str(e)}", "error"))

    def download_from_huggingface(self):
        """Download a LoRA from HuggingFace"""
        url = self.view.hf_url_var.get().strip()
        if not url:
            self.view.show_message("Warning", "Please enter a HuggingFace URL", "warning")
            return

        if not self.model.lora_folder:
            self.view.show_message("Warning", "Please select a LoRA folder first", "warning")
            return

        # Start download in a separate thread
        self.view.set_status(f"Downloading from HuggingFace: {url}")
        self.view.set_progress(0)

        thread = threading.Thread(
            target=self._download_from_huggingface_thread,
            args=(url,)
        )
        thread.daemon = True
        thread.start()

    def _download_from_huggingface_thread(self, url: str):
        """Thread function for downloading from HuggingFace"""
        try:
            result = self.huggingface_downloader.download(
                url,
                self.model.lora_folder,
                progress_callback=self._update_progress
            )

            if result:
                file_name, trigger_words = result

                # Update UI in main thread
                self.view.root.after(0, lambda: self._on_download_complete(file_name, url, trigger_words))
            else:
                self.view.root.after(0, lambda: self.view.show_message(
                    "Error", "Failed to download from HuggingFace", "error"))
        except Exception as e:
            logger.error(f"Error downloading from HuggingFace: {e}")
            self.view.root.after(0, lambda: self.view.show_message(
                "Error", f"Download error: {str(e)}", "error"))

    def _update_progress(self, progress: float):
        """Update the progress bar"""
        # Use after() to schedule UI updates in the main thread
        # Use a higher priority for UI updates, but don't overwhelm the UI
        self.view.root.after(50, lambda p=progress: self._safe_update_progress(p))

    def _safe_update_progress(self, progress: float):
        """Safely update the progress bar and process pending events"""
        try:
            # Update progress bar
            self.view.set_progress(int(progress))

            # Only process essential UI updates to reduce jitter
            self.view.root.update_idletasks()
        except Exception as e:
            logger.error(f"Error updating progress: {e}")

    def _on_download_complete(self, file_name: str, url: str, trigger_words: str, weight: float = 1.0):
        """Handle download completion"""
        self.refresh_lora_files()
        self.view.set_status(f"Download complete: {file_name}")

        # Ask user if they want to add the downloaded file to the configuration
        if self.view.ask_yes_no("Add Entry", f"Do you want to add {file_name} to the configuration?"):
            # Create initial values for the dialog
            name = os.path.splitext(file_name)[0]  # Remove .safetensors extension
            initial = {
                "name": name,
                "file": file_name,
                "weight": str(weight),
                "add_prompt": trigger_words,
                "url": url
            }

            dialog = EntryDialog(
                self.view.root,
                "Add LoRA Entry",
                initial=initial,
                available_files=self.model.available_lora_files
            )

            if dialog.result:
                # Convert dialog result to LoraHistoryEntry
                entry = LoraHistoryEntry(
                    file_name=dialog.result["file"],
                    display_name=dialog.result["name"],
                    trigger_words=dialog.result["add_prompt"],
                    weight=float(dialog.result["weight"]),
                    url=dialog.result["url"],
                    is_active=True
                )

                # Add to model
                if self.model.add_lora(entry):
                    self.refresh_tree()
                    self.view.set_status(f"Added new entry: {entry.display_name}")
                else:
                    self.view.show_message("Error", "Failed to add entry", "error")
