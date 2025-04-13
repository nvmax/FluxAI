"""
Discord view for displaying generated images.
"""

import discord
import logging
import uuid
import random
from typing import Dict, Any, List, Optional

from discord.ui import View, Button, Select

from src.domain.models.queue_item import RequestItem, QueuePriority
from src.infrastructure.config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class ImageControlView(View):
    """
    View for displaying generated images.
    Provides buttons for regenerating, upscaling, and more.
    """
    
    def __init__(self, bot):
        """
        Initialize the image control view.
        
        Args:
            bot: Discord bot instance
        """
        super().__init__(timeout=None)
        self.bot = bot
        self.config = ConfigManager()
        
        # Add buttons
        self.add_item(Button(
            style=discord.ButtonStyle.primary,
            label="Regenerate",
            custom_id="regenerate",
            emoji="🔄"
        ))
        
        self.add_item(Button(
            style=discord.ButtonStyle.secondary,
            label="Upscale 2x",
            custom_id="upscale_2x",
            emoji="🔍"
        ))
        
        self.add_item(Button(
            style=discord.ButtonStyle.secondary,
            label="Upscale 4x",
            custom_id="upscale_4x",
            emoji="🔎"
        ))
        
        self.add_item(Button(
            style=discord.ButtonStyle.success,
            label="Variations",
            custom_id="variations",
            emoji="🎲"
        ))
        
        self.add_item(Button(
            style=discord.ButtonStyle.danger,
            label="Delete",
            custom_id="delete",
            emoji="🗑️"
        ))
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Check if the user can interact with the view.
        
        Args:
            interaction: Discord interaction
            
        Returns:
            True if the user can interact, False otherwise
        """
        # Check if the channel is allowed
        if interaction.channel_id not in self.bot.allowed_channels:
            await interaction.response.send_message(
                "This command can only be used in specific channels.",
                ephemeral=True
            )
            return False
            
        return True
        
    @discord.ui.button(custom_id="regenerate", style=discord.ButtonStyle.primary, label="Regenerate", emoji="🔄")
    async def regenerate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Handle regenerate button click.
        
        Args:
            interaction: Discord interaction
            button: Button that was clicked
        """
        try:
            # Get the message
            message = interaction.message
            
            # Get the embed
            embed = message.embeds[0] if message.embeds else None
            if not embed:
                await interaction.response.send_message(
                    "Could not find image information.",
                    ephemeral=True
                )
                return
                
            # Get the prompt from the embed
            prompt = embed.description
            if not prompt:
                await interaction.response.send_message(
                    "Could not find prompt information.",
                    ephemeral=True
                )
                return
                
            # Defer response
            await interaction.response.defer(ephemeral=False)
            
            # Send processing message
            processing_message = await interaction.followup.send(
                "🔄 Regenerating image...",
                ephemeral=False
            )
            
            # Create request item
            request_item = RequestItem(
                id=str(uuid.uuid4()),
                user_id=str(interaction.user.id),
                channel_id=str(interaction.channel_id),
                interaction_id=str(interaction.id),
                original_message_id=str(processing_message.id),
                prompt=prompt,
                resolution="512x512",  # Default resolution
                loras=[],  # No LoRAs by default
                upscale_factor=1,
                workflow_filename=None,
                seed=random.randint(0, 2**32 - 1),  # Random seed
                is_pulid=False
            )
            
            # Add to queue
            success, request_id, message = await self.bot.queue_service.add_request(
                request_item,
                QueuePriority.NORMAL
            )
            
            if not success:
                await interaction.followup.send(
                    f"Failed to add request to queue: {message}",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error in regenerate button: {e}", exc_info=True)
            
            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
            
    @discord.ui.button(custom_id="upscale_2x", style=discord.ButtonStyle.secondary, label="Upscale 2x", emoji="🔍")
    async def upscale_2x_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Handle upscale 2x button click.
        
        Args:
            interaction: Discord interaction
            button: Button that was clicked
        """
        try:
            # Get the message
            message = interaction.message
            
            # Get the embed
            embed = message.embeds[0] if message.embeds else None
            if not embed:
                await interaction.response.send_message(
                    "Could not find image information.",
                    ephemeral=True
                )
                return
                
            # Get the prompt from the embed
            prompt = embed.description
            if not prompt:
                await interaction.response.send_message(
                    "Could not find prompt information.",
                    ephemeral=True
                )
                return
                
            # Defer response
            await interaction.response.defer(ephemeral=False)
            
            # Send processing message
            processing_message = await interaction.followup.send(
                "🔍 Upscaling image (2x)...",
                ephemeral=False
            )
            
            # Create request item
            request_item = RequestItem(
                id=str(uuid.uuid4()),
                user_id=str(interaction.user.id),
                channel_id=str(interaction.channel_id),
                interaction_id=str(interaction.id),
                original_message_id=str(processing_message.id),
                prompt=prompt,
                resolution="512x512",  # Default resolution
                loras=[],  # No LoRAs by default
                upscale_factor=2,  # 2x upscale
                workflow_filename=None,
                seed=random.randint(0, 2**32 - 1),  # Random seed
                is_pulid=False
            )
            
            # Add to queue
            success, request_id, message = await self.bot.queue_service.add_request(
                request_item,
                QueuePriority.NORMAL
            )
            
            if not success:
                await interaction.followup.send(
                    f"Failed to add request to queue: {message}",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error in upscale 2x button: {e}", exc_info=True)
            
            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
            
    @discord.ui.button(custom_id="upscale_4x", style=discord.ButtonStyle.secondary, label="Upscale 4x", emoji="🔎")
    async def upscale_4x_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Handle upscale 4x button click.
        
        Args:
            interaction: Discord interaction
            button: Button that was clicked
        """
        try:
            # Get the message
            message = interaction.message
            
            # Get the embed
            embed = message.embeds[0] if message.embeds else None
            if not embed:
                await interaction.response.send_message(
                    "Could not find image information.",
                    ephemeral=True
                )
                return
                
            # Get the prompt from the embed
            prompt = embed.description
            if not prompt:
                await interaction.response.send_message(
                    "Could not find prompt information.",
                    ephemeral=True
                )
                return
                
            # Defer response
            await interaction.response.defer(ephemeral=False)
            
            # Send processing message
            processing_message = await interaction.followup.send(
                "🔎 Upscaling image (4x)...",
                ephemeral=False
            )
            
            # Create request item
            request_item = RequestItem(
                id=str(uuid.uuid4()),
                user_id=str(interaction.user.id),
                channel_id=str(interaction.channel_id),
                interaction_id=str(interaction.id),
                original_message_id=str(processing_message.id),
                prompt=prompt,
                resolution="512x512",  # Default resolution
                loras=[],  # No LoRAs by default
                upscale_factor=4,  # 4x upscale
                workflow_filename=None,
                seed=random.randint(0, 2**32 - 1),  # Random seed
                is_pulid=False
            )
            
            # Add to queue
            success, request_id, message = await self.bot.queue_service.add_request(
                request_item,
                QueuePriority.NORMAL
            )
            
            if not success:
                await interaction.followup.send(
                    f"Failed to add request to queue: {message}",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error in upscale 4x button: {e}", exc_info=True)
            
            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
            
    @discord.ui.button(custom_id="variations", style=discord.ButtonStyle.success, label="Variations", emoji="🎲")
    async def variations_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Handle variations button click.
        
        Args:
            interaction: Discord interaction
            button: Button that was clicked
        """
        try:
            # Get the message
            message = interaction.message
            
            # Get the embed
            embed = message.embeds[0] if message.embeds else None
            if not embed:
                await interaction.response.send_message(
                    "Could not find image information.",
                    ephemeral=True
                )
                return
                
            # Get the prompt from the embed
            prompt = embed.description
            if not prompt:
                await interaction.response.send_message(
                    "Could not find prompt information.",
                    ephemeral=True
                )
                return
                
            # Defer response
            await interaction.response.defer(ephemeral=False)
            
            # Generate 3 variations
            for i in range(3):
                # Send processing message
                processing_message = await interaction.followup.send(
                    f"🎲 Generating variation {i+1}/3...",
                    ephemeral=False
                )
                
                # Create request item
                request_item = RequestItem(
                    id=str(uuid.uuid4()),
                    user_id=str(interaction.user.id),
                    channel_id=str(interaction.channel_id),
                    interaction_id=str(interaction.id),
                    original_message_id=str(processing_message.id),
                    prompt=prompt,
                    resolution="512x512",  # Default resolution
                    loras=[],  # No LoRAs by default
                    upscale_factor=1,
                    workflow_filename=None,
                    seed=random.randint(0, 2**32 - 1),  # Random seed
                    is_pulid=False
                )
                
                # Add to queue
                success, request_id, message = await self.bot.queue_service.add_request(
                    request_item,
                    QueuePriority.NORMAL
                )
                
                if not success:
                    await interaction.followup.send(
                        f"Failed to add request to queue: {message}",
                        ephemeral=True
                    )
                    break
                
        except Exception as e:
            logger.error(f"Error in variations button: {e}", exc_info=True)
            
            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
            
    @discord.ui.button(custom_id="delete", style=discord.ButtonStyle.danger, label="Delete", emoji="🗑️")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Handle delete button click.
        
        Args:
            interaction: Discord interaction
            button: Button that was clicked
        """
        try:
            # Check if the user is the original requester or has manage messages permission
            message = interaction.message
            
            # Get the embed
            embed = message.embeds[0] if message.embeds else None
            if not embed:
                await interaction.response.send_message(
                    "Could not find image information.",
                    ephemeral=True
                )
                return
                
            # Get the requester from the embed footer
            footer_text = embed.footer.text if embed.footer else ""
            requester_id = footer_text.replace("Requested by ", "") if footer_text.startswith("Requested by ") else None
            
            # Check if the user is the requester or has manage messages permission
            is_requester = requester_id and requester_id == str(interaction.user.id)
            has_permission = interaction.user.guild_permissions.manage_messages
            
            if not (is_requester or has_permission):
                await interaction.response.send_message(
                    "You can only delete your own images or if you have manage messages permission.",
                    ephemeral=True
                )
                return
                
            # Delete the message
            await message.delete()
            
            # Send confirmation
            await interaction.response.send_message(
                "Image deleted.",
                ephemeral=True
            )
                
        except Exception as e:
            logger.error(f"Error in delete button: {e}", exc_info=True)
            
            await interaction.response.send_message(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
