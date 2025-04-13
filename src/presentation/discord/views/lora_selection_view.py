import discord
import logging
from typing import List, Dict, Any
from discord import ui, SelectOption

logger = logging.getLogger(__name__)

class PaginatedLoraSelect(ui.Select):
    """A paginated select menu for LoRAs"""

    def __init__(self, loras: List[Dict[str, Any]], page: int = 0, selected_loras: List[str] = None):
        """
        Initialize the paginated LoRA select menu.

        Args:
            loras: List of LoRA dictionaries with 'name' and 'file' keys
            page: Current page number (0-indexed)
            selected_loras: List of selected LoRA filenames
        """
        self.all_options = []
        selected_loras = selected_loras or []

        # Calculate page slicing
        loras_per_page = 20  # Discord allows up to 25 options, but we'll use 20 for safety
        start_idx = page * loras_per_page
        end_idx = min(start_idx + loras_per_page, len(loras))
        page_loras = loras[start_idx:end_idx]

        # Create options for the current page
        options = []
        for lora in page_loras:
            options.append(
                SelectOption(
                    label=lora['name'][:25],  # Limit label length to 25 chars
                    value=lora['file'],
                    default=(lora['file'] in selected_loras)
                )
            )

        total_pages = (len(loras) - 1) // loras_per_page + 1
        super().__init__(
            placeholder=f"Select LoRAs (Page {page + 1}/{total_pages})",
            min_values=0,
            max_values=len(options),
            options=options
        )


