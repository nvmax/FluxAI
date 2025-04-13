"""
Script to copy banned words from Main\banned.json to src\application\content_filter\banned_words.json
"""

import os
import json
import sys
import logging

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def copy_banned_words():
    """Copy banned words from Main\banned.json to src\application\content_filter\banned_words.json"""
    try:
        # Source file path
        source_path = os.path.join('Main', 'banned.json')
        if not os.path.exists(source_path):
            logger.error(f"Source file not found: {source_path}")
            return
            
        # Destination file path
        dest_dir = os.path.join('src', 'application', 'content_filter')
        dest_path = os.path.join(dest_dir, 'banned_words.json')
        
        # Ensure destination directory exists
        os.makedirs(dest_dir, exist_ok=True)
        
        # Load banned words from source file
        with open(source_path, 'r') as f:
            banned_words = json.load(f)
            
        logger.info(f"Loaded {len(banned_words)} banned words from {source_path}")
        
        # Save to destination file
        with open(dest_path, 'w') as f:
            json.dump(banned_words, f, indent=4)
            
        logger.info(f"Saved {len(banned_words)} banned words to {dest_path}")
        
    except Exception as e:
        logger.error(f"Error copying banned words: {e}", exc_info=True)

if __name__ == "__main__":
    copy_banned_words()
