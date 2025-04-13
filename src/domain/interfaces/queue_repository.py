"""
Interface for queue data access.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..models.queue_item import QueueItem

class QueueRepository(ABC):
    """Interface for queue data access"""
    
    @abstractmethod
    async def save_item(self, item: QueueItem) -> bool:
        """
        Save a queue item.
        
        Args:
            item: Queue item to save
            
        Returns:
            True if successful, False otherwise
        """
        pass
        
    @abstractmethod
    async def get_pending_items(self) -> List[QueueItem]:
        """
        Get all pending items.
        
        Returns:
            List of pending queue items
        """
        pass
        
    @abstractmethod
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
        pass
        
    @abstractmethod
    async def get_user_request_count(self, user_id: str, time_window: float) -> int:
        """
        Get the number of requests a user has made in a time window.
        
        Args:
            user_id: User ID
            time_window: Time window in seconds
            
        Returns:
            Number of requests
        """
        pass
        
    @abstractmethod
    async def update_user_rate_limit(self, user_id: str) -> bool:
        """
        Update a user's rate limit.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        pass
        
    @abstractmethod
    async def get_queue_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get queue statistics.
        
        Args:
            days: Number of days to get statistics for
            
        Returns:
            Queue statistics
        """
        pass
