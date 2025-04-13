"""
Repository for queue data access.
"""

import json
import logging
import time
import sqlite3
from typing import Dict, Any, List, Optional, Tuple

from src.domain.interfaces.queue_repository import QueueRepository
from src.domain.models.queue_item import QueueItem, QueueStatus
from src.infrastructure.database.database_service import DatabaseService

logger = logging.getLogger(__name__)

class SQLiteQueueRepository(QueueRepository):
    """
    SQLite implementation of the queue repository.
    Handles persistence of queue items in a SQLite database.
    """
    
    def __init__(self, database_service: DatabaseService, db_path: str = "queue.db"):
        """
        Initialize the queue repository.
        
        Args:
            database_service: Database service for database access
            db_path: Path to the database file
        """
        self.database_service = database_service
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Initialize the database schema"""
        try:
            # Create queue items table
            self.database_service.create_table(
                "queue_items",
                {
                    "request_id": "TEXT PRIMARY KEY",
                    "request_data": "TEXT NOT NULL",
                    "priority": "INTEGER NOT NULL",
                    "user_id": "TEXT NOT NULL",
                    "added_at": "REAL NOT NULL",
                    "started_at": "REAL",
                    "completed_at": "REAL",
                    "status": "TEXT NOT NULL",
                    "error_message": "TEXT"
                }
            )
            
            # Create user rate limits table
            self.database_service.create_table(
                "user_rate_limits",
                {
                    "user_id": "TEXT PRIMARY KEY",
                    "request_count": "INTEGER NOT NULL",
                    "last_request_time": "REAL NOT NULL"
                }
            )
            
            logger.info("Queue database initialized")
        except Exception as e:
            logger.error(f"Error initializing queue database: {e}")
            raise
        
    async def save_item(self, item: QueueItem) -> bool:
        """
        Save a queue item.
        
        Args:
            item: Queue item to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert request item to JSON
            request_data = json.dumps(item.to_dict())
            
            # Insert into database
            self.database_service.insert(
                "queue_items",
                {
                    "request_id": item.request_id,
                    "request_data": request_data,
                    "priority": item.priority,
                    "user_id": item.user_id,
                    "added_at": item.added_at,
                    "started_at": item.started_at,
                    "completed_at": item.completed_at,
                    "status": item.status.value,
                    "error_message": item.error_message
                }
            )
            
            logger.debug(f"Saved queue item: {item.request_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving queue item: {e}")
            return False
        
    async def get_pending_items(self) -> List[QueueItem]:
        """
        Get all pending items.
        
        Returns:
            List of pending queue items
        """
        try:
            # Get pending items from database
            rows = self.database_service.fetch_all(
                "SELECT request_data FROM queue_items WHERE status = ? ORDER BY priority, added_at",
                (QueueStatus.PENDING.value,)
            )
            
            # Convert to queue items
            items = []
            for row in rows:
                try:
                    data = json.loads(row[0])
                    items.append(QueueItem.from_dict(data))
                except Exception as e:
                    logger.error(f"Error parsing queue item: {e}")
                    
            logger.debug(f"Got {len(items)} pending queue items")
            return items
        except Exception as e:
            logger.error(f"Error getting pending queue items: {e}")
            return []
        
    async def update_item_status(self, request_id: str, status: str, 
                                started_at: Optional[float] = None, 
                                completed_at: Optional[float] = None,
                                error_message: Optional[str] = None) -> bool:
        """
        Update a queue item's status.
        
        Args:
            request_id: ID of the request to update
            status: New status
            started_at: Time the request started processing
            completed_at: Time the request completed processing
            error_message: Error message if the request failed
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build update data
            update_data = {"status": status}
            if started_at is not None:
                update_data["started_at"] = started_at
            if completed_at is not None:
                update_data["completed_at"] = completed_at
            if error_message is not None:
                update_data["error_message"] = error_message
                
            # Update in database
            self.database_service.update(
                "queue_items",
                update_data,
                "request_id = ?",
                (request_id,)
            )
            
            logger.debug(f"Updated queue item status: {request_id} -> {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating queue item status: {e}")
            return False
        
    async def get_user_request_count(self, user_id: str, time_window: float) -> int:
        """
        Get the number of requests a user has made in a time window.
        
        Args:
            user_id: User ID
            time_window: Time window in seconds
            
        Returns:
            Number of requests
        """
        try:
            # Calculate cutoff time
            cutoff_time = time.time() - time_window
            
            # Get count from database
            row = self.database_service.fetch_one(
                "SELECT COUNT(*) FROM queue_items WHERE user_id = ? AND added_at > ?",
                (user_id, cutoff_time)
            )
            
            count = row[0] if row else 0
            logger.debug(f"User {user_id} has made {count} requests in the last {time_window/3600:.1f} hours")
            return count
        except Exception as e:
            logger.error(f"Error getting user request count: {e}")
            return 0
        
    async def update_user_rate_limit(self, user_id: str) -> bool:
        """
        Update a user's rate limit.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current rate limit
            row = self.database_service.fetch_one(
                "SELECT request_count, last_request_time FROM user_rate_limits WHERE user_id = ?",
                (user_id,)
            )
            
            current_time = time.time()
            
            if row:
                # Update existing rate limit
                request_count = row[0] + 1
                self.database_service.update(
                    "user_rate_limits",
                    {
                        "request_count": request_count,
                        "last_request_time": current_time
                    },
                    "user_id = ?",
                    (user_id,)
                )
            else:
                # Insert new rate limit
                self.database_service.insert(
                    "user_rate_limits",
                    {
                        "user_id": user_id,
                        "request_count": 1,
                        "last_request_time": current_time
                    }
                )
                
            logger.debug(f"Updated rate limit for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating user rate limit: {e}")
            return False
        
    async def get_queue_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get queue statistics.
        
        Args:
            days: Number of days to get statistics for
            
        Returns:
            Queue statistics
        """
        try:
            # Calculate cutoff time
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            
            # Get stats from database
            stats = []
            
            # Total items
            row = self.database_service.fetch_one(
                "SELECT COUNT(*) FROM queue_items WHERE added_at > ?",
                (cutoff_time,)
            )
            total_items = row[0] if row else 0
            
            # Completed items
            row = self.database_service.fetch_one(
                "SELECT COUNT(*) FROM queue_items WHERE status = ? AND added_at > ?",
                (QueueStatus.COMPLETED.value, cutoff_time)
            )
            completed_items = row[0] if row else 0
            
            # Failed items
            row = self.database_service.fetch_one(
                "SELECT COUNT(*) FROM queue_items WHERE status = ? AND added_at > ?",
                (QueueStatus.FAILED.value, cutoff_time)
            )
            failed_items = row[0] if row else 0
            
            # Average processing time
            row = self.database_service.fetch_one(
                "SELECT AVG(completed_at - started_at) FROM queue_items WHERE status = ? AND added_at > ? AND started_at IS NOT NULL AND completed_at IS NOT NULL",
                (QueueStatus.COMPLETED.value, cutoff_time)
            )
            avg_processing_time = row[0] if row and row[0] is not None else 0
            
            # Unique users
            row = self.database_service.fetch_one(
                "SELECT COUNT(DISTINCT user_id) FROM queue_items WHERE added_at > ?",
                (cutoff_time,)
            )
            unique_users = row[0] if row else 0
            
            stats.append({
                "total_items": total_items,
                "completed_items": completed_items,
                "failed_items": failed_items,
                "avg_processing_time": avg_processing_time,
                "unique_users": unique_users,
                "days": days
            })
            
            logger.debug(f"Got queue stats for {days} days")
            return stats
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return []
