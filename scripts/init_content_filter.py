"""
Script to initialize content filter tables.
"""

import sys
import os
import time
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.database.database_service import DatabaseService

def init_content_filter_tables():
    """Initialize content filter tables"""
    db_service = DatabaseService()
    
    # Create banned words table
    db_service.create_table(
        "banned_words",
        {
            "word": "TEXT PRIMARY KEY",
            "added_at": "REAL NOT NULL"
        }
    )
    print("Created banned_words table")
    
    # Create regex patterns table
    db_service.create_table(
        "regex_patterns",
        {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT NOT NULL",
            "pattern": "TEXT NOT NULL",
            "description": "TEXT",
            "severity": "TEXT NOT NULL",
            "added_at": "REAL NOT NULL"
        }
    )
    print("Created regex_patterns table")
    
    # Create context rules table
    db_service.create_table(
        "context_rules",
        {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "trigger_word": "TEXT NOT NULL",
            "allowed_contexts": "TEXT",
            "disallowed_contexts": "TEXT",
            "description": "TEXT",
            "added_at": "REAL NOT NULL"
        }
    )
    print("Created context_rules table")
    
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
    print("Created filter_violations table")
    
    # Add some default banned words
    default_banned_words = [
        "nsfw",
        "nude",
        "naked",
        "porn",
        "explicit"
    ]
    
    for word in default_banned_words:
        try:
            db_service.insert(
                "banned_words",
                {
                    "word": word,
                    "added_at": time.time()
                }
            )
            print(f"Added banned word: {word}")
        except:
            # Word might already exist
            pass

if __name__ == "__main__":
    init_content_filter_tables()
