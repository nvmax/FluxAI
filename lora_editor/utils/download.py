"""
Utilities for downloading files
"""
import os
import requests
import logging
from typing import Optional, Callable
from pathlib import Path
import threading
from dotenv import load_dotenv
import re

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_model_info(url: str) -> Optional[dict]:
    """
    Get model information from CivitAI API
    """
    try:
        # Extract model version ID from URL
        match = re.search(r'models/(\d+)(?:\?|$)', url)
        if not match:
            # Try alternate pattern for download URLs
            match = re.search(r'download/models/(\d+)(?:\?|$)', url)
            
        if match:
            model_version_id = match.group(1)
            
            # Set up headers with API token
            headers = {
                'Authorization': f'Bearer {os.getenv("CIVITAI_API_TOKEN")}'
            }
            
            # First get the model info to get the model ID
            api_url = f'https://civitai.com/api/v1/models/{model_version_id}'
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            model_data = response.json()

            # Get the latest version info
            if model_data.get('modelVersions'):
                latest_version = model_data['modelVersions'][0]  # Versions are sorted by date, newest first
                logger.info(f"Latest version: {latest_version.get('name')}, created at: {latest_version.get('createdAt')}")
                return latest_version
            
            return None
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        return None

def download_file(url: str, 
                 destination_folder: str, 
                 filename: Optional[str] = None,
                 progress_callback: Optional[Callable[[float], None]] = None) -> Optional[str]:
    """
    Download a file from a URL to a destination folder
    
    Args:
        url: The URL to download from
        destination_folder: The folder to save the file to
        filename: Optional filename to use (if None, uses the filename from the API)
        progress_callback: Optional callback function that receives progress (0.0 to 1.0)
        
    Returns:
        The path to the downloaded file, or None if download failed
    """
    try:
        logger.info(f"Downloading file from {url}")
        
        # Create the destination folder if it doesn't exist
        os.makedirs(destination_folder, exist_ok=True)

        # Set up headers with API token
        headers = {
            'Authorization': f'Bearer {os.getenv("CIVITAI_API_TOKEN")}'
        }

        # First make a request to get the download URL and headers
        with requests.get(url, stream=True, headers=headers, allow_redirects=False) as response:
            if response.status_code == 307:  # Temporary redirect
                download_url = response.headers['Location']
                logger.info(f"Following redirect to: {download_url}")
            else:
                download_url = url

        # Now download from the actual URL
        with requests.get(download_url, stream=True) as response:
            response.raise_for_status()
            
            # Try to get filename from Content-Disposition header if not provided
            if not filename and 'Content-Disposition' in response.headers:
                content_disp = response.headers['Content-Disposition']
                # Extract filename="something.safetensors"
                import re
                match = re.search(r'filename=(?:"([^"]+)"|([^;\n]+))', content_disp)
                if match:
                    filename = match.group(1) or match.group(2)
                    logger.info(f"Using filename from Content-Disposition: {filename}")

            # If still no filename, try API
            if not filename:
                model_info = get_model_info(url)
                if model_info and 'files' in model_info and len(model_info['files']) > 0:
                    # Get the first primary file (usually the model file)
                    primary_files = [f for f in model_info['files'] if f.get('type') == 'Model']
                    if primary_files:
                        filename = primary_files[0]['name']
                        logger.info(f"Using primary file name from API: {filename}")
                    else:
                        filename = model_info['files'][0]['name']
                        logger.info(f"Using first file name from API: {filename}")
                else:
                    # Fallback to URL filename if API call fails
                    filename = url.split('/')[-1]
                    if '?' in filename:
                        filename = filename.split('?')[0]
                    logger.info(f"Using fallback filename: {filename}")
            
            # Full path to save the file
            file_path = os.path.join(destination_folder, filename)
            
            # Get the file size if available
            total_size = int(response.headers.get('content-length', 0))
            
            # Download the file
            with open(file_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Report progress if callback provided and total size known
                        if progress_callback and total_size > 0:
                            progress = downloaded / total_size
                            progress_callback(progress)
        
        logger.info(f"Download complete: {file_path}")
        return file_path
    
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def download_file_async(url: str, 
                       destination_folder: str, 
                       filename: Optional[str] = None,
                       progress_callback: Optional[Callable[[float], None]] = None,
                       completion_callback: Optional[Callable[[Optional[str]], None]] = None):
    """
    Download a file asynchronously
    
    Args:
        url: The URL to download from
        destination_folder: The folder to save the file to
        filename: Optional filename to use (if None, uses the filename from the URL)
        progress_callback: Optional callback function that receives progress (0.0 to 1.0)
        completion_callback: Optional callback function that receives the downloaded file path
    """
    def _download_thread():
        result = download_file(url, destination_folder, filename, progress_callback)
        if completion_callback:
            completion_callback(result)
    
    # Start the download in a separate thread
    thread = threading.Thread(target=_download_thread)
    thread.daemon = True
    thread.start()
    
    return thread
