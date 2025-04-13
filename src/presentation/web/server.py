"""
Web server for handling ComfyUI callbacks.
"""

import logging
import json
from typing import Dict, Any, Optional

from aiohttp import web
import discord

from src.infrastructure.config.config_manager import ConfigManager
from src.domain.events.event_bus import EventBus
from src.domain.events.common_events import ImageGenerationCompletedEvent
from src.presentation.discord.views.image_view import ImageControlView

logger = logging.getLogger(__name__)

class WebServer:
    """
    Web server for handling ComfyUI callbacks.
    Provides endpoints for receiving generated images and progress updates.
    """

    def __init__(self, bot):
        """
        Initialize the web server.

        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.config = ConfigManager()
        self.event_bus = EventBus()
        self.app = web.Application()
        self.setup_routes()

    def setup_routes(self):
        """Set up the web server routes"""
        self.app.router.add_post('/send_image', self.handle_generated_image)
        self.app.router.add_post('/update_progress', self.update_progress)
        self.app.router.add_post('/image_generated', self.handle_generated_image)

        # Store bot reference in app
        self.app['bot'] = self.bot

    async def start(self, host: str = "0.0.0.0", port: int = 8080):
        """
        Start the web server.

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host=host, port=port)
        await site.start()
        logger.info(f"Web server started on {host}:{port}")
        return self.app

    async def handle_generated_image(self, request: web.Request) -> web.Response:
        """
        Handle a generated image callback from ComfyUI.

        Args:
            request: Web request

        Returns:
            Web response
        """
        try:
            # Parse request data
            data = await request.json()

            request_id = data.get('request_id')
            user_id = data.get('user_id')
            channel_id = data.get('channel_id')
            image_path = data.get('image_path')
            generation_time = data.get('generation_time', 0)

            if not all([request_id, user_id, channel_id, image_path]):
                return web.Response(text="Missing required fields", status=400)

            # Get the channel
            try:
                channel = await self.bot.fetch_channel(int(channel_id))
            except (discord.NotFound, discord.HTTPException) as e:
                logger.error(f"Could not fetch channel {channel_id}: {str(e)}")
                return web.Response(text="Channel not found", status=404)

            # Create embed
            embed = discord.Embed(
                title="Generated Image",
                description=f"Generated in {generation_time:.2f} seconds",
                color=discord.Color.blue()
            )

            embed.set_image(url=f"attachment://{image_path.split('/')[-1]}")
            embed.set_footer(text=f"Requested by {user_id}")

            # Create file
            try:
                file = discord.File(image_path, filename=image_path.split('/')[-1])
            except Exception as e:
                logger.error(f"Could not create file from {image_path}: {str(e)}")
                return web.Response(text="Could not create file", status=500)

            # Create view
            view = ImageControlView(self.bot)

            # Get the original progress message and update it
            try:
                original_message_id = data.get('original_message_id')
                if original_message_id:
                    progress_message = await channel.fetch_message(int(original_message_id))
                    await progress_message.edit(content=None, embed=embed, attachments=[], view=view)
                    await progress_message.add_files(file)
                else:
                    # Send as new message
                    await channel.send(file=file, embed=embed, view=view)
            except (discord.NotFound, discord.HTTPException) as e:
                # If we can't find the original message or there's an error editing, send as new message
                logger.error(f"Could not edit original message, sending new one: {str(e)}")
                await channel.send(file=file, embed=embed, view=view)

            # Publish event with detailed logging
            logger.info(f"ANALYTICS: Publishing ImageGenerationCompletedEvent - request_id: {request_id}, user_id: {user_id}, generation_time: {generation_time:.2f}s")

            event = ImageGenerationCompletedEvent(
                request_id=request_id,
                user_id=user_id,
                image_path=image_path,
                generation_time=generation_time,
                is_video=False,
                generation_type=data.get('generation_type', 'standard')
            )

            self.event_bus.publish(event)

            logger.info(f"ANALYTICS: Event published successfully")

            # Directly update the analytics database
            try:
                logger.info(f"ANALYTICS: Directly updating analytics database for user {user_id}")
                import sqlite3
                import os
                import json
                import time

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
                        return web.Response(text="Success")

                # Connect to the database
                conn = sqlite3.connect(analytics_db_path)
                c = conn.cursor()

                # Check if the table exists
                c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='image_stats'")
                if not c.fetchone():
                    logger.error(f"ANALYTICS: image_stats table does not exist in {analytics_db_path}")
                    return web.Response(text="Success")

                # Get the current timestamp
                current_time = time.time()

                # Insert the image generation record
                c.execute(
                    "INSERT INTO image_stats (user_id, prompt, resolution, loras, upscale_factor, generation_time, is_video, generation_type, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (user_id, "", "", json.dumps([]), 1, generation_time, 0, data.get('generation_type', 'standard'), current_time)
                )

                # Verify the data was inserted correctly
                c.execute("SELECT generation_time FROM image_stats WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (user_id,))
                result = c.fetchone()
                if result:
                    logger.info(f"ANALYTICS: Verified generation time in database: {result[0]:.2f} seconds")
                else:
                    logger.error(f"ANALYTICS: Failed to verify insertion - no record found")

                # Commit changes and close connection
                conn.commit()
                conn.close()

                logger.info(f"ANALYTICS: Successfully recorded image generation for user {user_id}")

                # Verify the record was inserted by querying the database again
                conn = sqlite3.connect(analytics_db_path)
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM image_stats WHERE timestamp > ?", (current_time - 10,))
                count = c.fetchone()[0]
                logger.info(f"ANALYTICS: Found {count} records inserted in the last 10 seconds")
                conn.close()

            except Exception as e:
                logger.error(f"ANALYTICS: Error directly updating analytics database: {e}", exc_info=True)

            return web.Response(text="Success")

        except Exception as e:
            logger.error(f"Error in handle_generated_image: {str(e)}", exc_info=True)
            return web.Response(status=500, text=f"Internal server error: {str(e)}")

    async def update_progress(self, request: web.Request) -> web.Response:
        """
        Update progress for a generation request.

        Args:
            request: Web request

        Returns:
            Web response
        """
        try:
            # Parse request data
            data = await request.json()

            request_id = data.get('request_id')
            progress_data = data.get('progress_data', {})

            if not request_id:
                return web.Response(text="Missing request_id", status=400)

            # Get the request item from the bot's pending requests
            # This is a legacy approach and should be updated to use the queue system
            if not hasattr(self.bot, 'pending_requests') or request_id not in self.bot.pending_requests:
                return web.Response(text="Unknown request_id", status=404)

            request_item = self.bot.pending_requests[request_id]

            try:
                # Get the channel and message
                channel = await self.bot.fetch_channel(int(request_item.channel_id))
                message = await channel.fetch_message(int(request_item.original_message_id))

                # Update the message with progress
                status = progress_data.get('status', '')
                progress_message = progress_data.get('message', 'Processing...')
                progress = progress_data.get('progress', 0)

                # Define status messages
                status_messages = {
                    'loading_models': {
                        'message': 'Loading models and preparing generation...',
                        'emoji': '⚙️'
                    },
                    'generating': {
                        'message': 'Generating image...',
                        'emoji': '🎨'
                    },
                    'upscaling': {
                        'message': 'Upscaling image...',
                        'emoji': '🔍'
                    },
                    'saving': {
                        'message': 'Saving image...',
                        'emoji': '💾'
                    },
                    'error': {
                        'message': 'Error:',
                        'emoji': '❌'
                    },
                    'complete': {
                        'message': 'Generation complete!',
                        'emoji': '✅'
                    }
                }

                status_info = status_messages.get(status, {
                    'message': progress_message,
                    'emoji': '⚙️'
                })

                if status == 'generating' and progress == 100:
                    status = 'upscaling'
                    status_info = status_messages['upscaling']
                    formatted_message = f"{status_info['emoji']} {status_info['message']}"
                elif status == 'generating':
                    formatted_message = f"{status_info['emoji']} {status_info['message']} {progress}%"
                elif status == 'error':
                    formatted_message = f"{status_info['emoji']} {status_info['message']} {progress_message}"
                    # Only remove on error
                    if request_id in self.bot.pending_requests:
                        del self.bot.pending_requests[request_id]
                else:
                    formatted_message = f"{status_info['emoji']} {status_info['message']}"

                await message.edit(content=formatted_message)
                logger.debug(f"Updated progress message: {formatted_message}")

                return web.Response(text="Progress updated")

            except discord.errors.NotFound:
                logger.warning(f"Message {request_item.original_message_id} not found")
                return web.Response(text="Message not found", status=404)
            except discord.errors.Forbidden:
                logger.warning("Bot lacks permission to edit message")
                return web.Response(text="Permission denied", status=403)
            except Exception as e:
                logger.error(f"Error updating progress message: {str(e)}")
                return web.Response(text=f"Error: {str(e)}", status=500)

        except Exception as e:
            logger.error(f"Error in update_progress: {str(e)}")
            return web.Response(text="Internal server error", status=500)
