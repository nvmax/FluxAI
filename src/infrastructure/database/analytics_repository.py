"""
Repository for analytics data access.
"""

import json
import logging
import time
import sqlite3
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

from src.domain.interfaces.analytics_repository import AnalyticsRepository
from src.infrastructure.database.database_service import DatabaseService

logger = logging.getLogger(__name__)

class SQLiteAnalyticsRepository(AnalyticsRepository):
    """
    SQLite implementation of the analytics repository.
    Handles persistence of analytics data in a SQLite database.
    """

    def __init__(self, database_service: DatabaseService, db_path: str = "analytics.db"):
        """
        Initialize the analytics repository.

        Args:
            database_service: Database service for database access
            db_path: Path to the database file
        """
        self.database_service = database_service
        self.db_path = db_path

        # Create a new database service instance specifically for analytics
        self.analytics_db_service = DatabaseService(db_path=db_path)

        # Ensure the database file exists
        if not os.path.exists(db_path):
            logger.info(f"ANALYTICS: Creating new analytics database at {db_path}")
            # Create an empty connection to create the file
            conn = sqlite3.connect(db_path)
            conn.close()

        self._init_db()

    def _init_db(self):
        """Initialize the database schema"""
        try:
            # Create command usage table
            self.analytics_db_service.create_table(
                "command_usage",
                {
                    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                    "command_name": "TEXT NOT NULL",
                    "user_id": "TEXT NOT NULL",
                    "guild_id": "TEXT",
                    "channel_id": "TEXT",
                    "timestamp": "REAL NOT NULL",
                    "execution_time": "REAL",
                    "success": "INTEGER NOT NULL"
                }
            )

            # Create user activity table
            self.analytics_db_service.create_table(
                "user_activity",
                {
                    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                    "user_id": "TEXT NOT NULL",
                    "guild_id": "TEXT",
                    "action_type": "TEXT NOT NULL",
                    "timestamp": "REAL NOT NULL",
                    "details": "TEXT"
                }
            )

            # Create image stats table
            self.analytics_db_service.create_table(
                "image_stats",
                {
                    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                    "user_id": "TEXT NOT NULL",
                    "prompt": "TEXT",
                    "resolution": "TEXT",
                    "loras": "TEXT",
                    "upscale_factor": "INTEGER",
                    "generation_time": "REAL",
                    "is_video": "INTEGER DEFAULT 0",
                    "generation_type": "TEXT DEFAULT 'standard'",
                    "timestamp": "REAL NOT NULL"
                }
            )

            # Create daily stats table
            self.analytics_db_service.create_table(
                "daily_stats",
                {
                    "date": "TEXT PRIMARY KEY",
                    "total_commands": "INTEGER NOT NULL",
                    "total_images": "INTEGER NOT NULL",
                    "unique_users": "INTEGER NOT NULL",
                    "avg_generation_time": "REAL",
                    "popular_commands": "TEXT",
                    "popular_resolutions": "TEXT"
                }
            )

            logger.info(f"Analytics database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing analytics database: {e}")
            raise

    async def record_command_usage(self,
                                  command_name: str,
                                  user_id: str,
                                  guild_id: Optional[str] = None,
                                  channel_id: Optional[str] = None,
                                  execution_time: Optional[float] = None,
                                  success: bool = True) -> bool:
        """
        Record command usage.

        Args:
            command_name: Name of the command
            user_id: ID of the user who executed the command
            guild_id: ID of the guild where the command was executed
            channel_id: ID of the channel where the command was executed
            execution_time: Time taken to execute the command
            success: Whether the command was successful

        Returns:
            True if successful, False otherwise
        """
        try:
            # Insert into database
            self.analytics_db_service.insert(
                "command_usage",
                {
                    "command_name": command_name,
                    "user_id": user_id,
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "timestamp": time.time(),
                    "execution_time": execution_time,
                    "success": 1 if success else 0
                }
            )

            logger.debug(f"Recorded command usage: {command_name} by {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error recording command usage: {e}")
            return False

    async def record_user_activity(self,
                                  user_id: str,
                                  action_type: str,
                                  guild_id: Optional[str] = None,
                                  details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Record user activity.

        Args:
            user_id: ID of the user
            action_type: Type of action
            guild_id: ID of the guild where the action occurred
            details: Additional details about the action

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert details to JSON
            details_json = json.dumps(details) if details else None

            # Insert into database
            self.analytics_db_service.insert(
                "user_activity",
                {
                    "user_id": user_id,
                    "guild_id": guild_id,
                    "action_type": action_type,
                    "timestamp": time.time(),
                    "details": details_json
                }
            )

            logger.debug(f"Recorded user activity: {action_type} by {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error recording user activity: {e}")
            return False

    async def record_image_generation(self,
                                     user_id: str,
                                     prompt: str,
                                     resolution: str,
                                     loras: str,
                                     upscale_factor: int,
                                     generation_time: float,
                                     is_video: bool = False,
                                     generation_type: str = "standard") -> bool:
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

        Returns:
            True if successful, False otherwise
        """
        try:
            # Insert into database
            self.analytics_db_service.insert(
                "image_stats",
                {
                    "user_id": user_id,
                    "prompt": prompt,
                    "resolution": resolution,
                    "loras": loras,
                    "upscale_factor": upscale_factor,
                    "generation_time": generation_time,
                    "is_video": 1 if is_video else 0,
                    "generation_type": generation_type,
                    "timestamp": time.time()
                }
            )

            logger.debug(f"Recorded image generation by {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error recording image generation: {e}")
            return False

    async def get_command_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get command usage statistics.

        Args:
            days: Number of days to get statistics for

        Returns:
            Command usage statistics
        """
        try:
            # Calculate cutoff time
            cutoff_time = time.time() - (days * 24 * 60 * 60)

            # Get total commands
            row = self.analytics_db_service.fetch_one(
                "SELECT COUNT(*) FROM command_usage WHERE timestamp > ?",
                (cutoff_time,)
            )
            total_commands = row[0] if row else 0

            # Get successful commands
            row = self.analytics_db_service.fetch_one(
                "SELECT COUNT(*) FROM command_usage WHERE timestamp > ? AND success = 1",
                (cutoff_time,)
            )
            successful_commands = row[0] if row else 0

            # Get average execution time
            row = self.analytics_db_service.fetch_one(
                "SELECT AVG(execution_time) FROM command_usage WHERE timestamp > ? AND execution_time IS NOT NULL",
                (cutoff_time,)
            )
            avg_execution_time = row[0] if row and row[0] is not None else 0

            # Get popular commands
            rows = self.analytics_db_service.fetch_all(
                "SELECT command_name, COUNT(*) as count FROM command_usage WHERE timestamp > ? GROUP BY command_name ORDER BY count DESC LIMIT 10",
                (cutoff_time,)
            )
            popular_commands = [{"name": row[0], "count": row[1]} for row in rows]

            return {
                "total_commands": total_commands,
                "successful_commands": successful_commands,
                "avg_execution_time": avg_execution_time,
                "popular_commands": popular_commands,
                "days": days
            }
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
            # Calculate cutoff time
            cutoff_time = time.time() - (days * 24 * 60 * 60)

            # Get total users
            row = self.analytics_db_service.fetch_one(
                "SELECT COUNT(DISTINCT user_id) FROM user_activity WHERE timestamp > ?",
                (cutoff_time,)
            )
            total_users = row[0] if row else 0

            # Get active users (users with at least 5 activities)
            row = self.analytics_db_service.fetch_one(
                """
                SELECT COUNT(*) FROM (
                    SELECT user_id, COUNT(*) as count
                    FROM user_activity
                    WHERE timestamp > ?
                    GROUP BY user_id
                    HAVING count >= 5
                )
                """,
                (cutoff_time,)
            )
            active_users = row[0] if row else 0

            # Get popular action types
            rows = self.analytics_db_service.fetch_all(
                "SELECT action_type, COUNT(*) as count FROM user_activity WHERE timestamp > ? GROUP BY action_type ORDER BY count DESC LIMIT 10",
                (cutoff_time,)
            )
            popular_actions = [{"name": row[0], "count": row[1]} for row in rows]

            return {
                "total_users": total_users,
                "active_users": active_users,
                "popular_actions": popular_actions,
                "days": days
            }
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
            # Calculate cutoff time
            cutoff_time = time.time() - (days * 24 * 60 * 60)

            # Get total images
            row = self.analytics_db_service.fetch_one(
                "SELECT COUNT(*) FROM image_stats WHERE timestamp > ? AND is_video = 0",
                (cutoff_time,)
            )
            total_images = row[0] if row else 0

            # Get average generation time for images
            row = self.analytics_db_service.fetch_one(
                "SELECT AVG(generation_time) FROM image_stats WHERE timestamp > ? AND is_video = 0 AND generation_time IS NOT NULL",
                (cutoff_time,)
            )
            avg_generation_time = row[0] if row and row[0] is not None else 0

            # Get total videos
            row = self.analytics_db_service.fetch_one(
                "SELECT COUNT(*) FROM image_stats WHERE timestamp > ? AND is_video = 1",
                (cutoff_time,)
            )
            total_videos = row[0] if row else 0

            # Get average generation time for videos
            row = self.analytics_db_service.fetch_one(
                "SELECT AVG(generation_time) FROM image_stats WHERE timestamp > ? AND is_video = 1 AND generation_time IS NOT NULL",
                (cutoff_time,)
            )
            avg_video_time = row[0] if row and row[0] is not None else 0

            # Get popular resolutions
            rows = self.analytics_db_service.fetch_all(
                "SELECT resolution, COUNT(*) as count FROM image_stats WHERE timestamp > ? GROUP BY resolution ORDER BY count DESC LIMIT 10",
                (cutoff_time,)
            )
            popular_resolutions = [{"name": row[0], "count": row[1]} for row in rows]

            # Get popular generation types
            rows = self.analytics_db_service.fetch_all(
                "SELECT generation_type, COUNT(*) as count FROM image_stats WHERE timestamp > ? GROUP BY generation_type ORDER BY count DESC LIMIT 10",
                (cutoff_time,)
            )
            popular_types = [{"name": row[0], "count": row[1]} for row in rows]

            return {
                "total_images": total_images,
                "avg_generation_time": avg_generation_time,
                "total_videos": total_videos,
                "avg_video_time": avg_video_time,
                "popular_resolutions": popular_resolutions,
                "popular_types": popular_types,
                "days": days
            }
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
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_date_str = cutoff_date.strftime("%Y-%m-%d")

            # Get daily stats from database
            rows = self.analytics_db_service.fetch_all(
                "SELECT date, total_commands, total_images, unique_users, avg_generation_time, popular_commands, popular_resolutions FROM daily_stats WHERE date >= ? ORDER BY date DESC",
                (cutoff_date_str,)
            )

            daily_stats = []
            for row in rows:
                try:
                    popular_commands = json.loads(row[5]) if row[5] else []
                    popular_resolutions = json.loads(row[6]) if row[6] else []

                    daily_stats.append({
                        "date": row[0],
                        "total_commands": row[1],
                        "total_images": row[2],
                        "unique_users": row[3],
                        "avg_generation_time": row[4],
                        "popular_commands": popular_commands,
                        "popular_resolutions": popular_resolutions
                    })
                except Exception as e:
                    logger.error(f"Error parsing daily stats: {e}")

            logger.debug(f"Got {len(daily_stats)} daily stats")
            return daily_stats
        except Exception as e:
            logger.error(f"Error getting daily stats: {e}")
            return []

    async def reset_analytics(self) -> bool:
        """
        Reset all analytics data.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Drop and recreate tables
            self.analytics_db_service.drop_table("command_usage")
            self.analytics_db_service.drop_table("user_activity")
            self.analytics_db_service.drop_table("image_stats")
            self.analytics_db_service.drop_table("daily_stats")

            # Reinitialize database
            self._init_db()

            logger.info("Reset analytics data")
            return True
        except Exception as e:
            logger.error(f"Error resetting analytics data: {e}")
            return False
