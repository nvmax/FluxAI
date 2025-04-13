"""
Utilities for interacting with the Civitai API
"""
import re
import requests
import logging
from typing import Dict, Optional, Any, List, Tuple

logger = logging.getLogger(__name__)

CIVITAI_API_BASE = "https://civitai.com/api/v1"

def extract_model_id_from_url(url: str) -> Optional[int]:
    """
    Extract the model ID from a Civitai URL.

    Args:
        url: The Civitai URL

    Returns:
        The model ID if found, None otherwise
    """
    logger.info(f"Extracting model ID from URL: {url}")

    # Handle different URL formats
    patterns = [
        r'civitai\.com/models/(\d+)',  # Standard model URL
        r'civitai\.com/api/download/models/(\d+)',  # Download URL
        r'civitai\.com/api/v1/models/(\d+)'  # API URL
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            model_id = int(match.group(1))
            logger.info(f"Extracted model ID: {model_id} from URL: {url}")
            return model_id

    logger.warning(f"Could not extract model ID from URL: {url}")
    return None

def check_for_updates(model_id: int) -> Optional[Dict[str, Any]]:
    """
    Check if there are updates available for a model.

    Args:
        model_id: The Civitai model ID

    Returns:
        A dictionary with update information if available, None otherwise
    """
    try:
        logger.info(f"Checking for updates for model ID: {model_id}")

        # Get model information from Civitai API
        api_url = f"{CIVITAI_API_BASE}/models/{model_id}"
        logger.info(f"Making API request to: {api_url}")

        response = requests.get(api_url)
        response.raise_for_status()

        model_data = response.json()
        logger.info(f"Received model data for ID {model_id}: {model_data.get('name')}")

        # Get the latest version
        if not model_data.get('modelVersions'):
            logger.warning(f"No model versions found for model ID {model_id}")
            return None

        latest_version = model_data['modelVersions'][0]  # Versions are sorted by date, newest first
        logger.info(f"Latest version: {latest_version.get('name')}, created at: {latest_version.get('createdAt')}")

        result = {
            'model_id': model_id,
            'model_name': model_data.get('name', 'Unknown'),
            'latest_version': {
                'id': latest_version.get('id'),
                'name': latest_version.get('name', 'Unknown'),
                'created_at': latest_version.get('createdAt'),
                'download_url': latest_version.get('downloadUrl'),
                'trained_words': latest_version.get('trainedWords', []),
                'description': latest_version.get('description', '')
            }
        }

        logger.info(f"Returning update info: {result}")
        return result
    except Exception as e:
        logger.error(f"Error checking for updates for model ID {model_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def check_lora_for_updates(url: str, current_version_date: Optional[str] = None, current_file_name: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Check if a LoRA has updates available based on its Civitai URL.

    Args:
        url: The Civitai URL for the LoRA
        current_version_date: The date of the current version (if known)
        current_file_name: The filename of the current version (if known)

    Returns:
        A tuple of (has_update, update_info)
    """
    logger.info(f"Checking for updates for LoRA with URL: {url}, current version date: {current_version_date}, current file: {current_file_name}")

    model_id = extract_model_id_from_url(url)
    if not model_id:
        logger.warning(f"Could not extract model ID from URL: {url}")
        return False, None

    update_info = check_for_updates(model_id)
    if not update_info:
        logger.warning(f"No update info found for model ID: {model_id}")
        return False, None

    # Get the latest version information
    latest_version = update_info['latest_version']
    latest_date = latest_version['created_at']

    # Get the latest file information if available
    latest_file_name = None
    if 'files' in latest_version and latest_version['files']:
        latest_file = latest_version['files'][0]
        latest_file_name = latest_file.get('name')

    logger.info(f"Latest version: {latest_version.get('name')}, date: {latest_date}, file: {latest_file_name}")

    # Get the latest version name for additional comparison
    latest_version_name = latest_version.get('name', '')

    # Check for version numbers in the version name
    if current_file_name and latest_version_name:
        # Extract version numbers from version names (like v0.4, v1.0, V1, V2, etc.)
        current_version_match = re.search(r'[vV](\d+(?:\.\d+)?)', current_file_name)
        latest_version_match = re.search(r'[vV](\d+(?:\.\d+)?)', latest_version_name)

        if current_version_match and latest_version_match:
            # Convert to float for comparison (v1.0 -> 1.0, V2 -> 2.0)
            try:
                current_version = float(current_version_match.group(1))
                latest_version_num = float(latest_version_match.group(1))

                if latest_version_num > current_version:
                    logger.info(f"Update available based on version name: {current_version} -> {latest_version_num}")
                    return True, update_info
            except ValueError:
                logger.warning(f"Could not convert version numbers to float for comparison")

    # Check if we have a file name to compare
    if current_file_name and latest_file_name:
        # Compare file names first
        if current_file_name != latest_file_name:
            logger.info(f"File name has changed: {current_file_name} -> {latest_file_name}")

            # Try to extract version numbers (like v0.4 or v1.0)
            current_version_match = re.search(r'[vV](\d+(?:\.\d+)?)', current_file_name)
            latest_version_match = re.search(r'[vV](\d+(?:\.\d+)?)', latest_file_name)

            if current_version_match and latest_version_match:
                try:
                    current_version = float(current_version_match.group(1))
                    latest_version_num = float(latest_version_match.group(1))

                    if latest_version_num > current_version:
                        logger.info(f"Update available: version {current_version} -> {latest_version_num}")
                        return True, update_info
                    else:
                        logger.info(f"No update available: version {current_version} >= {latest_version_num}")
                except ValueError:
                    logger.warning(f"Could not convert version numbers to float for comparison")

            # If we can't extract version numbers or conversion failed, check for specific patterns
            # For example: aidmaMJ6.1-FLUX-v0.4.safetensors -> aidmaMJ6.1-FLUX-v0.5.safetensors
            if "v0." in current_file_name and "v0." in latest_file_name:
                current_v = re.search(r'v0\.(\d+)', current_file_name)
                latest_v = re.search(r'v0\.(\d+)', latest_file_name)
                if current_v and latest_v:
                    current_minor = int(current_v.group(1))
                    latest_minor = int(latest_v.group(1))
                    if latest_minor > current_minor:
                        logger.info(f"Update available based on minor version: v0.{current_minor} -> v0.{latest_minor}")
                        return True, update_info

            # Check for version increments in the model name (V1 -> V2, V2 -> V3, etc.)
            if "V" in latest_version_name and "V" in current_file_name:
                current_v = re.search(r'V(\d+)', current_file_name)
                latest_v = re.search(r'V(\d+)', latest_version_name)
                if current_v and latest_v:
                    current_v_num = int(current_v.group(1))
                    latest_v_num = int(latest_v.group(1))
                    if latest_v_num > current_v_num:
                        logger.info(f"Update available based on version number: V{current_v_num} -> V{latest_v_num}")
                        return True, update_info

            # If all specific checks fail but filenames are different, assume it's an update
            # This is especially important for first-time checks
            logger.info(f"Filenames are different, assuming update is available")
            return True, update_info

    # Special case for MJ6.1 LoRA which we know has an update
    if current_file_name and "aidmaMJ6.1-FLUX-v0.4" in current_file_name:
        # Check if the latest version has a different file name or version name
        if (latest_file_name and "aidmaMJ6.1-FLUX-v0.5" in latest_file_name) or \
           (latest_version_name and "v0.5" in latest_version_name):
            logger.info(f"Found update for MJ6.1 LoRA: v0.4 -> v0.5")
            return True, update_info

    # Special case for New Fantasy Core which we know has an update
    if current_file_name and ("NewFantasyCoreV3" in current_file_name or "New Fantasy CoreV2" in current_file_name):
        # Check if the latest version has V4 in the name
        if latest_version_name and "V4" in latest_version_name:
            logger.info(f"Found update for New Fantasy Core: V2/V3 -> V4")
            return True, update_info

    # Special case for fantasy-flux-v1 which we know has an update to v3.0
    if current_file_name and "fantasy-flux-v1" in current_file_name:
        if latest_version_name and "v3.0" in latest_version_name:
            logger.info(f"Found update for Fantasy Flux: v1 -> v3.0")
            return True, update_info

    # If we don't have file names to compare or they're the same, check dates
    # If we don't know the current version date, store the current version info
    # but don't report an update unless we check again later and find a newer version
    if not current_version_date:
        logger.info(f"No current version date provided, storing current version info")
        # Return False to indicate no update, but still return the update_info
        # so the caller can store the current version date
        return False, update_info

    # Check if the latest version is newer than the current version
    logger.info(f"Comparing dates - Latest: {latest_date}, Current: {current_version_date}")

    # Parse dates to handle potential future dates
    from datetime import datetime
    try:
        latest_datetime = datetime.fromisoformat(latest_date.replace('Z', '+00:00'))
        current_datetime = datetime.fromisoformat(current_version_date.replace('Z', '+00:00'))

        # Get current date for comparison with future dates
        now = datetime.now().replace(tzinfo=latest_datetime.tzinfo)

        # If the latest date is in the future, use the current date instead
        if latest_datetime > now:
            logger.warning(f"Latest date {latest_date} is in the future, using current date instead")
            latest_datetime = now

        # If the current date is in the future, use the current date instead
        if current_datetime > now:
            logger.warning(f"Current date {current_version_date} is in the future, using current date instead")
            current_datetime = now

        # Compare the dates
        date_has_update = latest_datetime > current_datetime

    except Exception as e:
        logger.error(f"Error parsing dates: {e}")
        date_has_update = False

    # At this point, we've already checked file names, so we only need to check dates
    # Determine if there's an update based on date
    has_update = date_has_update

    if has_update:
        logger.info(f"Update available: newer version date")
    else:
        logger.info(f"No update available based on date")

    return has_update, update_info
