"""
Script to create the filter_violations table if it doesn't exist.
"""

import sys
import os
import time
import sqlite3
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.infrastructure.database.database_service import DatabaseService
    # Use the new database service
    def create_filter_violations_table():
        """Create the filter_violations table using the new database service"""
        logger.info("Creating filter_violations table using DatabaseService")
        db_service = DatabaseService()
        
        # Create filter violations table
        db_service.create_table(
            "filter_violations",
            {
                "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "user_id": "TEXT NOT NULL",
                "prompt": "TEXT NOT NULL",
                "violation_type": "TEXT NOT NULL",
                "violation_details": "TEXT",
                "timestamp": "REAL NOT NULL"
            }
        )
        logger.info("Created filter_violations table")
except ImportError:
    # Fall back to direct SQLite if the new database service is not available
    def create_filter_violations_table():
        """Create the filter_violations table using direct SQLite"""
        logger.info("Creating filter_violations table using direct SQLite")
        db_path = "database.db"
        
        # Check if we should use the legacy database path
        if os.path.exists("image_history.db"):
            db_path = "image_history.db"
            logger.info("Using legacy database: image_history.db")
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Create filter violations table
        c.execute('''CREATE TABLE IF NOT EXISTS filter_violations
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    violation_type TEXT NOT NULL,
                    violation_details TEXT,
                    timestamp REAL NOT NULL)''')
        
        conn.commit()
        conn.close()
        logger.info(f"Created filter_violations table in {db_path}")

def main():
    """Main function"""
    logger.info("Starting filter_violations table creation")
    
    try:
        create_filter_violations_table()
        logger.info("Successfully created filter_violations table")
    except Exception as e:
        logger.error(f"Error creating filter_violations table: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
