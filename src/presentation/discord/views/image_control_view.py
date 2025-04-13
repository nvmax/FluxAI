import discord
import logging
import uuid
import random
from discord.ui import View
from typing import Optional, List, Dict, Any

from src.domain.models.queue_item import RequestItem, QueueItem, QueuePriority
from src.application.image_generation.image_generation_service import ImageGenerationService
from src.presentation.discord.views.options_modal import OptionsView

logger = logging.getLogger(__name__)

class ImageControlView(View):
    # Make this view persistent so it works after bot restarts
    timeout = None

    def __init__(self, bot=None, original_prompt: Optional[str] = None,
                 image_filename: Optional[str] = None,
                 original_resolution: Optional[str] = None,
                 original_loras: Optional[List[str]] = None,
                 original_upscale_factor: Optional[int] = None,
                 original_seed: Optional[int] = None):
        super().__init__()
        self.bot = bot
        self.original_prompt = original_prompt
        self.image_filename = image_filename
        self.original_resolution = original_resolution
        self.original_loras = original_loras if original_loras else []
        self.original_upscale_factor = original_upscale_factor if original_upscale_factor else 1
        self.original_seed = original_seed

        # Buttons are added via decorators

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is valid"""
        # Only allow the original user to use these buttons
        if hasattr(self, 'user_id') and interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "You cannot use these controls.",
                ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        """Called when the view times out"""
        # Remove buttons when the view times out
        for item in self.children:
            item.disabled = True

    # Add properties to store selected options
    @property
    def selected_resolution(self):
        return getattr(self, '_selected_resolution', self.original_resolution)

    @selected_resolution.setter
    def selected_resolution(self, value):
        self._selected_resolution = value

    @property
    def selected_loras(self):
        return getattr(self, '_selected_loras', self.original_loras)

    @selected_loras.setter
    def selected_loras(self, value):
        self._selected_loras = value

    @property
    def selected_upscale_factor(self):
        return getattr(self, '_selected_upscale_factor', self.original_upscale_factor)

    @selected_upscale_factor.setter
    def selected_upscale_factor(self, value):
        self._selected_upscale_factor = value

    @discord.ui.button(label="Options", style=discord.ButtonStyle.primary, emoji="📘", custom_id="image:options")
    async def options_callback(self, interaction: discord.Interaction, _: discord.ui.Button):
        """Callback for the options button - shows options view"""
        try:
            # Get the bot instance if not already set
            if not self.bot:
                self.bot = interaction.client

            # If we don't have the original data (after restart), try to get it from the database
            if not self.original_prompt or not self.original_resolution:
                # Get the message ID
                message_id = str(interaction.message.id)

                # Get the image repository
                image_repository = self.bot.container.resolve('ImageRepository')

                # Get the generation data
                generation_data = await image_repository.get_generation_by_message_id(message_id)

                if generation_data:
                    # Update the view with the data from the database
                    self.original_prompt = generation_data['prompt']
                    self.original_resolution = generation_data['resolution']
                    self.original_loras = generation_data['loras']
                    self.original_upscale_factor = generation_data['upscale_factor']
                    self.original_seed = generation_data['seed']
                    logger.info(f"Retrieved generation data for message {message_id} from database")
                else:
                    logger.warning(f"Could not find generation data for message {message_id} in database")
                    await interaction.response.send_message("Could not find the original generation data. Please try regenerating the image.", ephemeral=True)
                    return

            # Create the options view
            options_view = OptionsView(
                bot=self.bot,
                original_prompt=self.original_prompt,
                original_resolution=self.original_resolution,
                original_loras=self.original_loras,
                original_upscale_factor=self.original_upscale_factor,
                original_seed=self.original_seed,
                parent_view=self
            )

            # Create initial embed
            embed = discord.Embed(
                title="Image Options",
                description="Select options for regenerating the image:",
                color=discord.Color.blue()
            )

            # Add current selections
            embed.add_field(name="Resolution", value=self.original_resolution, inline=True)
            embed.add_field(name="Upscale Factor", value=str(self.original_upscale_factor), inline=True)

            # Add LoRAs
            lora_count = len(self.original_loras)
            lora_text = ", ".join(self.original_loras) if lora_count > 0 else "None"
            embed.add_field(name="LoRAs Selected", value=f"{lora_count} LoRA(s)", inline=True)
            embed.add_field(name="LoRA Details", value=lora_text, inline=False)

            # Send the options view to the user
            await interaction.response.send_message(embed=embed, view=options_view, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in options button: {str(e)}", exc_info=True)
            await interaction.response.send_message("An error occurred while showing options.", ephemeral=True)

    @discord.ui.button(label="Regenerate", style=discord.ButtonStyle.primary, emoji="♻️", custom_id="image:regenerate")
    async def regenerate_callback(self, interaction: discord.Interaction, _: discord.ui.Button):
        """Callback for the regenerate button"""
        try:
            await interaction.response.defer(ephemeral=False)

            # Get the bot instance if not already set
            if not self.bot:
                self.bot = interaction.client

            # If we don't have the original data (after restart), try to get it from the database
            if not self.original_prompt or not self.original_resolution:
                # Get the message ID
                message_id = str(interaction.message.id)

                # Get the image repository
                image_repository = self.bot.container.resolve('ImageRepository')

                # Get the generation data
                generation_data = await image_repository.get_generation_by_message_id(message_id)

                if generation_data:
                    # Update the view with the data from the database
                    self.original_prompt = generation_data['prompt']
                    self.original_resolution = generation_data['resolution']
                    self.original_loras = generation_data['loras']
                    self.original_upscale_factor = generation_data['upscale_factor']
                    self.original_seed = generation_data['seed']
                    logger.info(f"Retrieved generation data for message {message_id} from database")
                else:
                    logger.warning(f"Could not find generation data for message {message_id} in database")
                    await interaction.followup.send("Could not find the original generation data. Please try creating a new image.", ephemeral=True)
                    return

            # Generate a new request ID and seed
            request_uuid = str(uuid.uuid4())
            new_seed = random.randint(1, 2147483647)  # Simple random seed generation

            # Send a message indicating regeneration is in progress
            new_message = await interaction.followup.send("🔄 Regenerating image...")

            # Create a request item

            request_item = RequestItem(
                id=request_uuid,
                user_id=str(interaction.user.id),
                channel_id=str(interaction.channel.id),
                interaction_id=str(interaction.id),
                original_message_id=str(new_message.id),
                prompt=self.original_prompt,
                resolution=self.original_resolution,
                loras=self.original_loras,
                upscale_factor=self.original_upscale_factor,
                workflow_filename=None,  # Will be created by the image generation service
                seed=new_seed
            )

            # Add to pending requests for progress updates
            self.bot.pending_requests[request_uuid] = request_item
            logger.info(f"Added request {request_uuid} to pending_requests")

            # Create a QueueItem to wrap the RequestItem
            queue_item = QueueItem(
                request_id=request_uuid,
                request_item=request_item,
                priority=QueuePriority.NORMAL,
                user_id=str(interaction.user.id)
            )

            # Use the bot's image generation service
            if hasattr(self.bot, 'image_generation_service') and self.bot.image_generation_service:
                # Use the existing service from the bot
                await self.bot.image_generation_service.generate_image(queue_item)
            else:
                # If not available, try to create a new service with dependencies
                from src.infrastructure.comfyui.comfyui_service import ComfyUIService
                from src.application.analytics.analytics_service import AnalyticsService
                from src.infrastructure.config.config_manager import ConfigManager

                # Create required services
                comfyui_service = ComfyUIService()
                analytics_service = AnalyticsService()
                config_manager = ConfigManager()

                # Create the image generation service
                image_service = ImageGenerationService(
                    comfyui_service=comfyui_service,
                    analytics_service=analytics_service,
                    config_manager=config_manager,
                    bot=self.bot
                )

                # Process the request
                await image_service.generate_image(queue_item)

        except Exception as e:
            logger.error(f"Error in regenerate button: {str(e)}", exc_info=True)
            await interaction.followup.send("An error occurred while regenerating the image.", ephemeral=True)

    async def regenerate_with_options(self, interaction: discord.Interaction):
        """Regenerate the image with the selected options"""
        try:
            # Generate a new request ID and seed
            request_uuid = str(uuid.uuid4())
            new_seed = random.randint(1, 2147483647)  # Simple random seed generation

            # Send a message indicating regeneration is in progress
            new_message = await interaction.followup.send("🔄 Regenerating image with new options...", ephemeral=False)

            # Create a request item with the selected options
            request_item = RequestItem(
                id=request_uuid,
                user_id=str(interaction.user.id),
                channel_id=str(interaction.channel.id),
                interaction_id=str(interaction.id),
                original_message_id=str(new_message.id),
                prompt=self.original_prompt,
                resolution=self.selected_resolution,  # Use selected resolution
                loras=self.selected_loras,  # Use selected LoRAs
                upscale_factor=self.selected_upscale_factor,  # Use selected upscale factor
                workflow_filename=None,  # Will be created by the image generation service
                seed=new_seed
            )

            # Add to pending requests for progress updates
            self.bot.pending_requests[request_uuid] = request_item
            logger.info(f"Added request {request_uuid} to pending_requests with custom options")

            # Create a QueueItem to wrap the RequestItem
            queue_item = QueueItem(
                request_id=request_uuid,
                request_item=request_item,
                priority=QueuePriority.NORMAL,
                user_id=str(interaction.user.id)
            )

            # Use the bot's image generation service
            if hasattr(self.bot, 'image_generation_service') and self.bot.image_generation_service:
                # Use the existing service from the bot
                await self.bot.image_generation_service.generate_image(queue_item)
            else:
                # If not available, try to create a new service with dependencies
                from src.infrastructure.comfyui.comfyui_service import ComfyUIService
                from src.application.analytics.analytics_service import AnalyticsService
                from src.infrastructure.config.config_manager import ConfigManager

                # Create required services
                comfyui_service = ComfyUIService()
                analytics_service = AnalyticsService()
                config_manager = ConfigManager()

                # Create the image generation service
                image_service = ImageGenerationService(
                    comfyui_service=comfyui_service,
                    analytics_service=analytics_service,
                    config_manager=config_manager,
                    bot=self.bot
                )

                # Process the request
                await image_service.generate_image(queue_item)

            # Send a confirmation message
            await interaction.followup.send(
                "Your image is being generated with the selected options.",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error in regenerate with options: {str(e)}", exc_info=True)
            await interaction.followup.send("An error occurred while regenerating the image with options.", ephemeral=True)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="image:delete")
    async def delete_callback(self, interaction: discord.Interaction, _: discord.ui.Button):
        """Callback for the delete button"""
        try:
            # Use defer without ephemeral to avoid any visible response
            await interaction.response.defer(ephemeral=False, thinking=False)

            # Check if the user is the original author or has manage messages permission
            message = interaction.message
            is_author = message.author.id == interaction.user.id
            has_permission = interaction.user.guild_permissions.manage_messages if interaction.guild else False

            if is_author or has_permission:
                await interaction.message.delete()
            else:
                # Only show a message if they don't have permission
                await interaction.followup.send("You can only delete your own messages.", ephemeral=True)
        except discord.errors.NotFound:
            logger.warning("Message already deleted")
            # No need to send a message if already deleted
        except discord.errors.Forbidden:
            logger.warning("Missing permissions to delete message")
            await interaction.followup.send("I don't have permission to delete this message.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error deleting message: {str(e)}")
            await interaction.followup.send("An error occurred while trying to delete the message.", ephemeral=True)
