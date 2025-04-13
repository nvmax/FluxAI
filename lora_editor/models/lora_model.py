"""
LoRA Model - Handles data operations for LoRA entries
"""
import logging
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from lora_database import LoraDatabase, LoraHistoryEntry
from utils.config import get_lora_json_path, load_json_config, save_json_config, update_env_file
from utils.civitai_api import check_lora_for_updates

logger = logging.getLogger(__name__)

class LoraModel:
    """Model class for handling LoRA data operations"""

    def __init__(self):
        """Initialize the LoRA model"""
        self.db = LoraDatabase()
        self.config = self._load_config()
        self.available_lora_files = []

        # Load settings
        settings = self._load_settings()

        # Get LoRA folder path from settings or environment variable
        self.lora_folder = settings.get('lora_folder', os.getenv('LORA_FOLDER_PATH', ''))

        # If we have a folder path, make sure it exists
        if self.lora_folder and not os.path.exists(self.lora_folder):
            logger.warning(f"LoRA folder does not exist: {self.lora_folder}")
            self.lora_folder = ''

        logger.info(f"Using LoRA folder: {self.lora_folder}")

    def _load_config(self) -> Dict[str, Any]:
        """Load the LoRA configuration from file"""
        json_path = get_lora_json_path()
        logger.info(f"Loading LoRA configuration from: {json_path}")
        config = load_json_config(str(json_path))

        # Sync database with JSON
        if config and "available_loras" in config:
            self.db.sync_with_json(config)

        return config

    def save_config(self) -> bool:
        """Save the current configuration to file"""
        try:
            json_path = get_lora_json_path()
            logger.info(f"Saving LoRA configuration to: {json_path}")
            return save_json_config(str(json_path), self.config)
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False

    def get_all_loras(self, include_inactive: bool = True) -> List[LoraHistoryEntry]:
        """Get all LoRA entries from the database"""
        return self.db.get_lora_history(include_inactive=include_inactive)

    def get_lora_by_id(self, lora_id: int) -> Optional[LoraHistoryEntry]:
        """Get a LoRA entry by ID"""
        return self.db.get_lora_by_id(lora_id)

    def get_lora_folder(self) -> str:
        """Get the LoRA folder path"""
        return self.lora_folder

    def add_lora(self, entry: LoraHistoryEntry) -> bool:
        """Add a new LoRA entry to the database"""
        try:
            self.db.add_lora(entry)
            return True
        except Exception as e:
            logger.error(f"Error adding LoRA: {e}")
            return False

    def update_lora(self, entry: LoraHistoryEntry) -> bool:
        """Update an existing LoRA entry"""
        try:
            self.db.update_lora(entry)
            return True
        except Exception as e:
            logger.error(f"Error updating LoRA: {e}")
            return False

    def delete_lora(self, lora_id: int) -> bool:
        """Delete a LoRA entry from the database"""
        try:
            self.db.delete_lora(lora_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting LoRA: {e}")
            return False

    def toggle_active(self, lora_id: int) -> bool:
        """Toggle the active status of a LoRA entry"""
        try:
            entry = self.db.get_lora_by_id(lora_id)
            if entry:
                entry.is_active = not entry.is_active
                self.db.update_lora(entry)
                return True
            return False
        except Exception as e:
            logger.error(f"Error toggling active status: {e}")
            return False

    def move_lora(self, lora_id: int, direction: str, steps: int = 1) -> bool:
        """Move a LoRA entry up or down in the display order

        This only changes the display_order value, not the ID.
        """
        try:
            # Get all entries
            all_entries = self.db.get_lora_history()

            # Sort entries by display_order for movement operations
            entries = sorted(all_entries, key=lambda e: e.display_order)

            # Log the entries for debugging
            logger.debug(f"Moving LoRA ID {lora_id} {direction} {steps} steps")

            # Find the entry with the given ID
            target_entry = None
            target_index = -1
            for i, entry in enumerate(entries):
                if entry.id == lora_id:
                    target_entry = entry
                    target_index = i
                    break

            if target_entry is None:
                logger.warning(f"Entry with ID {lora_id} not found")
                return False

            # Calculate the new position
            if direction == "up" and target_index > 0:
                new_index = max(0, target_index - steps)
            elif direction == "down" and target_index < len(entries) - 1:
                new_index = min(len(entries) - 1, target_index + steps)
            else:
                logger.warning(f"Can't move {direction}: target_index={target_index}, len(entries)={len(entries)}")
                return False

            # Remove the entry from its current position
            entries.pop(target_index)
            # Insert it at the new position
            entries.insert(new_index, target_entry)

            # Update display_order for all entries to maintain sequence
            for i, entry in enumerate(entries):
                entry.display_order = i
                self.db.update_lora(entry)

            logger.debug(f"Moved LoRA ID {lora_id} to position {new_index}")
            return True

        except Exception as e:
            logger.error(f"Error moving LoRA: {e}")
            return False

    def refresh_lora_files(self) -> List[str]:
        """Refresh the list of available LoRA files from the folder"""
        try:
            if not os.path.exists(self.lora_folder):
                self.available_lora_files = []
                return []

            # Get list of .safetensors files
            self.available_lora_files = [
                file for file in os.listdir(self.lora_folder)
                if file.endswith('.safetensors')
            ]

            return self.available_lora_files
        except Exception as e:
            logger.error(f"Error refreshing LoRA files: {e}")
            self.available_lora_files = []
            return []

    def set_lora_folder(self, folder_path: str) -> bool:
        """Set the LoRA folder path and save it to configuration"""
        try:
            if os.path.exists(folder_path):
                self.lora_folder = folder_path
                # Save to environment variable
                update_env_file('LORA_FOLDER_PATH', folder_path)
                # Also save to config file
                self._save_settings({'lora_folder': folder_path})
                self.refresh_lora_files()
                return True
            return False
        except Exception as e:
            logger.error(f"Error setting LoRA folder: {e}")
            return False

    def get_default_lora(self) -> str:
        """Get the default LoRA from the configuration"""
        return self.config.get("default", "")

    def set_default_lora(self, lora_file: str) -> bool:
        """Set the default LoRA in the configuration"""
        try:
            self.config["default"] = lora_file
            return True
        except Exception as e:
            logger.error(f"Error setting default LoRA: {e}")
            return False

    def export_active_loras_to_config(self) -> Dict[str, Any]:
        """Export active LoRA entries to configuration format"""
        try:
            entries = self.get_all_loras(include_inactive=False)
            loras = []
            for entry in entries:
                loras.append({
                    'file': entry.file_name,
                    'name': entry.display_name,
                    'weight': entry.weight,
                    'add_prompt': entry.trigger_words,
                    'url': entry.url,
                    'is_active': True
                })

            self.config['available_loras'] = loras
            return self.config
        except Exception as e:
            logger.error(f"Error exporting LoRAs to config: {e}")
            return {'default': '', 'available_loras': []}

    def _save_settings(self, settings: Dict[str, Any]) -> bool:
        """Save settings to a JSON file in the lora_editor folder"""
        try:
            # Get the settings file path in the lora_editor folder
            settings_path = Path(__file__).parent.parent / 'lora_settings.json'

            # Load existing settings if available
            existing_settings = {}
            if settings_path.exists():
                with open(settings_path, 'r', encoding='utf-8') as f:
                    try:
                        existing_settings = json.load(f)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in settings file: {settings_path}")

            # Update with new settings
            existing_settings.update(settings)

            # Save to file
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(existing_settings, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved settings to {settings_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False

    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from a JSON file in the lora_editor folder"""
        try:
            # Get the settings file path in the lora_editor folder
            settings_path = Path(__file__).parent.parent / 'lora_settings.json'

            # Load settings if available
            if settings_path.exists():
                with open(settings_path, 'r', encoding='utf-8') as f:
                    try:
                        settings = json.load(f)
                        logger.info(f"Loaded settings from {settings_path}")
                        return settings
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in settings file: {settings_path}")

            return {}
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return {}

    def reset_lora_database(self) -> bool:
        """Reset the LoRA database to default state"""
        try:
            self.db.reset_database()
            self.config = {'default': '', 'available_loras': []}
            return True
        except Exception as e:
            logger.error(f"Error resetting LoRA database: {e}")
            return False

    def check_for_updates(self, lora_id: int) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if a LoRA has updates available on Civitai.

        Args:
            lora_id: The ID of the LoRA to check

        Returns:
            A tuple of (has_update, update_info)
        """
        try:
            # Get the LoRA entry
            lora = self.db.get_lora_by_id(lora_id)
            if not lora:
                logger.warning(f"LoRA with ID {lora_id} not found")
                return False, None

            logger.info(f"Checking for updates for LoRA: {lora.display_name}, File: {lora.file_name}, URL: {lora.url}, Last Updated: {lora.last_updated}")

            # Check if the LoRA has a Civitai URL
            if not lora.url or 'civitai.com' not in lora.url:
                logger.warning(f"LoRA {lora.display_name} does not have a Civitai URL")
                return False, None

            # Check for updates
            has_update, update_info = check_lora_for_updates(lora.url, lora.last_updated, lora.file_name)

            if has_update:
                logger.info(f"Update available for LoRA {lora.display_name}")
            else:
                logger.info(f"No updates available for LoRA {lora.display_name}")

            return has_update, update_info
        except Exception as e:
            logger.error(f"Error checking for updates for LoRA ID {lora_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, None

    def check_all_for_updates(self) -> Dict[int, Dict[str, Any]]:
        """
        Check all LoRAs for updates on Civitai.

        Returns:
            A dictionary mapping LoRA IDs to update information
        """
        updates = {}

        try:
            # Get all LoRAs
            loras = self.db.get_all_loras()

            for lora in loras:
                has_update, update_info = self.check_for_updates(lora.id)
                if has_update and update_info:
                    updates[lora.id] = update_info

            logger.info(f"Found updates for {len(updates)} LoRAs")
            return updates
        except Exception as e:
            logger.error(f"Error checking for updates for all LoRAs: {e}")
            return {}
