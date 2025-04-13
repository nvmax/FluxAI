"""
Discord bot implementation.
"""

import discord
import asyncio
import logging
import platform
import os
import time
import random
from typing import Dict, Any, List, Optional, Set

from discord import Interaction, Intents, app_commands
from discord.ext import commands as discord_commands

from src.infrastructure.config.config_manager import ConfigManager
from src.infrastructure.di.container import DIContainer
from src.domain.events.event_bus import EventBus
from src.domain.events.common_events import CommandExecutedEvent
from src.application.queue.queue_service import QueueService
from src.application.analytics.analytics_service import AnalyticsService
from src.application.content_filter.content_filter_service import ContentFilterService
from src.application.image_generation.image_generation_service import ImageGenerationService

logger = logging.getLogger(__name__)

class DiscordBot(discord_commands.Bot):
    """
    Discord bot for image generation.
    Handles Discord interactions and commands.
    """

    def __init__(self, queue_service=None, analytics_service=None, content_filter_service=None, image_generation_service=None):
        """Initialize the Discord bot"""
        # Get configuration
        self.config = ConfigManager()

        # Initialize bot with intents
        intents = Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix=self.config.command_prefix,
            intents=intents
        )

        # Set up error handler
        self.tree.on_error = self.on_tree_error

        # Initialize pending requests dict for progress updates
        self.pending_requests = {}

        # Initialize service properties
        self.queue_service = queue_service
        self.analytics_service = analytics_service
        self.content_filter_service = content_filter_service
        self.image_generation_service = image_generation_service
        self.image_repository = None

        # If services are not provided, try to get them from DI container
        # This is a fallback mechanism and should be avoided in production
        if not all([queue_service, analytics_service, content_filter_service, image_generation_service]):
            logger.warning("Some services not provided to DiscordBot constructor, attempting to resolve from container")
            container = DIContainer()

            if not self.queue_service:
                self.queue_service = container.resolve(QueueService)

            if not self.analytics_service:
                self.analytics_service = container.resolve(AnalyticsService)

            if not self.content_filter_service:
                self.content_filter_service = container.resolve(ContentFilterService)

            if not self.image_generation_service:
                self.image_generation_service = container.resolve(ImageGenerationService)

        # Set up event bus
        self.event_bus = EventBus()

        # Initialize state
        self.allowed_channels = set(self.config.channel_ids)
        self.resolution_options = []
        self.lora_options = []

        # Load options
        self._load_options()

    def _load_options(self):
        """Load resolution and LoRA options"""
        try:
            # Load resolution options
            ratios_data = self.config.load_json('ratios.json')
            self.resolution_options = list(ratios_data.get('ratios', {}).keys())
            logger.info(f"Loaded {len(self.resolution_options)} resolution options")

            # Load LoRA options
            lora_data = self.config.load_json('lora.json')
            self.lora_options = lora_data.get('available_loras', [])
            logger.info(f"Loaded {len(self.lora_options)} LoRA options")
        except Exception as e:
            logger.error(f"Error loading options: {e}")

    async def reload_options(self):
        """Reload resolution and LoRA options"""
        try:
            self._load_options()
            logger.info("Reloaded options")
        except Exception as e:
            logger.error(f"Error reloading options: {e}")
            raise

    async def setup_hook(self):
        """Set up the bot"""
        logger.info("Setting up bot...")

        # Register commands
        await self._register_commands()

        # Register persistent views
        await self._register_persistent_views()

        # Initialize queue service
        if self.queue_service:
            await self.queue_service.initialize()

        logger.info("Bot setup complete")

    async def _register_persistent_views(self):
        """Register persistent views that work after bot restarts"""
        try:
            # Import views
            from src.presentation.discord.views.video_control_view import VideoControlView
            from src.presentation.discord.views.image_control_view import ImageControlView
            from src.presentation.discord.views.redux_view import ReduxView

            # Add persistent views
            self.add_view(VideoControlView())
            self.add_view(ImageControlView())
            self.add_view(ReduxView(user_id=0))  # Default user_id, will be overridden when creating actual views

            # Log registered views
            logger.info("Registered VideoControlView")
            logger.info("Registered ImageControlView")
            logger.info("Registered ReduxView")

            logger.info("Registered persistent views")
        except Exception as e:
            logger.error(f"Failed to register persistent views: {e}")

    async def _register_commands(self):
        """Register commands with Discord"""
        # Import command modules
        from src.presentation.discord.commands import (
            image_commands,
            queue_commands,
            analytics_commands,
            filter_commands,
            lora_commands
        )

        # Register command modules
        await self.add_cog(image_commands.ImageCommands(self))
        await self.add_cog(queue_commands.QueueCommands(self))
        await self.add_cog(analytics_commands.AnalyticsCommands(self))
        await self.add_cog(filter_commands.FilterCommands(self))
        await self.add_cog(lora_commands.LoraCommands(self))

        # Register commands directly on the tree
        @self.tree.command(name="comfy", description="Generate an image based on a prompt")
        @app_commands.describe(
            prompt="Enter your prompt",
            resolution="Choose the resolution",
            upscale_factor="Choose upscale factor (1-4, default is 1)",
            seed="Enter a seed for reproducibility (optional)"
        )
        @app_commands.choices(resolution=[
            app_commands.Choice(name=name, value=name) for name in self.resolution_options
        ])
        @app_commands.choices(upscale_factor=[
            app_commands.Choice(name="1x (No upscale)", value=1),
            app_commands.Choice(name="2x", value=2),
            app_commands.Choice(name="3x", value=3),
            app_commands.Choice(name="4x", value=4)
        ])
        async def comfy_command(interaction, prompt: str, resolution: str, upscale_factor: int = 1, seed: int = None):
            # Get the image commands cog
            cog = self.get_cog(image_commands.ImageCommands.__name__)
            if cog:
                await cog._comfy_callback(interaction, prompt, resolution, upscale_factor, seed)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        @self.tree.command(name="redux", description="Generate an image using two reference images")
        @app_commands.describe(
            resolution="Choose the resolution for the output image"
        )
        @app_commands.choices(resolution=[
            app_commands.Choice(name=name, value=name) for name in self.resolution_options
        ])
        async def redux_command(interaction, resolution: str):
            # Get the image commands cog
            cog = self.get_cog(image_commands.ImageCommands.__name__)
            if cog:
                await cog.redux_command(interaction, resolution)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        @self.tree.command(name="pulid", description="Generate an image using a reference image and a prompt")
        @app_commands.describe(
            prompt="The prompt to guide the image generation",
            resolution="Choose the resolution for the output image",
            strength="Strength of the reference image (0.1-1.0)",
            upscale_factor="Choose the upscale factor (1-3)"
        )
        @app_commands.choices(resolution=[
            app_commands.Choice(name=name, value=name) for name in self.resolution_options
        ])
        @app_commands.choices(upscale_factor=[
            app_commands.Choice(name="1x", value=1),
            app_commands.Choice(name="2x", value=2),
            app_commands.Choice(name="3x", value=3)
        ])
        async def pulid_command(interaction, prompt: str, resolution: str, strength: float = 0.5, upscale_factor: int = 1):
            # Get the image commands cog
            cog = self.get_cog(image_commands.ImageCommands.__name__)
            if cog:
                await cog.pulid_command(interaction, prompt, resolution, strength, upscale_factor)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        # ReduxPrompt command removed - not implementing this feature

        @self.tree.command(name="video", description="Generate a video based on a prompt")
        @app_commands.describe(
            prompt="Enter your prompt for the video generation"
        )
        async def video_command(interaction, prompt: str):
            # Get the image commands cog
            cog = self.get_cog(image_commands.ImageCommands.__name__)
            if cog:
                # Check if the cog has the method
                if hasattr(cog, 'video_command'):
                    await cog.video_command(interaction, prompt)
                else:
                    await interaction.response.send_message("The video command is not implemented yet", ephemeral=True)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        # Add other commands
        @self.tree.command(name="queue", description="Show the current queue status")
        async def queue_command(interaction):
            cog = self.get_cog(queue_commands.QueueCommands.__name__)
            if cog:
                await cog.queue_command(interaction)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        @self.tree.command(name="clear_queue", description="Clear the queue")
        async def clear_queue_command(interaction):
            cog = self.get_cog(queue_commands.QueueCommands.__name__)
            if cog:
                await cog.clear_queue_command(interaction)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        @self.tree.command(name="set_queue_priority", description="Set the priority for a user in the queue")
        @app_commands.describe(
            user="The user to set priority for",
            priority="The priority level"
        )
        @app_commands.choices(priority=[
            app_commands.Choice(name="High", value=0),
            app_commands.Choice(name="Normal", value=1),
            app_commands.Choice(name="Low", value=2)
        ])
        async def set_queue_priority_command(interaction, user: discord.User, priority: int = 1):
            cog = self.get_cog(queue_commands.QueueCommands.__name__)
            if cog:
                await cog.set_queue_priority_command(interaction, user, priority)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        @self.tree.command(name="stats", description="Show usage statistics")
        @app_commands.describe(
            days="Number of days to show statistics for (default: 7)"
        )
        async def stats_command(interaction, days: int = 7):
            cog = self.get_cog(analytics_commands.AnalyticsCommands.__name__)
            if cog:
                await cog.stats_command(interaction, days)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        @self.tree.command(name="reset_stats", description="Reset usage statistics")
        async def reset_stats_command(interaction):
            cog = self.get_cog(analytics_commands.AnalyticsCommands.__name__)
            if cog:
                await cog.reset_stats_command(interaction)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        @self.tree.command(name="add_banned_word", description="Add a word to the banned words list")
        @app_commands.describe(
            word="The word to ban"
        )
        async def add_banned_word_command(interaction, word: str):
            cog = self.get_cog(filter_commands.FilterCommands.__name__)
            if cog:
                await cog.add_banned_word_command(interaction, word)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        @self.tree.command(name="remove_banned_word", description="Remove a word from the banned words list")
        @app_commands.describe(
            word="The word to unban"
        )
        async def remove_banned_word_command(interaction, word: str):
            cog = self.get_cog(filter_commands.FilterCommands.__name__)
            if cog:
                await cog.remove_banned_word_command(interaction, word)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        @self.tree.command(name="list_banned_words", description="List all banned words")
        async def list_banned_words_command(interaction):
            cog = self.get_cog(filter_commands.FilterCommands.__name__)
            if cog:
                await cog.list_banned_words_command(interaction)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        @self.tree.command(name="add_regex_pattern", description="Add a regex pattern to the content filter")
        @app_commands.describe(
            name="Name of the pattern",
            pattern="Regex pattern",
            description="Description of the pattern",
            severity="Severity level (high, medium, low)"
        )
        async def add_regex_pattern_command(interaction, name: str, pattern: str, description: str, severity: str = "medium"):
            cog = self.get_cog(filter_commands.FilterCommands.__name__)
            if cog:
                await cog.add_regex_pattern_command(interaction, name, pattern, description, severity)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        @self.tree.command(name="warnings", description="Check warnings for a user")
        @app_commands.describe(
            user="User to check warnings for (optional, defaults to yourself)"
        )
        async def warnings_command(interaction, user: discord.User = None):
            cog = self.get_cog(filter_commands.FilterCommands.__name__)
            if cog:
                await cog.warnings_command(interaction, user)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        @self.tree.command(name="warningremove", description="Remove all warnings from a user")
        @app_commands.describe(
            user="User to remove warnings from"
        )
        async def warningremove_command(interaction, user: discord.User):
            cog = self.get_cog(filter_commands.FilterCommands.__name__)
            if cog:
                await cog.warningremove_command(interaction, user)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        @self.tree.command(name="banned", description="List all banned users")
        async def banned_command(interaction):
            cog = self.get_cog(filter_commands.FilterCommands.__name__)
            if cog:
                await cog.banned_command(interaction)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        @self.tree.command(name="ban", description="Ban a user from using the bot")
        @app_commands.describe(
            user="User to ban",
            reason="Reason for the ban"
        )
        async def ban_command(interaction, user: discord.User, reason: str):
            cog = self.get_cog(filter_commands.FilterCommands.__name__)
            if cog:
                await cog.ban_command(interaction, user, reason)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        @self.tree.command(name="unban", description="Unban a user from using the bot")
        @app_commands.describe(
            user="User to unban"
        )
        async def unban_command(interaction, user: discord.User):
            cog = self.get_cog(filter_commands.FilterCommands.__name__)
            if cog:
                await cog.unban_command(interaction, user)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        @self.tree.command(name="lorainfo", description="Show information about available LoRAs")
        @app_commands.describe(
            lora_name="Name of the LoRA to show information for (optional)"
        )
        async def lorainfo_command(interaction, lora_name: str = None):
            cog = self.get_cog(lora_commands.LoraCommands.__name__)
            if cog:
                await cog.lorainfo_command(interaction, lora_name)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        @self.tree.command(name="sync", description="Sync commands with Discord")
        async def sync_command(interaction):
            cog = self.get_cog(image_commands.ImageCommands.__name__)
            if cog:
                await cog.sync_command(interaction)
            else:
                await interaction.response.send_message("Command handler not found", ephemeral=True)

        logger.info("Registered command modules")

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f"{self.user} has connected to Discord!")
        logger.info(f"Bot is in {len(self.guilds)} guilds")

        # Initialize redux requests storage
        if not hasattr(self, 'redux_requests'):
            self.redux_requests = {}

        # Initialize active redux users storage
        if not hasattr(self, 'active_redux_users'):
            self.active_redux_users = {}

        # Sync commands with Discord
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle command errors"""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"Command is on cooldown. Try again in {error.retry_after:.2f}s",
                ephemeral=True
            )
        else:
            logger.error(f"Command error: {error}", exc_info=True)

    async def on_message(self, message):
        """Handle messages for image uploads in redux workflow"""
        # Ignore messages from the bot itself
        if message.author.id == self.user.id:
            return

        # Process commands first
        await self.process_commands(message)

        # Check if this user has an active redux request
        if not hasattr(self, 'active_redux_users') or message.author.id not in self.active_redux_users:
            return

        # Get the request ID
        request_id = self.active_redux_users[message.author.id]

        # Get the request data
        if not hasattr(self, 'redux_requests') or request_id not in self.redux_requests:
            return

        request_data = self.redux_requests[request_id]

        # Check if the message has an attachment
        if not message.attachments:
            return

        # Get the first attachment
        attachment = message.attachments[0]

        # Check if it's an image
        if not attachment.content_type or not attachment.content_type.startswith('image/'):
            await message.channel.send("Please upload an image file.")
            return

        try:
            # Download the image
            image_path = None

            # Get the original message or create one if it doesn't exist
            original_message = None
            if 'original_message_id' in request_data and request_data['original_message_id']:
                try:
                    original_message = await message.channel.fetch_message(int(request_data['original_message_id']))
                except Exception as e:
                    logger.error(f"Error fetching original message: {e}")

            if not original_message:
                # Create a new message if we couldn't find the original
                original_message = await message.channel.send("Processing image...")
                request_data['original_message_id'] = str(original_message.id)

            # Create output directory if it doesn't exist
            output_dir = os.path.join('output', request_id)
            os.makedirs(output_dir, exist_ok=True)

            # Check which image we're processing
            if request_data['image1_path'] is None:
                # First image
                image_path = os.path.join(output_dir, 'image1.png')
                await attachment.save(image_path)
                request_data['image1_path'] = image_path
                logger.info(f"Saved first image to {image_path}")

                # Delete the user's message
                try:
                    await message.delete()
                except Exception as e:
                    logger.error(f"Error deleting message: {e}")

                # Update the original message
                await original_message.edit(content="First image received. Please upload the second reference image.")

            elif request_data['image2_path'] is None:
                # Second image
                image_path = os.path.join(output_dir, 'image2.png')
                await attachment.save(image_path)
                request_data['image2_path'] = image_path
                logger.info(f"Saved second image to {image_path}")

                # Delete the user's message
                try:
                    await message.delete()
                except Exception as e:
                    logger.error(f"Error deleting message: {e}")

                # Update the original message
                await original_message.edit(content="Second image received. Starting generation process...")

                # Remove the user from active redux users
                del self.active_redux_users[message.author.id]

                # Process the request
                await self._process_redux_request(request_id, original_message)

        except Exception as e:
            logger.error(f"Error processing redux image: {e}", exc_info=True)
            await message.channel.send(f"Error processing image: {str(e)}")

    async def _process_redux_request(self, request_id, message):
        """Process a redux request with both images"""
        try:
            # Get the request data
            request_data = self.redux_requests[request_id]

            # Create a ReduxRequestItem
            from src.domain.models.queue_item import ReduxRequestItem, QueuePriority

            # Set is_redux flag to True to use ReduxImageView instead of ImageControlView
            # Use the original message ID from the first response message
            request_item = ReduxRequestItem(
                id=request_id,
                user_id=request_data['user_id'],
                channel_id=request_data['channel_id'],
                interaction_id=None,
                original_message_id=str(message.id),
                resolution=request_data['resolution'],
                strength1=request_data['strength1'],
                strength2=request_data['strength2'],
                workflow_filename="Redux.json",  # Default Redux workflow (case sensitive)
                image1_path=request_data['image1_path'],
                image2_path=request_data['image2_path'],
                is_redux=True,  # Add this flag to indicate it's a redux request
                seed=random.randint(0, 2**32 - 1)  # Add a random seed for node 25
            )

            # Explicitly set the is_redux attribute to ensure it's properly set
            setattr(request_item, 'is_redux', True)
            logger.info(f"Set is_redux=True on request_item {request_id}")

            # Add to queue
            success, queue_id, queue_message = await self.queue_service.add_request(
                request_item,
                QueuePriority.NORMAL
            )

            if not success:
                await message.edit(content=f"Failed to add request to queue: {queue_message}")
                return

            # Record command execution
            from src.domain.events.common_events import CommandExecutedEvent

            self.event_bus.publish(CommandExecutedEvent(
                command_name="redux",
                user_id=request_data['user_id'],
                guild_id=message.guild.id if message.guild else None,
                channel_id=request_data['channel_id'],
                execution_time=time.time() - request_data['start_time'],
                success=True
            ))

        except Exception as e:
            logger.error(f"Error processing redux request: {e}", exc_info=True)
            await message.edit(content=f"Error processing request: {str(e)}")

            # Record command execution
            from src.domain.events.common_events import CommandExecutedEvent

            self.event_bus.publish(CommandExecutedEvent(
                command_name="redux",
                user_id=request_data['user_id'] if 'user_id' in request_data else "unknown",
                guild_id=message.guild.id if message.guild else None,
                channel_id=request_data['channel_id'] if 'channel_id' in request_data else "unknown",
                execution_time=time.time() - request_data.get('start_time', time.time()),
                success=False
            ))

    def get_python_command(self) -> str:
        """Get the appropriate Python command for the current platform"""
        if platform.system() == "Windows":
            return "python"
        else:
            return "python3"

    async def close(self):
        """Close the bot and clean up resources"""
        logger.info("Shutting down bot...")
        await super().close()

    def is_channel_allowed(self, channel_id: int) -> bool:
        """
        Check if a channel is allowed.

        Args:
            channel_id: ID of the channel

        Returns:
            True if the channel is allowed, False otherwise
        """
        return channel_id in self.allowed_channels