class LoraSelectionView(ui.View):
    """A view for selecting LoRAs with pagination"""

    def __init__(self, loras: List[Dict[str, Any]], timeout: int = 300):
        """
        Initialize the LoRA selection view.

        Args:
            loras: List of LoRA dictionaries with 'name' and 'file' keys
            timeout: View timeout in seconds
        """
        super().__init__(timeout=timeout)
        self.loras = loras
        self.current_page = 0
        self.selected_loras = []
        self.has_confirmed = False
        self.loras_per_page = 20
        self.total_pages = (len(loras) - 1) // self.loras_per_page + 1
        self.message = None

        # Initialize the view
        self.update_view()

    async def on_timeout(self):
        """Handle view timeout by deleting the message"""
        if self.message:
            try:
                await self.message.delete()
            except Exception as e:
                logger.warning(f"Could not delete LoRA selection message on timeout: {e}")
                try:
                    # Try to update the message instead of deleting it
                    await self.message.edit(content="Selection timed out. You can dismiss this message.", view=None)
                except Exception:
                    pass
        self.stop()

    def update_view(self):
        """Update the view with current selections and pagination"""
        # Clear existing items
        self.clear_items()

        # Add LoRA select menu
        self.lora_select = PaginatedLoraSelect(
            self.loras,
            self.current_page,
            self.selected_loras
        )
        self.lora_select.callback = self.lora_select_callback
        self.add_item(self.lora_select)

        # Add pagination buttons if needed
        if self.total_pages > 1:
            # Previous page button
            if self.current_page > 0:
                prev_button = ui.Button(
                    label="◀ Previous",
                    style=discord.ButtonStyle.secondary,
                    custom_id="prev_page",
                    row=1
                )
                prev_button.callback = self.prev_page_callback
                self.add_item(prev_button)

            # Page indicator
            page_indicator = ui.Button(
                label=f"Page {self.current_page + 1}/{self.total_pages}",
                style=discord.ButtonStyle.secondary,
                disabled=True,
                custom_id="page_indicator",
                row=1
            )
            self.add_item(page_indicator)

            # Next page button
            if self.current_page < self.total_pages - 1:
                next_button = ui.Button(
                    label="Next ▶",
                    style=discord.ButtonStyle.secondary,
                    custom_id="next_page",
                    row=1
                )
                next_button.callback = self.next_page_callback
                self.add_item(next_button)

        # Add confirm button
        confirm_button = ui.Button(
            label=f"Confirm ({len(self.selected_loras)} LoRAs)",
            style=discord.ButtonStyle.success,
            custom_id="confirm",
            row=2
        )
        confirm_button.callback = self.confirm_callback
        self.add_item(confirm_button)

        # Add cancel button
        cancel_button = ui.Button(
            label="Cancel",
            style=discord.ButtonStyle.danger,
            custom_id="cancel",
            row=2
        )
        cancel_button.callback = self.cancel_callback
        self.add_item(cancel_button)

    async def lora_select_callback(self, interaction: discord.Interaction):
        """Handle LoRA selection"""
        # Get the selected LoRAs from this page
        page_selections = self.lora_select.values

        # Get LoRAs for the current page
        start_idx = self.current_page * self.loras_per_page
        end_idx = min(start_idx + self.loras_per_page, len(self.loras))
        page_loras = [lora['file'] for lora in self.loras[start_idx:end_idx]]

        # Remove any LoRAs from this page that aren't in the selection
        self.selected_loras = [lora for lora in self.selected_loras if lora not in page_loras]

        # Add the newly selected LoRAs
        self.selected_loras.extend(page_selections)

        # Update the view
        self.update_view()

        await interaction.response.edit_message(view=self)

    async def prev_page_callback(self, interaction: discord.Interaction):
        """Handle previous page button click"""
        self.current_page = max(0, self.current_page - 1)
        self.update_view()
        await interaction.response.edit_message(view=self)

    async def next_page_callback(self, interaction: discord.Interaction):
        """Handle next page button click"""
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        self.update_view()
        await interaction.response.edit_message(view=self)

    async def confirm_callback(self, interaction: discord.Interaction):
        """Handle confirm button click"""
        self.has_confirmed = True
        # Delete the entire message to completely remove it from Discord
        try:
            # First try to delete using the stored message reference
            if self.message:
                await self.message.delete()
            # If that fails or message isn't stored, try using the interaction message
            else:
                await interaction.message.delete()
        except Exception as e:
            # If we can't delete the message, at least remove the view
            logger.warning(f"Could not delete LoRA selection message: {e}")
            try:
                await interaction.response.edit_message(view=None, content="Selection complete. You can dismiss this message.")
            except Exception:
                pass
        self.stop()

    async def cancel_callback(self, interaction: discord.Interaction):
        """Handle cancel button click"""
        self.has_confirmed = False
        # Delete the entire message to completely remove it from Discord
        try:
            # First try to delete using the stored message reference
            if self.message:
                await self.message.delete()
            # If that fails or message isn't stored, try using the interaction message
            else:
                await interaction.message.delete()
        except Exception as e:
            # If we can't delete the message, at least remove the view
            logger.warning(f"Could not delete LoRA selection message: {e}")
            try:
                await interaction.response.edit_message(view=None, content="Selection cancelled. You can dismiss this message.")
            except Exception:
                pass
        self.stop()


async def select_loras(interaction: discord.Interaction, loras: List[Dict[str, Any]]) -> List[str]:
    """
    Show a LoRA selection view and return the selected LoRAs.

    Args:
        interaction: The Discord interaction
        loras: List of LoRA dictionaries with 'name' and 'file' keys

    Returns:
        List of selected LoRA filenames, or empty list if cancelled
    """
    # Create the view
    view = LoraSelectionView(loras)

    # Send the message with the view - use a minimal message
    message = await interaction.followup.send(
        "Select LoRAs:",  # Minimal message
        view=view,
        ephemeral=True
    )

    # Store the message in the view for cleanup
    view.message = message

    # Wait for the view to be completed
    await view.wait()

    # If the view didn't delete the message (e.g., timeout), delete it now
    try:
        await message.delete()
    except Exception as e:
        # Message might already be deleted by the view callbacks
        logger.debug(f"LoRA selection message already deleted or couldn't be deleted: {e}")
        try:
            # Try to update the message instead of deleting it
            await message.edit(content="Selection complete. You can dismiss this message.", view=None)
        except Exception:
            pass

    # Return the selected LoRAs if confirmed, otherwise empty list
    return view.selected_loras if view.has_confirmed else []
