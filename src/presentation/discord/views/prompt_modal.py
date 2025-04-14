"""
Discord modal for entering prompts.
"""

import discord
import logging
import uuid
import time
from typing import Dict, Any, List, Optional

from discord.ui import Modal, TextInput

from src.domain.models.queue_item import RequestItem, QueuePriority
from src.domain.events.event_bus import EventBus
from src.domain.events.common_events import CommandExecutedEvent
from src.presentation.discord.views.enhancement_modal import EnhancementModal
from src.application.ai.ai_service import AIService
from src.infrastructure.config.config_loader import get_config

logger = logging.getLogger(__name__)

class PromptModal(Modal):
    """
    Modal for entering prompts.
    Used for the generate command.
    """

    def __init__(self, bot):
        """
        Initialize the prompt modal.

        Args:
            bot: Discord bot instance
        """
        super().__init__(title="Generate Image")
        self.bot = bot
        self.event_bus = EventBus()

        # Default values
        self.resolution = "512x512"
        self.upscale_factor = 1

        # Get config
        self.config = get_config()
        self.enable_prompt_enhancement = self.config.get('enable_prompt_enhancement', 'False').lower() == 'true'

        # Initialize AI service
        if self.enable_prompt_enhancement:
            self.ai_service = AIService()

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

    async def on_submit(self, interaction: discord.Interaction):
        """
        Handle modal submission.

        Args:
            interaction: Discord interaction
        """
        start_time = time.time()

        try:
            # Get prompt and negative prompt
            prompt = self.prompt_input.value
            negative_prompt = self.negative_prompt_input.value

            # Combine prompts if negative prompt is provided
            if negative_prompt:
                full_prompt = f"{prompt} ### {negative_prompt}"
            else:
                full_prompt = prompt

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
                    command_name="generate",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # If prompt enhancement is enabled, show the enhancement modal
            if self.enable_prompt_enhancement:
                # Create and show the enhancement modal
                enhancement_modal = EnhancementModal(
                    original_prompt=prompt,
                    negative_prompt=negative_prompt,
                    on_submit_callback=self.process_enhanced_prompt
                )
                await interaction.response.send_modal(enhancement_modal)
            else:
                # Process the prompt without enhancement
                await self.process_prompt(interaction, full_prompt)

        except Exception as e:
            logger.error(f"Error in prompt modal: {e}", exc_info=True)

            try:
                await interaction.followup.send(
                    f"An error occurred: {str(e)}",
                    ephemeral=True
                )
            except:
                try:
                    await interaction.response.send_message(
                        f"An error occurred: {str(e)}",
                        ephemeral=True
                    )
                except:
                    pass

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="generate",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    async def process_enhanced_prompt(self, interaction: discord.Interaction, original_prompt: str, enhancement_level: int):
        """Process a prompt with AI enhancement"""
        start_time = time.time()

        try:
            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=False)

            # Send processing message - different message based on enhancement level
            if enhancement_level == 1:
                # For level 1, don't mention enhancement since we're not enhancing
                message = await interaction.followup.send(
                    "🚀 Starting generation process...",
                    ephemeral=False
                )
            else:
                # For levels 2-10, mention the enhancement
                message = await interaction.followup.send(
                    f"🔄 Enhancing prompt (level {enhancement_level}/10) and starting generation...",
                    ephemeral=False
                )

            # Enhance the prompt with AI
            enhanced_prompt = await self.ai_service.enhance_prompt(original_prompt, enhancement_level)

            # Create request item
            request_uuid = str(uuid.uuid4())
            request_item = RequestItem(
                id=request_uuid,
                user_id=str(interaction.user.id),
                channel_id=str(interaction.channel_id),
                interaction_id=str(interaction.id),
                original_message_id=str(message.id),
                prompt=enhanced_prompt,
                resolution=self.resolution,
                loras=[],  # Will be selected in the UI
                upscale_factor=self.upscale_factor,
                workflow_filename=None,
                seed=None,
                is_pulid=False
            )

            # Add to pending requests for progress updates
            self.bot.pending_requests[request_uuid] = request_item
            logger.info(f"Added request {request_uuid} to pending_requests with AI-enhanced prompt")

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

    async def process_prompt(self, interaction: discord.Interaction, prompt: str):
        """Process a prompt without enhancement"""
        start_time = time.time()

        try:
            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=False)

            # Send processing message
            message = await interaction.followup.send(
                "🔄 Starting generation process...",
                ephemeral=False
            )

            # Create request item
            request_uuid = str(uuid.uuid4())
            request_item = RequestItem(
                id=request_uuid,
                user_id=str(interaction.user.id),
                channel_id=str(interaction.channel_id),
                interaction_id=str(interaction.id),
                original_message_id=str(message.id),
                prompt=prompt,
                resolution=self.resolution,
                loras=[],  # Will be selected in the UI
                upscale_factor=self.upscale_factor,
                workflow_filename=None,
                seed=None,
                is_pulid=False
            )

            # Add to pending requests for progress updates
            self.bot.pending_requests[request_uuid] = request_item
            logger.info(f"Added request {request_uuid} to pending_requests")

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
            logger.error(f"Error in prompt modal: {e}", exc_info=True)

            await interaction.followup.send(
                f"An error occurred: {str(e)}",
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
