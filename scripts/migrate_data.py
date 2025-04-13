"""
Script to migrate data from the old structure to the new structure.
"""

import os
import sys
import json
import sqlite3
import logging
import shutil
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/migration.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Import application components
from src.infrastructure.database.database_service import DatabaseService

def migrate_database(old_db_path: str, new_db_path: str):
    """
    Migrate data from the old database to the new database.
    
    Args:
        old_db_path: Path to the old database
        new_db_path: Path to the new database
    """
    logger.info(f"Migrating database from {old_db_path} to {new_db_path}")
    
    # Check if old database exists
    if not os.path.exists(old_db_path):
        logger.error(f"Old database not found: {old_db_path}")
        return
        
    # Create new database service
    db_service = DatabaseService(new_db_path)
    
    # Connect to old database
    old_conn = sqlite3.connect(old_db_path)
    old_cursor = old_conn.cursor()
    
    try:
        # Get list of tables in old database
        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in old_cursor.fetchall()]
        
        logger.info(f"Found {len(tables)} tables in old database: {tables}")
        
        # Migrate each table
        for table in tables:
            try:
                # Get table schema
                old_cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in old_cursor.fetchall()]
                
                # Get table data
                old_cursor.execute(f"SELECT * FROM {table}")
                rows = old_cursor.fetchall()
                
                logger.info(f"Migrating table {table} with {len(rows)} rows")
                
                # Create table in new database
                # This is a simplified approach; in a real migration, you would need to
                # map the old schema to the new schema
                column_defs = {}
                for i, column in enumerate(columns):
                    # Get column type
                    old_cursor.execute(f"PRAGMA table_info({table})")
                    column_type = old_cursor.fetchall()[i][2]
                    column_defs[column] = column_type
                    
                # Create table
                db_service.create_table(table, column_defs)
                
                # Insert data
                for row in rows:
                    data = {columns[i]: row[i] for i in range(len(columns))}
                    db_service.insert(table, data)
                    
                logger.info(f"Migrated table {table}")
                
            except Exception as e:
                logger.error(f"Error migrating table {table}: {e}")
                
    except Exception as e:
        logger.error(f"Error migrating database: {e}")
        
    finally:
        old_conn.close()
        
def migrate_config(old_config_dir: str, new_config_dir: str):
    """
    Migrate configuration files from the old directory to the new directory.
    
    Args:
        old_config_dir: Path to the old configuration directory
        new_config_dir: Path to the new configuration directory
    """
    logger.info(f"Migrating configuration from {old_config_dir} to {new_config_dir}")
    
    # Check if old config directory exists
    if not os.path.exists(old_config_dir):
        logger.error(f"Old config directory not found: {old_config_dir}")
        return
        
    # Create new config directory if it doesn't exist
    os.makedirs(new_config_dir, exist_ok=True)
    
    try:
        # Copy all JSON files
        for file in os.listdir(old_config_dir):
            if file.endswith('.json'):
                old_path = os.path.join(old_config_dir, file)
                new_path = os.path.join(new_config_dir, file)
                
                shutil.copy2(old_path, new_path)
                logger.info(f"Copied {file} to {new_path}")
                
    except Exception as e:
        logger.error(f"Error migrating configuration: {e}")
        
def migrate_env(old_env_path: str, new_env_path: str):
    """
    Migrate environment variables from the old .env file to the new .env file.
    
    Args:
        old_env_path: Path to the old .env file
        new_env_path: Path to the new .env file
    """
    logger.info(f"Migrating environment variables from {old_env_path} to {new_env_path}")
    
    # Check if old .env file exists
    if not os.path.exists(old_env_path):
        logger.error(f"Old .env file not found: {old_env_path}")
        return
        
    try:
        # Read old .env file
        with open(old_env_path, 'r', encoding='utf-8') as f:
            env_vars = f.readlines()
            
        # Write to new .env file
        with open(new_env_path, 'w', encoding='utf-8') as f:
            f.writelines(env_vars)
            
        logger.info(f"Migrated environment variables to {new_env_path}")
        
    except Exception as e:
        logger.error(f"Error migrating environment variables: {e}")
        
def main():
    """Main function"""
    logger.info("Starting data migration")
    
    # Define paths
    old_db_path = "database.db"
    new_db_path = "database_new.db"
    old_config_dir = "."
    new_config_dir = "config"
    old_env_path = ".env"
    new_env_path = ".env"
    
    # Create directories
    os.makedirs("logs", exist_ok=True)
    os.makedirs("config", exist_ok=True)
    
    # Migrate database
    migrate_database(old_db_path, new_db_path)
    
    # Migrate configuration
    migrate_config(old_config_dir, new_config_dir)
    
    # Migrate environment variables
    migrate_env(old_env_path, new_env_path)
    
    logger.info("Data migration complete")
    
if __name__ == "__main__":
    main()
