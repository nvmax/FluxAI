"""
Discord modal for Redux image generation.
"""

import discord
import logging
import uuid
import time
import os
import aiohttp
import io
from typing import Dict, Any, List, Optional

from discord.ui import Modal, TextInput

from src.domain.models.queue_item import ReduxRequestItem, QueuePriority
from src.domain.events.event_bus import EventBus
from src.domain.events.common_events import CommandExecutedEvent
from src.infrastructure.config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class ReduxModal(Modal):
    """
    Modal for Redux image generation.
    Used for the redux command.
    """

    def __init__(self, bot, resolution: str = "512x512"):
        """
        Initialize the Redux modal.

        Args:
            bot: Discord bot instance
            resolution: Resolution for the output image
        """
        super().__init__(title="Set Strength Values for Images")
        self.bot = bot
        self.event_bus = EventBus()
        self.config = ConfigManager()
        self.resolution = resolution

        # Add strength 1 input
        self.strength1_input = TextInput(
            label="Strength 1 (0.1-1.0)",
            placeholder="Enter strength for the first image",
            style=discord.TextStyle.short,
            required=False,
            default="1.0"
        )
        self.add_item(self.strength1_input)

        # Add strength 2 input
        self.strength2_input = TextInput(
            label="Strength 2 (0.1-1.0)",
            placeholder="Enter strength for the second image",
            style=discord.TextStyle.short,
            required=False,
            default="0.5"
        )
        self.add_item(self.strength2_input)

    async def on_submit(self, interaction: discord.Interaction):
        """
        Handle modal submission.

        Args:
            interaction: Discord interaction
        """
        start_time = time.time()

        try:
            # Parse strengths
            try:
                strength1 = float(self.strength1_input.value or "1.0")
                strength2 = float(self.strength2_input.value or "0.5")

                # Validate strengths
                if not (0.1 <= strength1 <= 1.0) or not (0.1 <= strength2 <= 1.0):
                    await interaction.response.send_message(
                        "Strength values must be between 0.1 and 1.0.",
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    "Invalid strength values. Please enter numbers between 0.1 and 1.0.",
                    ephemeral=True
                )
                return

            # Create a unique ID for this request
            request_id = str(uuid.uuid4())

            # Create directory for images in the output folder
            image_dir = os.path.join('output', request_id)
            os.makedirs(image_dir, exist_ok=True)
            logger.info(f"Created output directory for redux request: {image_dir}")

            # Store the strength values and resolution in the bot's temporary storage
            if not hasattr(self.bot, 'redux_requests'):
                self.bot.redux_requests = {}

            self.bot.redux_requests[request_id] = {
                'strength1': strength1,
                'strength2': strength2,
                'resolution': self.resolution,
                'user_id': str(interaction.user.id),
                'channel_id': str(interaction.channel_id),
                'image_dir': image_dir,
                'image1_path': None,
                'image2_path': None,
                'start_time': start_time
            }

            # Ask the user to upload the first image
            response = await interaction.response.send_message(
                "Please upload the first reference image. I'll remove it after processing.",
                ephemeral=False
            )

            # Get the message object
            original_message = await interaction.original_response()

            # Store the message ID in the request data
            self.bot.redux_requests[request_id]['original_message_id'] = str(original_message.id)

            # Create a message collector to wait for the image upload
            def check_image1(message):
                # Check if the message is from the same user and has an attachment
                return (
                    message.author.id == interaction.user.id and
                    message.channel.id == interaction.channel_id and
                    len(message.attachments) > 0
                )

            # Store the request ID in the user's active requests
            if not hasattr(self.bot, 'active_redux_users'):
                self.bot.active_redux_users = {}

            self.bot.active_redux_users[interaction.user.id] = request_id

        except Exception as e:
            logger.error(f"Error in redux modal: {e}", exc_info=True)

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"An error occurred: {str(e)}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"An error occurred: {str(e)}",
                    ephemeral=True
                )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="redux",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    async def _download_image(self, url: str, path: str):
        """
        Download an image from a URL.

        Args:
            url: URL of the image
            path: Path to save the image to
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to download image: {response.status}")

                data = await response.read()

                # Save the image
                with open(path, 'wb') as f:
                    f.write(data)

                logger.debug(f"Downloaded image to {path}")
