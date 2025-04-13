"""
Service for managing the image generation queue.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple, Callable, Union, Awaitable

from src.domain.models.queue_item import QueueItem, QueueStatus, QueuePriority, RequestItem, ReduxRequestItem, ReduxPromptRequestItem
from src.domain.interfaces.queue_repository import QueueRepository
from src.domain.events.event_bus import EventBus
from src.domain.events.common_events import ImageGenerationRequestedEvent, ImageGenerationCompletedEvent, ImageGenerationFailedEvent

logger = logging.getLogger(__name__)

class QueueService:
    """
    Service for managing the image generation queue.
    Handles adding, processing, and managing queue items.
    """

    def __init__(self,
                 queue_repository: QueueRepository,
                 max_concurrent: int = 3,
                 rate_limit: int = 50,
                 rate_window: float = 3600):
        """
        Initialize the queue service.

        Args:
            queue_repository: Repository for queue data access
            max_concurrent: Maximum number of concurrent requests to process
            rate_limit: Maximum number of requests per user in the rate window
            rate_window: Time window for rate limiting in seconds (default: 1 hour)
        """
        self.repository = queue_repository
        self.queue = asyncio.PriorityQueue()
        self.processing: Dict[str, QueueItem] = {}
        self.max_concurrent = max_concurrent
        self.rate_limit = rate_limit
        self.rate_window = rate_window
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.event_bus = EventBus()

    async def initialize(self):
        """Initialize the queue service and load pending items"""
        await self._load_pending_items()

    async def _load_pending_items(self):
        """Load pending items from the repository"""
        items = await self.repository.get_pending_items()
        logger.info(f"Loaded {len(items)} pending queue items")

        # Add items to the queue
        for item in items:
            await self._add_to_queue(item)

    async def _add_to_queue(self, item: QueueItem):
        """
        Add an item to the priority queue.

        Args:
            item: Queue item to add
        """
        # Add the item directly to the queue
        # The QueueItem class has __lt__ method for priority queue ordering
        await self.queue.put(item)

    async def add_request(self,
                         request_item: Union[RequestItem, ReduxRequestItem, ReduxPromptRequestItem],
                         priority: int = QueuePriority.NORMAL) -> Tuple[bool, str, str]:
        """
        Add a request to the queue.

        Args:
            request_item: The request item to add
            priority: Priority level for the request

        Returns:
            Tuple of (success, request_id, message)
        """
        user_id = request_item.user_id

        # Check rate limit
        request_count = await self.repository.get_user_request_count(user_id, self.rate_window)
        if request_count >= self.rate_limit:
            return False, "", f"Rate limit exceeded. You can make {self.rate_limit} requests per {self.rate_window/3600:.1f} hours."

        # Create queue item
        request_id = str(uuid.uuid4())
        item = QueueItem(
            request_id=request_id,
            request_item=request_item,
            priority=priority,
            user_id=user_id
        )

        # Save to repository
        await self.repository.save_item(item)
        await self.repository.update_user_rate_limit(user_id)

        # Add to queue
        await self._add_to_queue(item)

        # Publish event
        is_video = False
        generation_type = "standard"

        if isinstance(request_item, ReduxRequestItem):
            generation_type = "redux"
        elif isinstance(request_item, ReduxPromptRequestItem):
            generation_type = "reduxprompt"
        elif hasattr(request_item, 'is_pulid') and request_item.is_pulid:
            generation_type = "pulid"

        self.event_bus.publish(ImageGenerationRequestedEvent(
            request_id=request_id,
            user_id=user_id,
            prompt=getattr(request_item, 'prompt', ''),
            resolution=request_item.resolution,
            loras=getattr(request_item, 'loras', []),
            upscale_factor=getattr(request_item, 'upscale_factor', 1),
            seed=getattr(request_item, 'seed', None),
            is_video=is_video,
            generation_type=generation_type
        ))

        position = self.queue.qsize()
        return True, request_id, f"Request added to queue. Position: {position}"

    async def get_next_request(self) -> Optional[QueueItem]:
        """
        Get the next request from the queue.

        Returns:
            Next queue item or None if queue is empty
        """
        if self.queue.empty():
            return None

        # Get item from queue
        item = await self.queue.get()

        # Update status
        item.status = QueueStatus.PROCESSING
        item.started_at = time.time()
        self.processing[item.request_id] = item
        await self.repository.update_item_status(
            item.request_id,
            QueueStatus.PROCESSING.value,
            started_at=item.started_at
        )

        return item

    async def complete_request(self,
                              request_id: str,
                              success: bool,
                              error_message: Optional[str] = None,
                              image_path: Optional[str] = None,
                              generation_time: Optional[float] = None):
        """
        Mark a request as completed.

        Args:
            request_id: ID of the request to complete
            success: Whether the request was successful
            error_message: Error message if the request failed
            image_path: Path to the generated image
            generation_time: Time taken to generate the image
        """
        if request_id not in self.processing:
            logger.warning(f"Request {request_id} not found in processing queue")
            return

        item = self.processing[request_id]
        item.completed_at = time.time()
        item.status = QueueStatus.COMPLETED if success else QueueStatus.FAILED
        item.error_message = error_message

        # Update in repository
        await self.repository.update_item_status(
            request_id,
            item.status.value,
            completed_at=item.completed_at,
            error_message=error_message
        )

        # Remove from processing
        del self.processing[request_id]

        # Mark queue task as done
        self.queue.task_done()

        # Publish event
        if success and image_path and generation_time:
            is_video = False
            generation_type = "standard"

            if isinstance(item.request_item, ReduxRequestItem):
                generation_type = "redux"
            elif isinstance(item.request_item, ReduxPromptRequestItem):
                generation_type = "reduxprompt"
            elif hasattr(item.request_item, 'is_pulid') and item.request_item.is_pulid:
                generation_type = "pulid"

            self.event_bus.publish(ImageGenerationCompletedEvent(
                request_id=request_id,
                user_id=item.user_id,
                image_path=image_path,
                generation_time=generation_time,
                is_video=is_video,
                generation_type=generation_type
            ))
        elif not success:
            is_video = False
            generation_type = "standard"

            if isinstance(item.request_item, ReduxRequestItem):
                generation_type = "redux"
            elif isinstance(item.request_item, ReduxPromptRequestItem):
                generation_type = "reduxprompt"
            elif hasattr(item.request_item, 'is_pulid') and item.request_item.is_pulid:
                generation_type = "pulid"

            self.event_bus.publish(ImageGenerationFailedEvent(
                request_id=request_id,
                user_id=item.user_id,
                error_message=error_message or "Unknown error",
                is_video=is_video,
                generation_type=generation_type
            ))

    async def cancel_request(self, request_id: str) -> bool:
        """
        Cancel a request.

        Args:
            request_id: ID of the request to cancel

        Returns:
            True if successful, False otherwise
        """
        # Check if the request is in the processing queue
        if request_id in self.processing:
            item = self.processing[request_id]
            item.status = QueueStatus.CANCELLED

            # Update in repository
            await self.repository.update_item_status(
                request_id,
                QueueStatus.CANCELLED.value
            )

            # Remove from processing
            del self.processing[request_id]

            # Mark queue task as done
            self.queue.task_done()

            return True

        # If not in processing, we need to find it in the queue
        # This is more complex since we can't easily remove from a PriorityQueue
        # We'll mark it as cancelled and skip it when we get to it
        await self.repository.update_item_status(
            request_id,
            QueueStatus.CANCELLED.value
        )

        return True

    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get the current queue status.

        Returns:
            Queue status information
        """
        return {
            "queue_size": self.queue.qsize(),
            "processing": len(self.processing),
            "max_concurrent": self.max_concurrent
        }

    async def get_user_queue_items(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all queue items for a specific user.

        Args:
            user_id: User ID

        Returns:
            List of queue items
        """
        # This would need to be implemented in the repository
        # For now, we'll return an empty list
        return []

    async def get_queue_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get queue statistics.

        Args:
            days: Number of days to get statistics for

        Returns:
            Queue statistics
        """
        return await self.repository.get_queue_stats(days)

    async def start_processing(self, process_func: Callable[[QueueItem], Awaitable[bool]]):
        """
        Start processing the queue.

        Args:
            process_func: Async function that takes a QueueItem and processes it
        """
        # Start the queue processor in a background task
        asyncio.create_task(self.process_queue(process_func))

    async def process_queue(self, process_func: Callable[[QueueItem], Awaitable[bool]]):
        """
        Process the queue continuously.

        Args:
            process_func: Async function that takes a QueueItem and processes it
        """
        while True:
            try:
                async with self.semaphore:
                    item = await self.get_next_request()

                    if not item:
                        # No items in queue, wait a bit
                        await asyncio.sleep(1)
                        continue

                    if item.status == QueueStatus.CANCELLED:
                        # Skip cancelled items
                        self.queue.task_done()
                        continue

                    # Process the item
                    try:
                        success = await process_func(item)
                        await self.complete_request(item.request_id, success)
                    except Exception as e:
                        logger.error(f"Error processing queue item: {e}")
                        await self.complete_request(item.request_id, False, str(e))

            except Exception as e:
                logger.error(f"Error in queue processing loop: {e}")
                await asyncio.sleep(5)  # Wait a bit before retrying
