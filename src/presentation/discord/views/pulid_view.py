import discord
from discord.ui import View, Button
import logging

logger = logging.getLogger(__name__)

class PulidView(View):
    """
    View for PuLID image generation results.
    Only includes a delete button.
    """

    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

        # Add delete button with a unique custom_id
        delete_button = Button(
            style=discord.ButtonStyle.danger,
            label="Delete",
            custom_id=f"pulid_delete_button"
        )
        delete_button.callback = self.delete_callback
        self.add_item(delete_button)

        logger.info(f"Initialized PulidView with user_id={user_id}")

    async def delete_callback(self, interaction: discord.Interaction):
        """
        Callback for the delete button.
        Deletes the message if the user who clicked is the one who generated the image.
        """
        # Check if the user who clicked is the one who generated the image
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't delete this image as you didn't generate it.", ephemeral=True)
            return

        try:
            # Delete the message
            await interaction.message.delete()
            logger.info(f"Message deleted by user {interaction.user.id}")
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            await interaction.response.send_message("Failed to delete the message.", ephemeral=True)
