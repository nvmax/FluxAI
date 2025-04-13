"""
Script to migrate banned words from banned.json to the database.
"""

import os
import json
import sys
import time
import logging

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infrastructure.database.database_service import DatabaseService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def migrate_banned_words():
    """Migrate banned words from banned.json to the database"""
    try:
        # Initialize database service
        db_service = DatabaseService()
        
        # Create banned_words table if it doesn't exist
        db_service.create_table(
            "banned_words",
            {
                "word": "TEXT PRIMARY KEY",
                "added_at": "REAL NOT NULL"
            }
        )
        logger.info("Created or verified banned_words table")
        
        # Load banned words from banned.json
        banned_json_path = os.path.join('Main', 'banned.json')
        if not os.path.exists(banned_json_path):
            logger.error(f"Banned words file not found: {banned_json_path}")
            return
            
        with open(banned_json_path, 'r') as f:
            banned_words = json.load(f)
            
        logger.info(f"Loaded {len(banned_words)} banned words from {banned_json_path}")
        
        # Insert banned words into the database
        count = 0
        for word in banned_words:
            try:
                db_service.insert(
                    "banned_words",
                    {
                        "word": word.lower().strip(),
                        "added_at": time.time()
                    }
                )
                count += 1
            except Exception as e:
                # Word might already exist
                logger.warning(f"Could not insert word '{word}': {e}")
                
        logger.info(f"Successfully migrated {count} banned words to the database")
        
        # Verify the migration
        rows = db_service.fetch_all("SELECT COUNT(*) FROM banned_words")
        total_words = rows[0][0] if rows else 0
        logger.info(f"Total banned words in database: {total_words}")
        
    except Exception as e:
        logger.error(f"Error migrating banned words: {e}", exc_info=True)

if __name__ == "__main__":
    migrate_banned_words()
