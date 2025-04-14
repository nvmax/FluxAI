"""
Discord commands for image generation.
"""

import discord
import logging
import time
import uuid
import os
import json
import random
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from discord import app_commands
from discord.ext import commands

from src.domain.models.queue_item import RequestItem, QueuePriority
from src.domain.events.event_bus import EventBus
from src.domain.events.common_events import CommandExecutedEvent
from src.application.queue.queue_service import QueueService
from src.application.content_filter.content_filter_service import ContentFilterService
from src.application.ai.ai_service import AIService
from src.infrastructure.config.config_loader import get_config
from src.presentation.discord.views.image_view import ImageControlView
from src.presentation.discord.views.prompt_modal import PromptModal
from src.presentation.discord.views.redux_modal import ReduxModal
from src.presentation.discord.views.pulid_modal import PulidModal

logger = logging.getLogger(__name__)

class ImageCommands(commands.Cog):
    """Commands for generating images"""

    async def cog_load(self):
        """Called when the cog is loaded"""
        logger.info("Image commands loaded")

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info("Image commands ready")

    def _check_channel(self, interaction: discord.Interaction) -> bool:
        """
        Check if the channel is allowed.

        Args:
            interaction: Discord interaction

        Returns:
            True if the channel is allowed, False otherwise
        """
        return self.bot.is_channel_allowed(interaction.channel_id)

    async def _process_with_enhancement(self, interaction: discord.Interaction, original_prompt: str,
                                       enhancement_level: int, resolution: str = None,
                                       upscale_factor: int = 1, seed: Optional[int] = None):
        """Process a prompt with AI enhancement"""
        start_time = time.time()

        try:
            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=False)

            # Send processing message (same as without enhancement)
            message = await interaction.followup.send(
                "🚀 Starting generation process...",
                ephemeral=False
            )

            # Initialize AI service
            ai_service = AIService()

            # Enhance the prompt with AI
            enhanced_prompt = await ai_service.enhance_prompt(original_prompt, enhancement_level)

            # Only show enhancement message if the prompt was actually enhanced (level > 1)
            if enhancement_level > 1:
                # Send a private message with the enhanced prompt
                await interaction.followup.send(
                    f"**Your prompt was enhanced:**\n\n**Original:** {original_prompt}\n\n**Enhanced:** {enhanced_prompt}",
                    ephemeral=True
                )

            # Use default resolution if not provided
            if not resolution and self.bot.resolution_options:
                resolution = self.bot.resolution_options[0]

            # Show LoRA selection view
            try:
                from src.presentation.discord.views.lora_selection_view import select_loras
                from src.domain.lora_management import LoraManager

                # Get available LoRAs
                lora_manager = LoraManager()
                available_loras = lora_manager.get_all_loras()

                # Show LoRA selection view
                selected_loras = await select_loras(interaction, available_loras)
                logger.info(f"User selected {len(selected_loras)} LoRAs: {selected_loras}")

                # If user cancelled LoRA selection, use empty list
                if selected_loras is None:
                    selected_loras = []
            except Exception as e:
                # Just log the error and continue without showing a message to the user
                logger.error(f"Error showing LoRA selection: {str(e)}", exc_info=True)
                selected_loras = []

            # Create request item
            request_uuid = str(uuid.uuid4())
            request_item = RequestItem(
                id=request_uuid,
                user_id=str(interaction.user.id),
                channel_id=str(interaction.channel_id),
                interaction_id=str(interaction.id),
                original_message_id=str(message.id),
                prompt=enhanced_prompt,
                resolution=resolution,
                loras=selected_loras,  # Use selected LoRAs
                upscale_factor=upscale_factor,
                workflow_filename=None,
                seed=seed,
                is_pulid=False
            )

            # Add to pending requests for progress updates
            self.bot.pending_requests[request_uuid] = request_item
            logger.info(f"Added request {request_uuid} to pending_requests with AI-enhanced prompt and {len(selected_loras)} LoRAs")

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
                    command_name="generate",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="generate",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=True
            ))

        except Exception as e:
            logger.error(f"Error in enhanced prompt processing: {e}", exc_info=True)

            await interaction.followup.send(
                f"An error occurred while enhancing your prompt: {str(e)}",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="generate",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    def __init__(self, bot):
        """
        Initialize image commands.

        Args:
            bot: Discord bot instance
        """
        super().__init__()
        self.bot = bot
        self.event_bus = EventBus()

        # The comfy command is now registered directly in the bot.py file
    async def _comfy_callback(self,
                              interaction: discord.Interaction,
                              prompt: str,
                              resolution: str,
                              upscale_factor: int = 1,
                              seed: Optional[int] = None):
        """
        Generate an image from a prompt.

        Args:
            interaction: Discord interaction
            prompt: Prompt to generate an image from
            resolution: Resolution for the output image
            upscale: Upscale factor
        """
        start_time = time.time()

        try:
            # Check if channel is allowed
            if not self._check_channel(interaction):
                await interaction.response.send_message(
                    "This command can only be used in specific channels.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="generate",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # If no prompt provided, show prompt modal
            if not prompt:
                # Show the modal for prompt input
                modal = PromptModal(self.bot)
                if resolution:
                    modal.resolution = resolution
                if upscale_factor:
                    modal.upscale_factor = upscale_factor

                await interaction.response.send_modal(modal)

                # Record command execution (will be recorded when modal is submitted)
                return

            # Check content filter
            is_allowed, violation_type, violation_details = self.bot.content_filter_service.check_prompt(
                str(interaction.user.id),
                prompt
            )

            if not is_allowed:
                await interaction.response.send_message(
                    f"Your prompt was flagged by our content filter: {violation_details}",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="generate",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Check if prompt enhancement is enabled
            config = get_config()
            enable_prompt_enhancement = config.get('enable_prompt_enhancement', 'False').lower() == 'true'

            if enable_prompt_enhancement:
                # Create and show the enhancement modal
                from src.presentation.discord.views.enhancement_modal import EnhancementModal

                # Create a callback function to process the enhanced prompt
                async def process_enhanced_prompt(interaction, original_prompt, enhancement_level):
                    await self._process_with_enhancement(interaction, original_prompt, enhancement_level, resolution, upscale_factor, seed)

                enhancement_modal = EnhancementModal(
                    original_prompt=prompt,
                    negative_prompt=None,
                    on_submit_callback=process_enhanced_prompt
                )
                await interaction.response.send_modal(enhancement_modal)
                return

            # If enhancement is disabled, proceed normally
            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=False)

            # Use default resolution if not provided
            if not resolution and self.bot.resolution_options:
                resolution = self.bot.resolution_options[0]

            # Create processing message
            message = await interaction.followup.send(
                "🚀 Starting generation process...",
                ephemeral=False
            )

            # Create request item
            request_item = RequestItem(
                id=str(uuid.uuid4()),
                user_id=str(interaction.user.id),
                channel_id=str(interaction.channel_id),
                interaction_id=str(interaction.id),
                original_message_id=str(message.id),
                prompt=prompt,
                resolution=resolution,
                loras=[],  # Will be selected in the UI
                upscale_factor=upscale_factor,
                workflow_filename=None,
                seed=seed,
                is_pulid=False
            )

            # Add to queue
            success, request_id, message = await self.bot.queue_service.add_request(
                request_item,
                QueuePriority.NORMAL
            )

            # Store in pending requests for progress updates
            if success:
                request_item.id = request_id
                self.bot.pending_requests[request_id] = request_item
                logger.info(f"Added request {request_id} to pending_requests")

            if not success:
                await interaction.followup.send(
                    f"Failed to add request to queue: {message}",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="generate",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="comfy",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=True
            ))

        except Exception as e:
            logger.error(f"Error in generate command: {e}", exc_info=True)

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
                command_name="comfy",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    # Command is registered in bot.py
    async def redux_command(self, interaction: discord.Interaction, resolution: str):
        """
        Generate an image using two reference images.

        Args:
            interaction: Discord interaction
            resolution: Resolution for the output image (required)
        """
        start_time = time.time()

        try:
            # Check if channel is allowed
            if not self._check_channel(interaction):
                await interaction.response.send_message(
                    "This command can only be used in specific channels.",
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

                return

            # Resolution is now required, so we don't need to set a default

            # Show the modal for image upload and strength settings
            modal = ReduxModal(self.bot, resolution)
            await interaction.response.send_modal(modal)

            # Record command execution (will be recorded when modal is submitted)

        except Exception as e:
            logger.error(f"Error in redux command: {e}", exc_info=True)

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

    # Command is registered in bot.py
    async def pulid_command(self,
                           interaction: discord.Interaction,
                           prompt: str,
                           resolution: str,
                           strength: float = 0.5,
                           upscale_factor: int = 1):
        """
        Generate an image using a reference image and a prompt.

        Args:
            interaction: Discord interaction
            prompt: Prompt to guide the image generation
            resolution: Resolution for the output image
            strength: Strength of the reference image (0.1-1.0)
            upscale_factor: Upscale factor for the output image (1-3)
        """
        start_time = time.time()

        try:
            # Check if channel is allowed
            if not self._check_channel(interaction):
                await interaction.response.send_message(
                    "This command can only be used in specific channels.",
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

            # Validate strength
            if not (0.1 <= strength <= 1.0):
                await interaction.response.send_message(
                    "Strength value must be between 0.1 and 1.0.",
                    ephemeral=True
                )
                return

            # Resolution is now required, so we don't need to set a default

            # Check content filter
            is_allowed, violation_type, violation_details = self.bot.content_filter_service.check_prompt(
                str(interaction.user.id),
                prompt
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

            # Defer the response
            await interaction.response.defer(ephemeral=False)

            # Send message asking for image upload
            message = await interaction.followup.send(
                f"🚀 PuLID Image Generation**\n\nPrompt: {prompt}\nResolution: {resolution}\nStrength: {strength}\n\nPlease upload a reference image to start the process.",
                ephemeral=False
            )

            # Define check function for the image upload
            def check_message(m):
                return (m.author.id == interaction.user.id and
                        m.channel.id == interaction.channel.id and
                        len(m.attachments) > 0)

            try:
                # Wait for image upload
                uploaded_message = await self.bot.wait_for('message', timeout=60.0, check=check_message)

                # Get the first attachment
                attachment = uploaded_message.attachments[0]

                # Check if it's an image
                if not attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    await interaction.followup.send(
                        "Please upload a valid image file (PNG, JPG, JPEG, or WEBP).",
                        ephemeral=True
                    )
                    return

                # Read the image data
                image_data = await attachment.read()
                request_id = str(uuid.uuid4())
                image_filename = f"pulid_{request_id}_{attachment.filename}"

                # Save the image to a temporary file
                image_dir = os.path.join('output', request_id)
                os.makedirs(image_dir, exist_ok=True)

                image_path = os.path.join(image_dir, image_filename)
                with open(image_path, "wb") as f:
                    f.write(image_data)

                # Delete the user's message to keep the channel clean
                try:
                    await uploaded_message.delete()
                except Exception as e:
                    logger.warning(f"Could not delete user's image upload message: {e}")

                # Update the message
                await message.edit(content=f"âœ… Image received! Processing with prompt: {prompt}")

                # Import the LoraSelectionView
                from src.presentation.discord.views.lora_selection_view import LoraSelectionView
                from src.domain.lora_management import LoraManager

                # Get available LoRAs
                lora_manager = LoraManager()
                available_loras = lora_manager.get_all_loras()

                # Create a view for LoRA selection
                view = discord.ui.View()

                # Add a button to select LoRAs
                select_loras_button = discord.ui.Button(label="Select LoRAs", style=discord.ButtonStyle.primary)

                # Define callback for the select LoRAs button
                async def select_loras_callback(button_interaction):
                    # Create a LoraSelectionView
                    lora_view = LoraSelectionView(available_loras)

                    # Send a message with the view
                    lora_message = await button_interaction.response.send_message(
                        "Select LoRAs to use with your image:",
                        view=lora_view,
                        ephemeral=True
                    )

                    # Store the message in the view for cleanup
                    lora_view.message = await button_interaction.original_response()

                    # Wait for the view to complete
                    await lora_view.wait()

                    # Get the selected LoRAs
                    selected_loras = lora_view.selected_loras if lora_view.has_confirmed else []

                    # Make sure the message is deleted if it wasn't already
                    try:
                        await lora_view.message.delete()
                    except Exception as e:
                        logger.debug(f"LoRA selection message already deleted or couldn't be deleted: {e}")

                    # Process the image with the selected LoRAs
                    await process_image(selected_loras)

                select_loras_button.callback = select_loras_callback
                view.add_item(select_loras_button)

                # Add a button to process without LoRAs
                process_button = discord.ui.Button(label="Process Without LoRAs", style=discord.ButtonStyle.secondary)

                # Define callback for the process button
                async def process_button_callback(button_interaction):
                    await button_interaction.response.defer()
                    await process_image([])

                process_button.callback = process_button_callback
                view.add_item(process_button)

                # Update the message with the buttons
                await message.edit(
                    content=f"⚙️ Image received! Would you like to add LoRAs to your generation?\n\nPrompt: {prompt}\nResolution: {resolution}\nStrength: {strength}\nUpscale: {upscale_factor}x",
                    view=view
                )

                # Define the process_image function
                async def process_image(selected_loras):
                    try:
                        # Update the message
                        await message.edit(content="ðŸ”„ Processing your image...", view=None)

                        # Load PuLID workflow
                        try:
                            # Try to load directly from config directory
                            workflow_path = os.path.join('config', 'PulidFluxDev.json')
                            if os.path.exists(workflow_path):
                                with open(workflow_path, 'r') as f:
                                    workflow = json.load(f)
                                logger.info(f"Loaded PuLID workflow from {workflow_path}")
                            else:
                                # Fall back to config manager
                                workflow = self.bot.config.load_json(self.bot.config.pulid_workflow)
                        except Exception as e:
                            logger.error(f"Error loading PuLID workflow: {e}")
                            await message.edit(content=f"Error loading PuLID workflow: {str(e)}")
                            return

                        # Update workflow
                        if hasattr(self.bot, 'image_generation_service') and self.bot.image_generation_service:
                            # Use the comfyui_service from the image_generation_service
                            workflow = self.bot.image_generation_service.comfyui_service.update_reduxprompt_workflow(
                                workflow=workflow,
                                image_path=image_path,
                                prompt=prompt,
                                strength=strength,
                                resolution=resolution,
                                loras=selected_loras,
                                upscale_factor=upscale_factor
                            )
                        else:
                            # Fallback: Create a new ComfyUIService instance
                            from src.infrastructure.comfyui.comfyui_service import ComfyUIService
                            comfyui_service = ComfyUIService()
                            workflow = comfyui_service.update_reduxprompt_workflow(
                                workflow=workflow,
                                image_path=image_path,
                                prompt=prompt,
                                strength=strength,
                                resolution=resolution,
                                loras=selected_loras,
                                upscale_factor=upscale_factor
                            )

                        # Save workflow to output directory
                        workflow_filename = os.path.join('output', f"pulid_{request_id}.json")
                        self.bot.config.save_json(workflow_filename, workflow)

                        # Create request item
                        request_item = RequestItem(
                            id=request_id,
                            user_id=str(interaction.user.id),
                            channel_id=str(interaction.channel_id),
                            interaction_id=str(interaction.id),
                            original_message_id=str(message.id),
                            prompt=prompt,
                            resolution=resolution,
                            loras=selected_loras,
                            upscale_factor=upscale_factor,
                            workflow_filename=workflow_filename,
                            seed=None,
                            is_pulid=True
                        )

                        # Explicitly set the is_pulid attribute to ensure it's properly set
                        setattr(request_item, 'is_pulid', True)
                        logger.info(f"Set is_pulid=True on request_item {request_id}")

                        # Set command_name attribute for additional identification
                        setattr(request_item, 'command_name', 'pulid')
                        logger.info(f"Set command_name='pulid' on request_item {request_id}")

                        # Add to queue
                        success, queue_id, queue_message = await self.bot.queue_service.add_request(
                            request_item,
                            QueuePriority.NORMAL
                        )

                        if not success:
                            await message.edit(content=f"Failed to add request to queue: {queue_message}")
                            return

                        # Store in pending requests for progress updates
                        self.bot.pending_requests[request_id] = request_item
                        logger.info(f"Added request {request_id} to pending_requests for PuLID generation")

                    except Exception as e:
                        logger.error(f"Error processing image: {e}", exc_info=True)
                        await message.edit(content=f"Error processing image: {str(e)}")

            except asyncio.TimeoutError:
                await interaction.followup.send("Timed out waiting for image upload.", ephemeral=True)

            # Record command execution (will be recorded when modal is submitted)

        except Exception as e:
            logger.error(f"Error in pulid command: {e}", exc_info=True)

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

    async def video_command(self, interaction: discord.Interaction, prompt: str):
        """Generate a video based on a prompt.

        Args:
            interaction: Discord interaction
            prompt: Prompt for the video generation
        """
        start_time = time.time()

        try:
            # Check if channel is allowed
            if not self._check_channel(interaction):
                await interaction.response.send_message(
                    "This command can only be used in specific channels.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="video",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Check content filter
            is_allowed, violation_type, violation_details = self.bot.content_filter_service.check_prompt(
                str(interaction.user.id),
                prompt
            )

            if not is_allowed:
                await interaction.response.send_message(
                    f"Your prompt was flagged by our content filter: {violation_details}",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="video",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=False)

            # Create processing message
            message = await interaction.followup.send(
                "🚀 Starting video generation process...\n"
                f"Prompt: {prompt}\n"
                "This may take several minutes.",
                ephemeral=False
            )

            # Generate a unique workflow filename
            request_id = str(uuid.uuid4())

            # Create output directory if it doesn't exist
            os.makedirs('output', exist_ok=True)

            # Save workflow in output directory
            workflow_filename = os.path.join('output', f'Video_{request_id}.json')

            # Load and modify the video workflow
            workflow = self.bot.config.load_json('Video.json')

            # Generate random seed
            seed = random.randint(1, 2147483647)

            # We don't need to update the workflow here
            # The ComfyUIService will handle updating the workflow based on the is_video flag

            # Save the modified workflow
            self.bot.config.save_json(workflow_filename, workflow)

            # Create request item
            request_item = RequestItem(
                id=request_id,
                user_id=str(interaction.user.id),
                channel_id=str(interaction.channel_id),
                interaction_id=str(interaction.id),
                original_message_id=str(message.id),
                prompt=prompt,
                resolution="video",  # Using "video" as resolution identifier
                loras=[],  # Empty list as videos don't use LoRAs
                upscale_factor=1,  # Default value
                workflow_filename=workflow_filename,
                seed=seed,
                is_video=True
            )

            # Add to queue
            success, request_id, message_text = await self.bot.queue_service.add_request(
                request_item,
                QueuePriority.NORMAL
            )

            # Store in pending requests for progress updates
            if success:
                request_item.id = request_id
                self.bot.pending_requests[request_id] = request_item
                logger.info(f"Added request {request_id} to pending_requests for video generation")

            if not success:
                await message.edit(content=f"Failed to add request to queue: {message_text}")

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="video",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="video",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=True
            ))

        except Exception as e:
            logger.error(f"Error in video command: {e}", exc_info=True)

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
                command_name="video",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    async def sync_command(self, interaction: discord.Interaction):
        """
        Sync commands with Discord.

        Args:
            interaction: Discord interaction
        """
        start_time = time.time()

        try:
            # Check if user has admin permissions
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "You don't have permission to use this command.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="sync",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # Sync commands
            try:
                synced = await self.bot.tree.sync(guild=interaction.guild)
                await interaction.followup.send(
                    f"Synced {len(synced)} commands to this server.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="sync",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=True
                ))
            except Exception as e:
                await interaction.followup.send(
                    f"Error syncing commands: {str(e)}",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="sync",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

        except Exception as e:
            logger.error(f"Error in sync command: {e}", exc_info=True)

            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="sync",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    async def video_command(self,
                          interaction: discord.Interaction,
                          prompt: str):
        """
        Generate a video based on a prompt.

        Args:
            interaction: Discord interaction
            prompt: Prompt for the video generation
        """
        start_time = time.time()

        try:
            # Check if channel is allowed
            if not self._check_channel(interaction):
                await interaction.response.send_message(
                    "This command can only be used in specific channels.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="video",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Check content filter
            is_allowed, violation_type, violation_details = self.bot.content_filter_service.check_prompt(
                str(interaction.user.id),
                prompt
            )

            if not is_allowed:
                await interaction.response.send_message(
                    f"Your prompt was flagged by our content filter: {violation_details}",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="video",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=False)

            # Create processing message
            message = await interaction.followup.send(
                "🚀 Starting video generation process...\n"
                f"Prompt: {prompt}\n"
                "This may take several minutes.",
                ephemeral=False
            )

            # Generate a unique workflow filename
            request_id = str(uuid.uuid4())

            # Create output directory if it doesn't exist
            os.makedirs('output', exist_ok=True)

            # Save workflow in output directory
            workflow_filename = os.path.join('output', f'Video_{request_id}.json')

            # Load and modify the video workflow
            workflow = self.bot.config.load_json('Video.json')

            # Generate random seed
            seed = random.randint(1, 2147483647)

            # We don't need to update the workflow here
            # The ComfyUIService will handle updating the workflow based on the is_video flag

            # Save the modified workflow
            self.bot.config.save_json(workflow_filename, workflow)

            # Create request item
            request_item = RequestItem(
                id=request_id,
                user_id=str(interaction.user.id),
                channel_id=str(interaction.channel_id),
                interaction_id=str(interaction.id),
                original_message_id=str(message.id),
                prompt=prompt,
                resolution="video",  # Using "video" as resolution identifier
                loras=[],  # Empty list as videos don't use LoRAs
                upscale_factor=1,  # Default value
                workflow_filename=workflow_filename,
                seed=seed,
                is_video=True
            )

            # Add to queue
            success, request_id, message_text = await self.bot.queue_service.add_request(
                request_item,
                QueuePriority.NORMAL
            )

            # Store in pending requests for progress updates
            if success:
                request_item.id = request_id
                self.bot.pending_requests[request_id] = request_item
                logger.info(f"Added request {request_id} to pending_requests for video generation")

            if not success:
                await message.edit(content=f"Failed to add request to queue: {message_text}")

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="video",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="video",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=True
            ))

        except Exception as e:
            logger.error(f"Error in video command: {e}", exc_info=True)

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
                command_name="video",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    async def reduxprompt_command(self, interaction: discord.Interaction, prompt: str, resolution: str, strength: float, image_path: str):
        """Generate a video based on a prompt.

        Args:
            interaction: Discord interaction
            prompt: Prompt for the video generation
            resolution: Resolution for the output video
            strength: Strength of the reference image
            image_path: Path to the reference image
        """
        start_time = time.time()

        try:
            # Check if channel is allowed
            if not self._check_channel(interaction):
                await interaction.response.send_message(
                    "This command can only be used in specific channels.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="reduxprompt",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Check content filter
            is_allowed, violation_type, violation_details = self.bot.content_filter_service.check_prompt(
                str(interaction.user.id),
                prompt
            )

            if not is_allowed:
                await interaction.response.send_message(
                    f"Your prompt was flagged by our content filter: {violation_details}",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="reduxprompt",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=False)

            # Create processing message
            processing_msg = await interaction.followup.send(
                "🚀 Starting video generation process...\n"
                f"Prompt: {prompt}\n"
                f"Resolution: {resolution}\n"
                f"Strength: {strength}\n"
                "This may take several minutes.",
                ephemeral=False
            )

            # Generate a unique workflow filename
            request_id = str(uuid.uuid4())

            # Create output directory if it doesn't exist
            os.makedirs('output', exist_ok=True)

            # Save workflow in output directory
            workflow_filename = os.path.join('output', f'Video_{request_id}.json')

            # Load and modify the video workflow
            workflow = self.bot.config.load_json('Video.json')

            # Generate random seed
            seed = random.randint(1, 2147483647)

            # We don't need to update the workflow here
            # The ComfyUIService will handle updating the workflow based on the is_video flag

            # Save the modified workflow
            self.bot.config.save_json(workflow_filename, workflow)

            # Create request item
            request_item = RequestItem(
                id=request_id,
                user_id=str(interaction.user.id),
                channel_id=str(interaction.channel_id),
                interaction_id=str(interaction.id),
                original_message_id=str(processing_msg.id),
                prompt=prompt,
                resolution=resolution,
                loras=[],  # Empty list as videos don't use LoRAs
                upscale_factor=1,  # Default value
                workflow_filename=workflow_filename,
                seed=seed,
                is_video=True,
                is_reduxprompt=True,
                strength=strength,
                image_path=image_path
            )

            # Add to queue
            success, request_id, message = await self.bot.queue_service.add_request(
                request_item,
                QueuePriority.NORMAL
            )

            # Store in pending requests for progress updates
            if success:
                request_item.id = request_id
                self.bot.pending_requests[request_id] = request_item
                logger.info(f"Added request {request_id} to pending_requests for video generation")

            if not success:
                await processing_msg.edit(content=f"Failed to add request to queue: {message}")

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="reduxprompt",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="reduxprompt",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=True
            ))

        except asyncio.TimeoutError:
            await interaction.followup.send(
                "Timed out waiting for image upload",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="reduxprompt",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

        except Exception as e:
            logger.error(f"Error in reduxprompt command: {e}", exc_info=True)

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
                command_name="reduxprompt",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))
