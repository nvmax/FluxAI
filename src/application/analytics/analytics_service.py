"""
Service for tracking and analyzing application usage.
"""

import logging
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from src.domain.interfaces.analytics_repository import AnalyticsRepository
from src.domain.events.event_bus import EventBus
from src.domain.events.common_events import (
    CommandExecutedEvent,
    UserActivityEvent,
    ImageGenerationCompletedEvent,
    ContentFilterViolationEvent
)

logger = logging.getLogger(__name__)

class AnalyticsService:
    """
    Service for tracking and analyzing application usage.
    Handles recording and retrieving analytics data.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one analytics service exists"""
        if cls._instance is None:
            cls._instance = super(AnalyticsService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, repository: AnalyticsRepository):
        """
        Initialize the analytics service.

        Args:
            repository: Repository for analytics data access
        """
        # Only initialize once (singleton pattern)
        if self._initialized:
            return

        self.repository = repository
        self.event_bus = EventBus()
        self._initialized = True

        # Register event handlers
        self._register_event_handlers()

    def _register_event_handlers(self):
        """Register event handlers for analytics events"""
        logger.info("ANALYTICS: Registering event handlers for analytics events")

        # Register command executed event handler
        self.event_bus.subscribe(CommandExecutedEvent, self._handle_command_executed)
        logger.info("ANALYTICS: Registered CommandExecutedEvent handler")

        # Register user activity event handler
        self.event_bus.subscribe(UserActivityEvent, self._handle_user_activity)
        logger.info("ANALYTICS: Registered UserActivityEvent handler")

        # Register image generation completed event handler
        self.event_bus.subscribe(ImageGenerationCompletedEvent, self._handle_image_generation_completed)
        logger.info("ANALYTICS: Registered ImageGenerationCompletedEvent handler")

        # Register content filter violation event handler
        self.event_bus.subscribe(ContentFilterViolationEvent, self._handle_content_filter_violation)
        logger.info("ANALYTICS: Registered ContentFilterViolationEvent handler")

        logger.info("ANALYTICS: All event handlers registered successfully")

    async def _handle_command_executed(self, event: CommandExecutedEvent):
        """
        Handle command executed event.

        Args:
            event: Command executed event
        """
        await self.record_command_usage(
            command_name=event.command_name,
            user_id=event.user_id,
            guild_id=event.guild_id,
            channel_id=event.channel_id,
            execution_time=event.execution_time,
            success=event.success
        )

    async def _handle_user_activity(self, event: UserActivityEvent):
        """
        Handle user activity event.

        Args:
            event: User activity event
        """
        await self.record_user_activity(
            user_id=event.user_id,
            action_type=event.action_type,
            guild_id=event.guild_id,
            details=event.details
        )

    async def _handle_image_generation_completed(self, event: ImageGenerationCompletedEvent):
        """
        Handle image generation completed event.

        Args:
            event: Image generation completed event
        """
        try:
            # Log the event with more details
            logger.info(f"ANALYTICS: Handling image generation completed event: {event.request_id}, user: {event.user_id}, time: {event.generation_time:.2f}s, is_video: {event.is_video}, type: {event.generation_type}")
            logger.info(f"ANALYTICS: Current working directory: {os.getcwd()}")

            # Connect directly to the analytics.db database
            import sqlite3
            import os
            import json

            # Get the path to the analytics.db file
            analytics_db_path = os.path.join(os.getcwd(), 'analytics.db')
            logger.info(f"ANALYTICS: Database path: {analytics_db_path}")

            # Check if the file exists
            if not os.path.exists(analytics_db_path):
                logger.error(f"ANALYTICS: Analytics database not found at {analytics_db_path}")

                # Try to find the database file
                for root, dirs, files in os.walk(os.getcwd()):
                    if 'analytics.db' in files:
                        analytics_db_path = os.path.join(root, 'analytics.db')
                        logger.info(f"ANALYTICS: Found database at {analytics_db_path}")
                        break
                else:
                    logger.error(f"ANALYTICS: Could not find analytics.db anywhere in the project")
                    return

            # Connect to the database
            conn = sqlite3.connect(analytics_db_path)
            c = conn.cursor()

            # Check if the table exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='image_stats'")
            if not c.fetchone():
                logger.error(f"ANALYTICS: image_stats table does not exist in {analytics_db_path}")
                return

            # Get the current timestamp
            current_time = time.time()

            # Insert the image generation record
            c.execute(
                "INSERT INTO image_stats (user_id, prompt, resolution, loras, upscale_factor, generation_time, is_video, generation_type, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (event.user_id, "", "", json.dumps([]), 1, event.generation_time, 1 if event.is_video else 0, event.generation_type, current_time)
            )

            # Verify the data was inserted correctly
            c.execute("SELECT generation_time FROM image_stats WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (event.user_id,))
            result = c.fetchone()
            if result:
                logger.info(f"ANALYTICS: Verified generation time in database: {result[0]:.2f} seconds")
            else:
                logger.error(f"ANALYTICS: Failed to verify insertion - no record found")

            # Commit changes and close connection
            conn.commit()
            conn.close()

            logger.info(f"ANALYTICS: Successfully recorded image generation for user {event.user_id}")

            # Verify the record was inserted by querying the database again
            conn = sqlite3.connect(analytics_db_path)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM image_stats WHERE timestamp > ?", (current_time - 10,))
            count = c.fetchone()[0]
            logger.info(f"ANALYTICS: Found {count} records inserted in the last 10 seconds")
            conn.close()

        except Exception as e:
            logger.error(f"ANALYTICS: Error handling image generation completed event: {e}", exc_info=True)
            # Try to use the repository method as a fallback
            try:
                logger.info(f"ANALYTICS: Trying fallback method to record image generation")
                await self.record_image_generation(
                    user_id=event.user_id,
                    prompt="",
                    resolution="",
                    loras=[],
                    upscale_factor=1,
                    generation_time=event.generation_time,
                    is_video=event.is_video,
                    generation_type=event.generation_type
                )
                logger.info(f"ANALYTICS: Fallback method succeeded")
            except Exception as e2:
                logger.error(f"ANALYTICS: Fallback recording also failed: {e2}", exc_info=True)

                # Last resort: try to directly execute SQL
                try:
                    logger.info(f"ANALYTICS: Trying last resort direct SQL execution")
                    import sqlite3
                    import os
                    import json

                    # Get the path to the analytics.db file
                    analytics_db_path = os.path.join(os.getcwd(), 'analytics.db')

                    # Connect to the database
                    conn = sqlite3.connect(analytics_db_path)
                    c = conn.cursor()

                    # Insert the image generation record
                    c.execute(
                        "INSERT INTO image_stats (user_id, prompt, resolution, loras, upscale_factor, generation_time, is_video, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (event.user_id, "", "", json.dumps([]), 1, event.generation_time, 1 if event.is_video else 0, time.time())
                    )

                    # Commit changes and close connection
                    conn.commit()
                    conn.close()

                    logger.info(f"ANALYTICS: Last resort method succeeded")
                except Exception as e3:
                    logger.error(f"ANALYTICS: Last resort method also failed: {e3}", exc_info=True)

    async def _handle_content_filter_violation(self, event: ContentFilterViolationEvent):
        """
        Handle content filter violation event.

        Args:
            event: Content filter violation event
        """
        # Record as user activity
        await self.record_user_activity(
            user_id=event.user_id,
            action_type="content_filter_violation",
            details={
                "prompt": event.prompt,
                "violation_type": event.violation_type,
                "violation_details": event.violation_details
            }
        )

    async def record_command_usage(self,
                                  command_name: str,
                                  user_id: str,
                                  guild_id: Optional[str] = None,
                                  channel_id: Optional[str] = None,
                                  execution_time: Optional[float] = None,
                                  success: bool = True):
        """
        Record command usage.

        Args:
            command_name: Name of the command
            user_id: ID of the user who executed the command
            guild_id: ID of the guild where the command was executed
            channel_id: ID of the channel where the command was executed
            execution_time: Time taken to execute the command
            success: Whether the command was successful
        """
        try:
            await self.repository.record_command_usage(
                command_name=command_name,
                user_id=user_id,
                guild_id=guild_id,
                channel_id=channel_id,
                execution_time=execution_time,
                success=success
            )
        except Exception as e:
            logger.error(f"Error recording command usage: {e}")

    async def record_user_activity(self,
                                  user_id: str,
                                  action_type: str,
                                  guild_id: Optional[str] = None,
                                  details: Optional[Dict[str, Any]] = None):
        """
        Record user activity.

        Args:
            user_id: ID of the user
            action_type: Type of action
            guild_id: ID of the guild where the action occurred
            details: Additional details about the action
        """
        try:
            await self.repository.record_user_activity(
                user_id=user_id,
                action_type=action_type,
                guild_id=guild_id,
                details=details
            )
        except Exception as e:
            logger.error(f"Error recording user activity: {e}")

    async def record_image_generation(self,
                                     user_id: str,
                                     prompt: str,
                                     resolution: str,
                                     loras: List[Dict[str, Any]],
                                     upscale_factor: int,
                                     generation_time: float,
                                     is_video: bool = False,
                                     generation_type: str = "standard"):
        """
        Record image generation.

        Args:
            user_id: ID of the user
            prompt: Prompt used for generation
            resolution: Resolution of the generated image
            loras: LoRAs used for generation
            upscale_factor: Upscale factor
            generation_time: Time taken to generate the image
            is_video: Whether the generation is a video
            generation_type: Type of generation (standard, redux, etc.)
        """
        try:
            # Convert loras to JSON string
            loras_json = json.dumps(loras)

            await self.repository.record_image_generation(
                user_id=user_id,
                prompt=prompt,
                resolution=resolution,
                loras=loras_json,
                upscale_factor=upscale_factor,
                generation_time=generation_time,
                is_video=is_video,
                generation_type=generation_type
            )
        except Exception as e:
            logger.error(f"Error recording image generation: {e}")

    async def get_command_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get command usage statistics.

        Args:
            days: Number of days to get statistics for

        Returns:
            Command usage statistics
        """
        try:
            return await self.repository.get_command_stats(days)
        except Exception as e:
            logger.error(f"Error getting command stats: {e}")
            return {}

    async def get_user_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get user activity statistics.

        Args:
            days: Number of days to get statistics for

        Returns:
            User activity statistics
        """
        try:
            return await self.repository.get_user_stats(days)
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}

    async def get_image_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get image generation statistics.

        Args:
            days: Number of days to get statistics for

        Returns:
            Image generation statistics
        """
        try:
            return await self.repository.get_image_stats(days)
        except Exception as e:
            logger.error(f"Error getting image stats: {e}")
            return {}

    async def get_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get daily statistics.

        Args:
            days: Number of days to get statistics for

        Returns:
            Daily statistics
        """
        try:
            return await self.repository.get_daily_stats(days)
        except Exception as e:
            logger.error(f"Error getting daily stats: {e}")
            return []

    async def get_all_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get all statistics.

        Args:
            days: Number of days to get statistics for

        Returns:
            All statistics
        """
        command_stats = await self.get_command_stats(days)
        user_stats = await self.get_user_stats(days)
        image_stats = await self.get_image_stats(days)
        daily_stats = await self.get_daily_stats(days)

        return {
            "command_stats": command_stats,
            "user_stats": user_stats,
            "image_stats": image_stats,
            "daily_stats": daily_stats,
            "days": days
        }

    async def reset_analytics(self) -> bool:
        """
        Reset all analytics data.

        Returns:
            True if successful, False otherwise
        """
        try:
            return await self.repository.reset_analytics()
        except Exception as e:
            logger.error(f"Error resetting analytics: {e}")
            return False
