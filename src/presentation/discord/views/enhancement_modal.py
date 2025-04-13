"""
Discord modal for prompt enhancement.
"""

import discord
import logging
from typing import Callable, Awaitable, Optional
from discord.ui import Modal, TextInput

logger = logging.getLogger(__name__)

class EnhancementModal(Modal):
    """
    Modal for selecting prompt enhancement level.
    """

    def __init__(self,
                 original_prompt: str,
                 negative_prompt: Optional[str] = None,
                 on_submit_callback: Callable[[discord.Interaction, str, int], Awaitable[None]] = None):
        """
        Initialize the enhancement modal.

        Args:
            original_prompt: The original prompt entered by the user
            negative_prompt: Optional negative prompt
            on_submit_callback: Callback function to call when the modal is submitted
        """
        super().__init__(title="Enhance Prompt (Results shown privately)")
        self.original_prompt = original_prompt
        self.negative_prompt = negative_prompt
        self.on_submit_callback = on_submit_callback

        # Add enhancement level input
        self.enhancement_level = TextInput(
            label="Level (1-10)",
            placeholder="Enter a value between 1 and 10",
            default="5",
            required=True,
            min_length=1,
            max_length=2
        )
        self.add_item(self.enhancement_level)

        # We'll just add a note in the title instead of using a disabled TextInput
        # since the disabled parameter is not supported in this version of Discord.py

    async def on_submit(self, interaction: discord.Interaction):
        """
        Handle modal submission.

        Args:
            interaction: Discord interaction
        """
        try:
            # Get enhancement level
            try:
                enhancement_level = int(self.enhancement_level.value)
                # Ensure it's between 1 and 10
                enhancement_level = max(1, min(10, enhancement_level))
            except ValueError:
                enhancement_level = 5  # Default to 5 if invalid input

            # Call the callback function if provided
            if self.on_submit_callback:
                await self.on_submit_callback(interaction, self.original_prompt, enhancement_level)
            else:
                await interaction.response.send_message(
                    f"Enhancement level set to {enhancement_level}, but no callback was provided.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in enhancement modal: {e}", exc_info=True)

            await interaction.response.send_message(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
