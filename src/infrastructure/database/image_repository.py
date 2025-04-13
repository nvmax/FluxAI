"""
Repository for image generation data access.
"""

import json
import logging
import time
import sqlite3
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime

from src.domain.models.queue_item import RequestItem, QueueItem
from src.infrastructure.database.database_service import DatabaseService

logger = logging.getLogger(__name__)

class ImageRepository:
    """
    Repository for image generation data.
    Handles persistence of image generation data in a SQLite database.
    """

    def __init__(self, database_service: DatabaseService):
        """
        Initialize the image repository.

        Args:
            database_service: Database service for database access
        """
        self.database_service = database_service
        self._init_db()

    def _init_db(self):
        """Initialize the database schema"""
        try:
            # Create image generations table
            self.database_service.create_table(
                "image_generations",
                {
                    "request_id": "TEXT PRIMARY KEY",
                    "user_id": "TEXT NOT NULL",
                    "channel_id": "TEXT NOT NULL",
                    "guild_id": "TEXT",
                    "original_message_id": "TEXT",
                    "prompt": "TEXT NOT NULL",
                    "resolution": "TEXT NOT NULL",
                    "loras": "TEXT",  # JSON array of lora objects
                    "upscale_factor": "INTEGER DEFAULT 1",
                    "seed": "INTEGER",
                    "is_video": "INTEGER DEFAULT 0",
                    "is_pulid": "INTEGER DEFAULT 0",
                    "generation_type": "TEXT DEFAULT 'standard'",
                    "image_path": "TEXT",
                    "created_at": "REAL NOT NULL",
                    "completed_at": "REAL",
                    "generation_time": "REAL",
                    "workflow_filename": "TEXT"
                }
            )

            logger.info("Image generations database initialized")
        except Exception as e:
            logger.error(f"Error initializing image generations database: {e}")
            raise

    async def save_image_generation(self,
                                   request_id: str,
                                   request_item: RequestItem,
                                   image_path: Optional[str] = None,
                                   generation_time: Optional[float] = None,
                                   completed: bool = False) -> bool:
        """
        Save image generation data.

        Args:
            request_id: Request ID
            request_item: Request item
            image_path: Path to the generated image
            generation_time: Time taken to generate the image
            completed: Whether the generation is completed

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert loras to JSON string
            loras_json = json.dumps(request_item.loras) if hasattr(request_item, 'loras') else '[]'

            # Determine generation type
            generation_type = 'standard'
            if hasattr(request_item, 'is_pulid') and request_item.is_pulid:
                generation_type = 'pulid'

            # Determine if it's a video
            is_video = 0
            if generation_type == 'video':
                is_video = 1

            # Get guild_id if available
            guild_id = None
            if hasattr(request_item, 'guild_id'):
                guild_id = request_item.guild_id

            # Check if record already exists
            existing = self.database_service.fetch_one(
                "SELECT request_id FROM image_generations WHERE request_id = ?",
                (request_id,)
            )

            current_time = time.time()

            if existing:
                # Update existing record
                query = """
                UPDATE image_generations
                SET image_path = ?,
                    completed_at = ?,
                    generation_time = ?
                WHERE request_id = ?
                """
                params = (
                    image_path,
                    current_time if completed else None,
                    generation_time,
                    request_id
                )
                self.database_service.execute(query, params)
            else:
                # Insert new record
                query = """
                INSERT INTO image_generations (
                    request_id, user_id, channel_id, guild_id, original_message_id,
                    prompt, resolution, loras, upscale_factor, seed,
                    is_video, is_pulid, generation_type, image_path,
                    created_at, completed_at, generation_time, workflow_filename
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    request_id,
                    request_item.user_id,
                    request_item.channel_id,
                    guild_id,
                    request_item.original_message_id,
                    request_item.prompt,
                    request_item.resolution,
                    loras_json,
                    request_item.upscale_factor if hasattr(request_item, 'upscale_factor') else 1,
                    request_item.seed if hasattr(request_item, 'seed') else None,
                    is_video,
                    1 if hasattr(request_item, 'is_pulid') and request_item.is_pulid else 0,
                    generation_type,
                    image_path,
                    current_time,
                    current_time if completed else None,
                    generation_time,
                    request_item.workflow_filename if hasattr(request_item, 'workflow_filename') else None
                )
                self.database_service.execute(query, params)

            return True
        except Exception as e:
            logger.error(f"Error saving image generation: {e}")
            return False

    async def get_image_generation(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get image generation data by request ID.

        Args:
            request_id: Request ID

        Returns:
            Image generation data or None if not found
        """
        try:
            query = "SELECT * FROM image_generations WHERE request_id = ?"
            result = self.database_service.fetch_one(query, (request_id,))

            if not result:
                return None

            # Convert row to dictionary
            columns = [
                'request_id', 'user_id', 'channel_id', 'guild_id', 'original_message_id',
                'prompt', 'resolution', 'loras', 'upscale_factor', 'seed',
                'is_video', 'is_pulid', 'generation_type', 'image_path',
                'created_at', 'completed_at', 'generation_time', 'workflow_filename'
            ]
            data = {columns[i]: result[i] for i in range(len(columns))}

            # Parse JSON fields
            if data['loras']:
                data['loras'] = json.loads(data['loras'])

            return data
        except Exception as e:
            logger.error(f"Error getting image generation: {e}")
            return None

    async def get_generation_by_message_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get image generation data by Discord message ID.

        Args:
            message_id: Discord message ID

        Returns:
            Image generation data or None if not found
        """
        try:
            query = "SELECT * FROM image_generations WHERE original_message_id = ?"
            result = self.database_service.fetch_one(query, (message_id,))

            if not result:
                return None

            # Convert row to dictionary
            columns = [
                'request_id', 'user_id', 'channel_id', 'guild_id', 'original_message_id',
                'prompt', 'resolution', 'loras', 'upscale_factor', 'seed',
                'is_video', 'is_pulid', 'generation_type', 'image_path',
                'created_at', 'completed_at', 'generation_time', 'workflow_filename'
            ]
            data = {columns[i]: result[i] for i in range(len(columns))}

            # Parse JSON fields
            if data['loras']:
                data['loras'] = json.loads(data['loras'])

            return data
        except Exception as e:
            logger.error(f"Error getting image generation by message ID: {e}")
            return None

    async def get_user_generations(self, user_id: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get image generations by user ID.

        Args:
            user_id: User ID
            limit: Maximum number of records to return
            offset: Offset for pagination

        Returns:
            List of image generation data
        """
        try:
            query = """
            SELECT * FROM image_generations
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """
            results = self.database_service.fetch_all(query, (user_id, limit, offset))

            if not results:
                return []

            # Convert rows to dictionaries
            columns = [
                'request_id', 'user_id', 'channel_id', 'guild_id', 'original_message_id',
                'prompt', 'resolution', 'loras', 'upscale_factor', 'seed',
                'is_video', 'is_pulid', 'generation_type', 'image_path',
                'created_at', 'completed_at', 'generation_time', 'workflow_filename'
            ]
            data = []
            for row in results:
                item = {columns[i]: row[i] for i in range(len(columns))}

                # Parse JSON fields
                if item['loras']:
                    item['loras'] = json.loads(item['loras'])

                data.append(item)

            return data
        except Exception as e:
            logger.error(f"Error getting user generations: {e}")
            return []

    async def get_recent_generations(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get recent image generations.

        Args:
            limit: Maximum number of records to return
            offset: Offset for pagination

        Returns:
            List of image generation data
        """
        try:
            query = """
            SELECT * FROM image_generations
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """
            results = self.database_service.fetch_all(query, (limit, offset))

            if not results:
                return []

            # Convert rows to dictionaries
            columns = [
                'request_id', 'user_id', 'channel_id', 'guild_id', 'original_message_id',
                'prompt', 'resolution', 'loras', 'upscale_factor', 'seed',
                'is_video', 'is_pulid', 'generation_type', 'image_path',
                'created_at', 'completed_at', 'generation_time', 'workflow_filename'
            ]
            data = []
            for row in results:
                item = {columns[i]: row[i] for i in range(len(columns))}

                # Parse JSON fields
                if item['loras']:
                    item['loras'] = json.loads(item['loras'])

                data.append(item)

            return data
        except Exception as e:
            logger.error(f"Error getting recent generations: {e}")
            return []

    async def create_request_item_from_data(self, data: Dict[str, Any]) -> RequestItem:
        """
        Create a RequestItem from image generation data.

        Args:
            data: Image generation data

        Returns:
            RequestItem object
        """
        try:
            request_item = RequestItem(
                id=data['request_id'],
                user_id=data['user_id'],
                channel_id=data['channel_id'],
                interaction_id=None,  # Not stored in the database
                original_message_id=data['original_message_id'],
                prompt=data['prompt'],
                resolution=data['resolution'],
                loras=data['loras'],
                upscale_factor=data['upscale_factor'],
                workflow_filename=data['workflow_filename'],
                seed=data['seed'],
                is_pulid=bool(data['is_pulid'])
            )
            return request_item
        except Exception as e:
            logger.error(f"Error creating RequestItem from data: {e}")
            raise

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get image generation statistics.

        Returns:
            Dictionary of statistics
        """
        try:
            stats = {}

            # Total generations
            query = "SELECT COUNT(*) FROM image_generations"
            result = self.database_service.fetch_one(query)
            stats['total_generations'] = result[0] if result else 0

            # Total completed generations
            query = "SELECT COUNT(*) FROM image_generations WHERE completed_at IS NOT NULL"
            result = self.database_service.fetch_one(query)
            stats['completed_generations'] = result[0] if result else 0

            # Total unique users
            query = "SELECT COUNT(DISTINCT user_id) FROM image_generations"
            result = self.database_service.fetch_one(query)
            stats['unique_users'] = result[0] if result else 0

            # Average generation time
            query = "SELECT AVG(generation_time) FROM image_generations WHERE generation_time IS NOT NULL"
            result = self.database_service.fetch_one(query)
            stats['avg_generation_time'] = result[0] if result and result[0] is not None else 0

            # Average generation time for images
            query = """
            SELECT AVG(generation_time) FROM image_generations
            WHERE generation_time IS NOT NULL AND is_video = 0
            """
            result = self.database_service.fetch_one(query)
            stats['avg_image_generation_time'] = result[0] if result and result[0] is not None else 0

            # Average generation time for videos
            query = """
            SELECT AVG(generation_time) FROM image_generations
            WHERE generation_time IS NOT NULL AND is_video = 1
            """
            result = self.database_service.fetch_one(query)
            stats['avg_video_generation_time'] = result[0] if result and result[0] is not None else 0

            # Popular resolutions
            query = """
            SELECT resolution, COUNT(*) as count
            FROM image_generations
            GROUP BY resolution
            ORDER BY count DESC
            LIMIT 5
            """
            results = self.database_service.fetch_all(query)
            stats['popular_resolutions'] = [{'resolution': row[0], 'count': row[1]} for row in results] if results else []

            # Popular loras
            query = """
            SELECT loras FROM image_generations
            WHERE loras IS NOT NULL AND loras != '[]'
            """
            results = self.database_service.fetch_all(query)

            lora_counts = {}
            for row in results:
                if row[0]:
                    try:
                        loras = json.loads(row[0])
                        for lora in loras:
                            lora_name = lora.get('name', 'Unknown')
                            if lora_name in lora_counts:
                                lora_counts[lora_name] += 1
                            else:
                                lora_counts[lora_name] = 1
                    except:
                        pass

            # Sort loras by count
            popular_loras = [{'name': name, 'count': count} for name, count in lora_counts.items()]
            popular_loras.sort(key=lambda x: x['count'], reverse=True)
            stats['popular_loras'] = popular_loras[:5]

            # Generation types
            query = """
            SELECT generation_type, COUNT(*) as count
            FROM image_generations
            GROUP BY generation_type
            ORDER BY count DESC
            """
            results = self.database_service.fetch_all(query)
            stats['generation_types'] = [{'type': row[0], 'count': row[1]} for row in results] if results else []

            return stats
        except Exception as e:
            logger.error(f"Error getting image generation stats: {e}")
            return {}
