"""
Database service for the application.
Provides a centralized way to access the database.
"""

import sqlite3
import logging
import json
import os
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class DatabaseService:
    """
    Database service for the application.
    Provides methods for database access and management.
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one database service exists"""
        if cls._instance is None:
            cls._instance = super(DatabaseService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = "database.db"):
        """
        Initialize the database service.
        
        Args:
            db_path: Path to the database file
        """
        # Only initialize once (singleton pattern)
        if self._initialized:
            return
            
        self.db_path = db_path
        self._initialized = True
        
    def get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection.
        
        Returns:
            A database connection
        """
        return sqlite3.connect(self.db_path)
        
    def execute(self, query: str, params: Tuple = None) -> sqlite3.Cursor:
        """
        Execute a query.
        
        Args:
            query: SQL query to execute
            params: Parameters for the query
            
        Returns:
            The cursor after executing the query
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
            
        return cursor
        
    def execute_many(self, query: str, params_list: List[Tuple]) -> sqlite3.Cursor:
        """
        Execute a query with multiple parameter sets.
        
        Args:
            query: SQL query to execute
            params_list: List of parameter tuples
            
        Returns:
            The cursor after executing the query
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.executemany(query, params_list)
            conn.commit()
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
            
        return cursor
        
    def fetch_one(self, query: str, params: Tuple = None) -> Optional[Tuple]:
        """
        Fetch a single row.
        
        Args:
            query: SQL query to execute
            params: Parameters for the query
            
        Returns:
            A single row or None if no rows were returned
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error fetching row: {e}")
            return None
        finally:
            conn.close()
            
    def fetch_all(self, query: str, params: Tuple = None) -> List[Tuple]:
        """
        Fetch all rows.
        
        Args:
            query: SQL query to execute
            params: Parameters for the query
            
        Returns:
            All rows returned by the query
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching rows: {e}")
            return []
        finally:
            conn.close()
            
    def create_tables(self, schema_file: str):
        """
        Create tables from a schema file.
        
        Args:
            schema_file: Path to the schema file
        """
        try:
            with open(schema_file, 'r') as f:
                schema = f.read()
                
            conn = self.get_connection()
            conn.executescript(schema)
            conn.commit()
            conn.close()
            logger.info(f"Created tables from schema file: {schema_file}")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
            
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists.
        
        Args:
            table_name: Name of the table
            
        Returns:
            True if the table exists, False otherwise
        """
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = self.fetch_one(query, (table_name,))
        return result is not None
        
    def create_table(self, table_name: str, columns: Dict[str, str], if_not_exists: bool = True):
        """
        Create a table.
        
        Args:
            table_name: Name of the table
            columns: Dictionary mapping column names to their definitions
            if_not_exists: Whether to add IF NOT EXISTS to the query
        """
        column_defs = ", ".join([f"{name} {definition}" for name, definition in columns.items()])
        exists_clause = "IF NOT EXISTS " if if_not_exists else ""
        query = f"CREATE TABLE {exists_clause}{table_name} ({column_defs})"
        
        try:
            self.execute(query)
            logger.info(f"Created table: {table_name}")
        except Exception as e:
            logger.error(f"Error creating table {table_name}: {e}")
            raise
            
    def drop_table(self, table_name: str, if_exists: bool = True):
        """
        Drop a table.
        
        Args:
            table_name: Name of the table
            if_exists: Whether to add IF EXISTS to the query
        """
        exists_clause = "IF EXISTS " if if_exists else ""
        query = f"DROP TABLE {exists_clause}{table_name}"
        
        try:
            self.execute(query)
            logger.info(f"Dropped table: {table_name}")
        except Exception as e:
            logger.error(f"Error dropping table {table_name}: {e}")
            raise
            
    def insert(self, table_name: str, data: Dict[str, Any]) -> int:
        """
        Insert data into a table.
        
        Args:
            table_name: Name of the table
            data: Dictionary mapping column names to values
            
        Returns:
            The ID of the inserted row
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, tuple(data.values()))
            row_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return row_id
        except Exception as e:
            logger.error(f"Error inserting into {table_name}: {e}")
            raise
            
    def update(self, table_name: str, data: Dict[str, Any], condition: str, condition_params: Tuple) -> int:
        """
        Update data in a table.
        
        Args:
            table_name: Name of the table
            data: Dictionary mapping column names to values
            condition: WHERE clause
            condition_params: Parameters for the WHERE clause
            
        Returns:
            The number of rows affected
        """
        set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {condition}"
        params = tuple(data.values()) + condition_params
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            row_count = cursor.rowcount
            conn.commit()
            conn.close()
            return row_count
        except Exception as e:
            logger.error(f"Error updating {table_name}: {e}")
            raise
            
    def delete(self, table_name: str, condition: str, condition_params: Tuple) -> int:
        """
        Delete data from a table.
        
        Args:
            table_name: Name of the table
            condition: WHERE clause
            condition_params: Parameters for the WHERE clause
            
        Returns:
            The number of rows affected
        """
        query = f"DELETE FROM {table_name} WHERE {condition}"
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, condition_params)
            row_count = cursor.rowcount
            conn.commit()
            conn.close()
            return row_count
        except Exception as e:
            logger.error(f"Error deleting from {table_name}: {e}")
            raise
