import discord
import logging
import uuid
import random
from discord.ui import View
from src.domain.models.queue_item import RequestItem, QueuePriority

logger = logging.getLogger(__name__)

class VideoControlView(View):
    """
    View for displaying generated videos.
    Provides buttons for regenerating and deleting, but not options.
    """
    # Make this view persistent so it works after bot restarts
    timeout = None

    def __init__(self, bot=None, original_prompt=None, video_filename=None, original_seed=None):
        """
        Initialize the video control view.

        Args:
            bot: Discord bot instance
            original_prompt: The prompt used to generate the video
            video_filename: The filename of the generated video
            original_seed: The seed used to generate the video
        """
        super().__init__()
        self.bot = bot
        self.original_prompt = original_prompt
        self.video_filename = video_filename
        self.original_seed = original_seed

    @discord.ui.button(label="Regenerate", style=discord.ButtonStyle.primary, emoji="♻️", custom_id="video:regenerate")
    async def regenerate_callback(self, interaction: discord.Interaction, _: discord.ui.Button):
        """
        Handle regenerate button click.

        Args:
            interaction: Discord interaction
        """
        await interaction.response.defer(ephemeral=True)

        try:
            # Get the bot instance if not already set
            if not self.bot:
                self.bot = interaction.client

            # Check if the bot has a queue service
            if not hasattr(self.bot, 'queue_service') or not self.bot.queue_service:
                logger.error("Bot does not have a queue service")
                await interaction.followup.send(
                    "Error: Bot is not properly configured. Please contact an administrator.",
                    ephemeral=True
                )
                return

            # If we don't have the original prompt or seed (after restart), use defaults
            if not self.original_prompt:
                self.original_prompt = "A cat jumping off a chair"  # Default prompt
                logger.info(f"Using default prompt after bot restart: {self.original_prompt}")

            if not self.original_seed:
                self.original_seed = 1234567890  # Default seed
                logger.info(f"Using default seed after bot restart: {self.original_seed}")

            # Send a message indicating regeneration is in progress
            new_message = await interaction.followup.send("🔄 Regenerating video...")

            # Generate a new request ID
            request_uuid = str(uuid.uuid4())

            # Generate a new random seed
            new_seed = random.randint(1, 2147483647)
            logger.info(f"Regenerating video with new seed: {new_seed} (original seed was: {self.original_seed})")

            # Create a new request item
            request_item = RequestItem(
                id=request_uuid,
                user_id=str(interaction.user.id),
                channel_id=str(interaction.channel_id),
                interaction_id=str(interaction.id),
                original_message_id=str(new_message.id),
                prompt=self.original_prompt,
                resolution="512x512",  # Default for video
                loras=[],  # No LoRAs for video
                upscale_factor=1,  # No upscale for video
                seed=new_seed,  # Use the new random seed
                is_video=True,
                workflow_filename="config/Video.json"  # Use the video workflow
            )

            # Set the video flag
            request_item.is_video = True

            # Queue item will be created by the queue service

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
            else:
                logger.error(f"Failed to add request to queue: {message}")
                await interaction.followup.send(f"Error: {message}", ephemeral=True)
                return

            # Send confirmation
            await interaction.followup.send(
                f"✅ Your video is being regenerated with a new seed ({new_seed}) and the prompt:\n```{self.original_prompt}```\nYou'll see a new message when it's ready.",
                ephemeral=True
            )

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error regenerating video: {str(e)}\n{error_details}")
            await interaction.followup.send(
                f"An error occurred while regenerating: {str(e)}",
                ephemeral=True
            )

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="video:delete")
    async def delete_callback(self, interaction: discord.Interaction, _: discord.ui.Button):
        """
        Handle delete button click.

        Args:
            interaction: Discord interaction
        """
        try:
            # Use defer without ephemeral to avoid any visible response
            await interaction.response.defer(ephemeral=False, thinking=False)

            # Check if the user is the original author or has manage messages permission
            message = interaction.message
            is_author = message.author.id == interaction.user.id
            has_permission = interaction.user.guild_permissions.manage_messages if interaction.guild else False

            if is_author or has_permission:
                await message.delete()
            else:
                # Only show a message if they don't have permission
                await interaction.followup.send(
                    "You can only delete your own messages.",
                    ephemeral=True
                )
        except discord.errors.NotFound:
            logger.warning("Message already deleted")
            # No need to send a message if already deleted
        except discord.errors.Forbidden:
            logger.warning("Missing permissions to delete message")
            await interaction.followup.send("I don't have permission to delete this message.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error deleting message: {str(e)}")
            # No need to send a message for other errors
