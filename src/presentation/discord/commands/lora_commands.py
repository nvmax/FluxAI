"""
Discord commands for LoRA management.
"""

import discord
import logging
import time
import json
import aiohttp
import os
import re
from typing import Dict, Any, List, Optional
from discord import app_commands, ui
from discord.ext import commands

from src.domain.events.event_bus import EventBus
from src.domain.events.common_events import CommandExecutedEvent
from src.infrastructure.config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class LoraInfoView(ui.View):
    """A paginated view for displaying LoRA information"""
    def __init__(self, loras: List[dict]):
        super().__init__(timeout=300)  # 5 minute timeout
        self.loras = loras
        self.current_page = 0
        self.items_per_page = 5  # Show 5 LoRAs per page
        self.total_pages = (len(self.loras) + self.items_per_page - 1) // self.items_per_page
        self.message = None
        self.update_buttons()

    def extract_civitai_model_id(self, url: str) -> str:
        """Extract the model ID from a Civitai URL"""
        if not url or 'civitai.com' not in url:
            return None

        # Try to extract the model ID using regex
        model_id_match = re.search(r'models/([0-9]+)', url)
        if model_id_match:
            return model_id_match.group(1)
        return None

    async def get_preview_image_url(self, url: str) -> str:
        """Get a preview image URL for a Civitai model"""
        if not url or 'civitai.com' not in url:
            logger.warning(f"Not a Civitai URL: {url}")
            return None

        # Extract the model ID from the URL
        model_id = self.extract_civitai_model_id(url)
        logger.info(f"Extracted model ID: {model_id} from URL: {url}")
        if not model_id:
            logger.warning(f"Could not extract model ID from URL: {url}")
            return None

        try:
            # Use Civitai's official API to get model information
            async with aiohttp.ClientSession() as session:
                api_url = f"https://civitai.com/api/v1/models/{model_id}"
                logger.info(f"Fetching model info from: {api_url}")
                async with session.get(api_url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to get model info: {response.status}")
                        return None

                    data = await response.json()

                    # Get the first model version
                    if 'modelVersions' in data and len(data['modelVersions']) > 0:
                        model_version = data['modelVersions'][0]

                        # Get the first image
                        if 'images' in model_version and len(model_version['images']) > 0:
                            image = model_version['images'][0]
                            return image.get('url')
        except Exception as e:
            logger.error(f"Error getting preview image: {e}")

        return None

    def update_buttons(self):
        """Update navigation buttons based on current page"""
        # Clear existing buttons
        for item in self.children.copy():
            if isinstance(item, ui.Button):
                self.remove_item(item)

        # Add navigation buttons if needed
        if self.total_pages > 1:
            # Previous button
            if self.current_page > 0:
                previous_button = ui.Button(
                    label=f"◀ Previous (Page {self.current_page}/{self.total_pages})",
                    style=discord.ButtonStyle.secondary,
                    custom_id="previous_page",
                    row=1
                )
                previous_button.callback = self.previous_page_callback
                self.add_item(previous_button)

            # Next button
            if self.current_page < self.total_pages - 1:
                next_button = ui.Button(
                    label=f"Next (Page {self.current_page + 2}/{self.total_pages}) ▶",
                    style=discord.ButtonStyle.secondary,
                    custom_id="next_page",
                    row=1
                )
                next_button.callback = self.next_page_callback
                self.add_item(next_button)

    async def previous_page_callback(self, interaction: discord.Interaction):
        """Handle previous page button click"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = await self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    async def next_page_callback(self, interaction: discord.Interaction):
        """Handle next page button click"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = await self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    async def create_embed(self) -> discord.Embed:
        """Create an embed for the current page"""
        embed = discord.Embed(
            title=f"LoRA Information (Page {self.current_page + 1} of {self.total_pages})",
            description=f"Total: {len(self.loras)} | Click on the preview links to see example images for each LoRA.",
            color=discord.Color.blue()
        )

        # Set footer with page info
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages} | Use /lorainfo [lora_name] for details")

        # Get LoRAs for the current page
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.loras))
        page_loras = self.loras[start_idx:end_idx]

        # Process each LoRA
        for i, lora in enumerate(page_loras):
            name = lora.get('name', 'Unknown LoRA')
            url = lora.get('url', '')
            trigger_words = lora.get('add_prompt', '')
            weight = lora.get('weight', 1.0)

            # Create field value with LoRA details
            field_value = ""

            # Try to get a preview image for this LoRA
            if url:
                try:
                    preview_url = await self.get_preview_image_url(url)
                    if preview_url:
                        # Make the preview link very prominent
                        field_value += f"**[🖼️ CLICK HERE FOR PREVIEW IMAGE]({preview_url})**\n\n"
                except Exception as e:
                    logger.error(f"Error getting preview image: {e}")

            # Add the rest of the LoRA information
            if url:
                field_value += f"[📄 View on Civitai]({url})\n"
            if trigger_words:
                field_value += f"🔤 Trigger Words: `{trigger_words}`\n"
            field_value += f"⚖️ Weight: {weight}"

            # Add a separator before each LoRA except the first one
            if i > 0:
                embed.add_field(name="────────────────────", value="", inline=False)

            # Add field to embed
            embed.add_field(
                name=f"📦 {name}",
                value=field_value or "No details available.",
                inline=False
            )

        return embed

    def get_page_content(self) -> str:
        """Get a text representation of the current page (fallback)"""
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.loras))
        page_loras = self.loras[start_idx:end_idx]

        content = f"**LoRA Information** (Page {self.current_page + 1}/{self.total_pages})\n\n"

        for lora in page_loras:
            name = lora.get('name', 'Unknown LoRA')
            url = lora.get('url', '')
            trigger_words = lora.get('add_prompt', '')
            weight = lora.get('weight', 1.0)

            content += f"**📦 {name}**\n"
            if url:
                content += f"📄 URL: {url}\n"
            if trigger_words:
                content += f"🔤 Trigger Words: {trigger_words}\n"
            content += f"⚖️ Weight: {weight}\n\n"
            content += "────────────────────\n\n"

        return content

