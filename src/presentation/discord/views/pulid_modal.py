"""
Discord modal for PuLID image generation.
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

from src.domain.models.queue_item import RequestItem, QueuePriority
from src.domain.events.event_bus import EventBus
from src.domain.events.common_events import CommandExecutedEvent
from src.infrastructure.config.config_manager import ConfigManager
from src.infrastructure.comfyui.comfyui_service import ComfyUIService

logger = logging.getLogger(__name__)

class PulidModal(Modal):
    """
    Modal for PuLID image generation.
    Used for the pulid command.
    """
    
    def __init__(self, bot):
        """
        Initialize the PuLID modal.
        
        Args:
            bot: Discord bot instance
        """
        super().__init__(title="Generate Image from Reference")
        self.bot = bot
        self.event_bus = EventBus()
        self.config = ConfigManager()
        self.comfyui_service = ComfyUIService()
        
        # Default values
        self.resolution = "512x512"
        self.prompt = ""
        
        # Add image URL input
        self.image_input = TextInput(
            label="Image URL",
            placeholder="Enter URL for the reference image",
            style=discord.TextStyle.short,
            required=True
        )
        self.add_item(self.image_input)
        
        # Add prompt input
        self.prompt_input = TextInput(
            label="Prompt",
            placeholder="Enter your prompt here...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        self.add_item(self.prompt_input)
        
        # Add negative prompt input
        self.negative_prompt_input = TextInput(
            label="Negative Prompt (optional)",
            placeholder="Enter things to avoid in the image...",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000
        )
        self.add_item(self.negative_prompt_input)
        
        # Add strength input
        self.strength_input = TextInput(
            label="Strength (0.1-1.0)",
            placeholder="Enter strength for the reference image (default: 0.5)",
            style=discord.TextStyle.short,
            required=False,
            default="0.5"
        )
        self.add_item(self.strength_input)
        
    async def on_submit(self, interaction: discord.Interaction):
        """
        Handle modal submission.
        
        Args:
            interaction: Discord interaction
        """
        start_time = time.time()
        
        try:
            # Get input values
            image_url = self.image_input.value
            prompt = self.prompt_input.value
            negative_prompt = self.negative_prompt_input.value
            
            # Combine prompts if negative prompt is provided
            if negative_prompt:
                full_prompt = f"{prompt} ### {negative_prompt}"
            else:
                full_prompt = prompt
                
            # Parse strength
            try:
                strength = float(self.strength_input.value or "0.5")
                
                # Validate strength
                if not (0.1 <= strength <= 1.0):
                    await interaction.response.send_message(
                        "Strength value must be between 0.1 and 1.0.",
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    "Invalid strength value. Please enter a number between 0.1 and 1.0.",
                    ephemeral=True
                )
                return
                
            # Check content filter
            is_allowed, violation_type, violation_details = self.bot.content_filter_service.check_prompt(
                str(interaction.user.id),
                full_prompt
            )
            
            if not is_allowed:
                await interaction.response.send_message(
                    f"Your prompt was flagged by our content filter: {violation_details}",
                    ephemeral=True
                )
                
                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="pulid",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))
                
                return
                
            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=False)
            
            # Send processing message
            message = await interaction.followup.send(
                "🔄 Downloading reference image...",
                ephemeral=False
            )
            
            # Download image
            try:
                # Create directory for image
                request_id = str(uuid.uuid4())
                image_dir = os.path.join('temp', request_id)
                os.makedirs(image_dir, exist_ok=True)
                
                # Download image
                image_path = os.path.join(image_dir, 'reference.png')
                await self._download_image(image_url, image_path)
                
                # Update message
                await message.edit(content="🔄 Starting generation process...")
                
                # Load PuLID workflow
                workflow = self.config.load_json(self.config.pulid_workflow)
                
                # Update workflow
                workflow = self.comfyui_service.update_reduxprompt_workflow(
                    workflow=workflow,
                    image_path=image_path,
                    prompt=full_prompt,
                    strength=strength,
                    resolution=self.resolution,
                    loras=[],  # No LoRAs by default
                    upscale_factor=1
                )
                
                # Save workflow
                workflow_filename = f"pulid_{request_id}.json"
                self.config.save_json(workflow_filename, workflow)
                
                # Create request item
                request_item = RequestItem(
                    id=str(uuid.uuid4()),
                    user_id=str(interaction.user.id),
                    channel_id=str(interaction.channel_id),
                    interaction_id=str(interaction.id),
                    original_message_id=str(message.id),
                    prompt=full_prompt,
                    resolution=self.resolution,
                    loras=[],  # No LoRAs by default
                    upscale_factor=1,
                    workflow_filename=workflow_filename,
                    seed=None,
                    is_pulid=True
                )
                
                # Add to queue
                success, request_id, queue_message = await self.bot.queue_service.add_request(
                    request_item,
                    QueuePriority.NORMAL
                )
                
                if not success:
                    await interaction.followup.send(
                        f"Failed to add request to queue: {queue_message}",
                        ephemeral=True
                    )
                    
                    # Record command execution
                    self.event_bus.publish(CommandExecutedEvent(
                        command_name="pulid",
                        user_id=str(interaction.user.id),
                        guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                        channel_id=str(interaction.channel_id),
                        execution_time=time.time() - start_time,
                        success=False
                    ))
                    
                    return
                    
                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="pulid",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=True
                ))
                
            except Exception as e:
                logger.error(f"Error downloading image: {e}", exc_info=True)
                
                await interaction.followup.send(
                    f"Error downloading image: {str(e)}",
                    ephemeral=True
                )
                
                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="pulid",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))
                
        except Exception as e:
            logger.error(f"Error in pulid modal: {e}", exc_info=True)
            
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
                command_name="pulid",
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
