"""
Script to create the user_warnings and banned_users tables if they don't exist.
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
    def create_warning_tables():
        """Create the user_warnings and banned_users tables using the new database service"""
        logger.info("Creating warning tables using DatabaseService")
        db_service = DatabaseService()
        
        # Create user_warnings table
        db_service.create_table(
            "user_warnings",
            {
                "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "user_id": "TEXT NOT NULL",
                "prompt": "TEXT NOT NULL",
                "word": "TEXT NOT NULL",
                "warned_at": "REAL NOT NULL"
            }
        )
        logger.info("Created user_warnings table")
        
        # Create banned_users table
        db_service.create_table(
            "banned_users",
            {
                "user_id": "TEXT PRIMARY KEY",
                "reason": "TEXT NOT NULL",
                "banned_at": "REAL NOT NULL"
            }
        )
        logger.info("Created banned_users table")
except ImportError:
    # Fall back to direct SQLite if the new database service is not available
    def create_warning_tables():
        """Create the user_warnings and banned_users tables using direct SQLite"""
        logger.info("Creating warning tables using direct SQLite")
        db_path = "database.db"
        
        # Check if we should use the legacy database path
        if os.path.exists("image_history.db"):
            db_path = "image_history.db"
            logger.info("Using legacy database: image_history.db")
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Create user_warnings table
        c.execute('''CREATE TABLE IF NOT EXISTS user_warnings
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    word TEXT NOT NULL,
                    warned_at REAL NOT NULL)''')
        
        # Create banned_users table
        c.execute('''CREATE TABLE IF NOT EXISTS banned_users
                    (user_id TEXT PRIMARY KEY,
                    reason TEXT NOT NULL,
                    banned_at REAL NOT NULL)''')
        
        conn.commit()
        conn.close()
        logger.info(f"Created warning tables in {db_path}")

def main():
    """Main function"""
    logger.info("Starting warning tables creation")
    
    try:
        create_warning_tables()
        logger.info("Successfully created warning tables")
    except Exception as e:
        logger.error(f"Error creating warning tables: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
