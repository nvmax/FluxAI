import os
import re
import logging
import requests
from urllib.parse import urlparse
from huggingface_hub import HfApi, hf_hub_download, hf_hub_url

logger = logging.getLogger(__name__)

class HuggingFaceDownloader:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.hf_token = os.getenv('HUGGINGFACE_TOKEN')

    def get_repo_files(self, repo_id: str) -> list:
        """Get list of .safetensors files in a HuggingFace repository"""
        try:
            api = HfApi(token=self.hf_token)
            files = api.list_repo_files(repo_id)
            return [f for f in files if f.endswith('.safetensors')]
        except Exception as e:
            logger.error(f"Error getting repo files: {e}")
            raise

    def download_file(self, repo_id: str, filename: str, dest_folder: str) -> str:
        """Download a file from HuggingFace with progress updates"""
        try:
            dest_path = os.path.join(dest_folder, filename)

            # Get the direct download URL
            file_url = hf_hub_url(repo_id=repo_id, filename=filename, revision="main")
            logger.info(f"Downloading from URL: {file_url}")

            # Set up headers with token if available
            headers = {}
            if self.hf_token:
                headers['Authorization'] = f'Bearer {self.hf_token}'

            # Stream the download with progress updates
            response = requests.get(file_url, headers=headers, stream=True)
            response.raise_for_status()

            # Get total file size
            total_size = int(response.headers.get('content-length', 0))
            logger.info(f"Total file size: {total_size} bytes")

            # Create directory if it doesn't exist
            os.makedirs(dest_folder, exist_ok=True)

            # Check if file already exists
            if os.path.exists(dest_path):
                logger.info(f"File already exists at {dest_path}")
                try:
                    # Try to remove the existing file
                    os.remove(dest_path)
                    logger.info(f"Successfully removed existing file at {dest_path}")
                except Exception as e:
                    logger.error(f"Failed to remove existing file: {e}")
                    raise ValueError(f"File already exists at {dest_path} and could not be removed")

            # Use a larger block size for smoother downloads
            block_size = 8192  # 8 KB
            update_interval = 0.1  # Update UI every 100ms
            last_update_time = 0
            import time
            downloaded = 0

            with open(dest_path, 'wb') as f:
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    f.write(data)

                    # Only update progress periodically to reduce UI jitter
                    current_time = time.time()
                    if self.progress_callback and total_size and (current_time - last_update_time) >= update_interval:
                        progress = (downloaded / total_size) * 100
                        self.progress_callback(progress)
                        last_update_time = current_time

            logger.info(f"Download complete: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            raise

    def extract_repo_info(self, url: str) -> tuple:
        """Extract repository ID and filename from HuggingFace URL"""
        try:
            # Remove trailing slash if present
            url = url.rstrip('/')

            # Extract repo ID from URL
            if '/blob/' in url:
                # URL format: https://huggingface.co/repo_id/blob/main/filename
                match = re.match(r'https://huggingface\.co/([^/]+/[^/]+)/blob/[^/]+/(.+)', url)
                if match:
                    return match.group(1), match.group(2)
            else:
                # URL format: https://huggingface.co/repo_id/resolve/main/filename
                match = re.match(r'https://huggingface\.co/([^/]+/[^/]+)(?:/resolve/[^/]+)?/(.+)', url)
                if match:
                    return match.group(1), match.group(2)

            # If it's just a repository URL, try to find safetensors files
            match = re.match(r'https://huggingface\.co/([^/]+/[^/]+)/?$', url)
            if match:
                repo_id = match.group(1)
                logger.info(f"Found repository ID: {repo_id}")

                # Get list of safetensors files
                files = self.get_repo_files(repo_id)
                if files:
                    logger.info(f"Found files in repository: {files}")
                    return repo_id, files[0]  # Return the first safetensors file

            raise ValueError("Could not extract repository info from URL")

        except Exception as e:
            logger.error(f"Error extracting repo info: {e}")
            raise

    def download(self, url: str, dest_folder: str, progress_callback=None) -> tuple:
        """Download a LoRA model from HuggingFace"""
        try:
            if progress_callback:
                self.progress_callback = progress_callback

            # Extract repository ID and filename
            repo_id, filename = self.extract_repo_info(url)
            logger.info(f"Downloading {filename} from {repo_id}")

            # Download the file
            filename = self.download_file(repo_id, filename, dest_folder)

            # For LoRA files, we don't have trigger words from HuggingFace
            # Use the filename as a default trigger word
            trigger_words = os.path.splitext(filename)[0].replace('_', ' ')

            return filename, trigger_words

        except Exception as e:
            logger.error(f"Error downloading from HuggingFace: {e}")
            raise