class LoraCommands(commands.Cog):
    """Commands for managing LoRAs"""

    def __init__(self, bot):
        """
        Initialize LoRA commands.

        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.event_bus = EventBus()
        self.config = ConfigManager()

    async def cog_load(self):
        """Called when the cog is loaded"""
        logger.info("LoRA commands loaded")

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info("LoRA commands ready")

    def _check_admin(self, interaction: discord.Interaction) -> bool:
        """
        Check if the user has admin permissions.

        Args:
            interaction: Discord interaction

        Returns:
            True if the user has admin permissions, False otherwise
        """
        if not interaction.guild:
            return False

        # Check if user has admin permissions
        if interaction.user.guild_permissions.administrator:
            return True

        # Check if user has bot manager role
        if self.bot.config.bot_manager_role_id:
            role = interaction.guild.get_role(self.bot.config.bot_manager_role_id)
            if role and role in interaction.user.roles:
                return True

        return False

    # Command is registered in bot.py
    async def lorainfo_command(self, interaction: discord.Interaction, lora_name: str = None):
        """
        Show information about available LoRAs.

        Args:
            interaction: Discord interaction
            lora_name: Name of the LoRA to show information for (optional)
        """
        start_time = time.time()

        try:
            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # Load LoRA data
            lora_data = self.config.load_json('lora.json')
            available_loras = lora_data.get('available_loras', [])

            if not available_loras:
                await interaction.followup.send(
                    "No LoRAs available.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="lorainfo",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=True
                ))

                return

            # If a specific LoRA was requested
            if lora_name:
                # Find the LoRA
                lora = next((l for l in available_loras if l.get('name', '').lower() == lora_name.lower()), None)

                if not lora:
                    await interaction.followup.send(
                        f"LoRA '{lora_name}' not found.",
                        ephemeral=True
                    )

                    # Record command execution
                    self.event_bus.publish(CommandExecutedEvent(
                        command_name="lorainfo",
                        user_id=str(interaction.user.id),
                        guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                        channel_id=str(interaction.channel_id),
                        execution_time=time.time() - start_time,
                        success=False
                    ))

                    return

                # Create embed
                embed = discord.Embed(
                    title=f"LoRA: {lora.get('name', 'Unknown')}",
                    description=lora.get('description', 'No description available.'),
                    color=discord.Color.blue()
                )

                # Add fields
                if 'civitai_id' in lora:
                    embed.add_field(
                        name="Civitai ID",
                        value=str(lora['civitai_id']),
                        inline=True
                    )

                    # Get preview image from Civitai API
                    try:
                        preview_url = await self._get_lora_preview(lora['civitai_id'])
                        if preview_url:
                            embed.set_image(url=preview_url)
                    except Exception as e:
                        logger.error(f"Error getting LoRA preview: {e}")

                if 'trigger_words' in lora:
                    embed.add_field(
                        name="Trigger Words",
                        value=", ".join(lora['trigger_words']),
                        inline=False
                    )

                if 'recommended_strength' in lora:
                    embed.add_field(
                        name="Recommended Strength",
                        value=f"Model: {lora.get('recommended_strength', {}).get('model', 0.7)}, CLIP: {lora.get('recommended_strength', {}).get('clip', 0.7)}",
                        inline=True
                    )

                # Send response
                await interaction.followup.send(embed=embed, ephemeral=True)

            else:
                # Create the view and embed for all LoRAs
                view = LoraInfoView(available_loras)
                embed = await view.create_embed()

                # Send the response with the embed and view
                await interaction.followup.send(
                    content="Use `/lorainfo [lora_name]` to see details about a specific LoRA.",
                    embed=embed,
                    view=view,
                    ephemeral=True
                )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="lorainfo",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=True
            ))

        except Exception as e:
            logger.error(f"Error in lorainfo command: {e}", exc_info=True)

            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="lorainfo",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    async def _get_lora_preview(self, civitai_id: int) -> Optional[str]:
        """
        Get a preview image URL for a LoRA from Civitai.

        Args:
            civitai_id: Civitai ID of the LoRA

        Returns:
            URL of the preview image, or None if not found
        """
        try:
            # Use Civitai API to get model info
            url = f"https://civitai.com/api/v1/models/{civitai_id}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Error getting model info from Civitai: {response.status}")
                        return None

                    data = await response.json()

                    # Get the first image
                    if 'modelVersions' in data and data['modelVersions']:
                        version = data['modelVersions'][0]
                        if 'images' in version and version['images']:
                            image = version['images'][0]
                            return image.get('url')

            return None
        except Exception as e:
            logger.error(f"Error getting LoRA preview: {e}")
            return None

    # Command is registered in bot.py
    async def reload_loras_command(self, interaction: discord.Interaction):
        """
        Reload the LoRA list.

        Args:
            interaction: Discord interaction
        """
        start_time = time.time()

        try:
            # Check if user has admin permissions
            if not self._check_admin(interaction):
                await interaction.response.send_message(
                    "You don't have permission to use this command.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="reload_loras",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # Reload LoRAs
            # This would normally involve scanning the LoRA directory
            # For now, we'll just reload the JSON file

            # Reload options
            await self.bot.reload_options()

            await interaction.followup.send(
                "LoRA list reloaded.",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="reload_loras",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=True
            ))

        except Exception as e:
            logger.error(f"Error in reload_loras command: {e}", exc_info=True)

            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="reload_loras",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))
