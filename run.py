"""
Run script for the application.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/bot.log', encoding='utf-8')
    ]
)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

logger = logging.getLogger(__name__)

def main():
    """Main function"""
    try:
        # Import the main module
        from src.main import main as app_main
        
        # Run the application
        asyncio.run(app_main())
    except Exception as e:
        logger.error(f"Error running application: {e}", exc_info=True)
        
if __name__ == "__main__":
    main()
