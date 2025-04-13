import discord
import logging
from typing import List, Dict, Any
from discord.ui import View

from src.infrastructure.config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class OptionsView(View):
    def __init__(self, bot, original_prompt: str, original_resolution: str,
                 original_loras: List[str], original_upscale_factor: int,
                 original_seed: int, parent_view):
        super().__init__(timeout=300)  # 5 minute timeout
        self.bot = bot
        self.original_prompt = original_prompt
        self.original_resolution = original_resolution
        self.original_loras = original_loras if original_loras else []
        self.original_upscale_factor = original_upscale_factor
        self.original_seed = original_seed
        self.parent_view = parent_view

        # Load available resolutions and LoRAs
        self.resolutions = self._load_resolutions()
        self.loras = self._load_loras()

        # Selected values (initialize with original values)
        self.selected_resolution = original_resolution
        self.selected_loras = original_loras.copy() if original_loras else []
        self.selected_upscale_factor = original_upscale_factor

        # Pagination for LoRAs
        self.current_lora_page = 0
        self.loras_per_page = 20  # Discord allows up to 25 options, but we'll use 20 for safety
        self.total_lora_pages = (len(self.loras) + self.loras_per_page - 1) // self.loras_per_page

        # Add resolution dropdown
        self.resolution_select = discord.ui.Select(
            placeholder="Select Resolution",
            options=[
                discord.SelectOption(label=res, value=res, default=(res == original_resolution))
                for res in self.resolutions
            ],
            min_values=1,
            max_values=1,
            custom_id="resolution_select",
            row=0
        )
        self.resolution_select.callback = self.resolution_callback
        self.add_item(self.resolution_select)

        # Add LoRA dropdown with pagination
        self.update_lora_dropdown()

        # Add upscale factor label
        self.upscale_row = discord.ui.Button(
            label="Upscale Factor: " + str(original_upscale_factor),
            disabled=True,
            style=discord.ButtonStyle.secondary,
            row=2
        )
        self.add_item(self.upscale_row)

        # Add upscale factor buttons
        for i in range(1, 5):
            upscale_button = discord.ui.Button(
                label=str(i),
                style=discord.ButtonStyle.primary,
                row=2,
                custom_id=f"upscale_{i}"
            )
            upscale_button.callback = self.upscale_callback
            self.add_item(upscale_button)

        # Add pagination buttons for LoRAs if needed
        self.update_pagination_buttons()

        # Add confirm button
        confirm_button = discord.ui.Button(
            label="Regenerate with Options",
            style=discord.ButtonStyle.success,
            emoji="✅",
            row=4
        )
        confirm_button.callback = self.confirm_callback
        self.add_item(confirm_button)

    def update_lora_dropdown(self):
        """Update the LoRA dropdown with the current page of LoRAs"""
        # Remove existing LoRA dropdown if it exists
        for item in self.children.copy():
            if getattr(item, 'custom_id', None) == "lora_select":
                self.remove_item(item)

        # Get LoRAs for the current page
        start_idx = self.current_lora_page * self.loras_per_page
        end_idx = min(start_idx + self.loras_per_page, len(self.loras))
        page_loras = self.loras[start_idx:end_idx]

        # Create options for the dropdown
        options = [
            discord.SelectOption(
                label=lora["name"][:25],  # Limit label length to 25 chars
                value=lora["name"],
                default=(lora["name"] in self.selected_loras)
            )
            for lora in page_loras
        ]

        # Add the LoRA dropdown
        if options:  # Only add if there are options
            self.lora_select = discord.ui.Select(
                placeholder=f"Select LoRAs (Page {self.current_lora_page+1}/{self.total_lora_pages})",
                options=options,
                min_values=0,
                max_values=min(5, len(options)),  # Can select up to 5 or all available
                custom_id="lora_select",
                row=1
            )
            self.lora_select.callback = self.lora_callback
            self.add_item(self.lora_select)

    def update_pagination_buttons(self):
        """Update the pagination buttons based on the current page"""
        # Remove existing pagination buttons
        for item in self.children.copy():
            if getattr(item, 'custom_id', None) in ["prev_lora_page", "next_lora_page"]:
                self.remove_item(item)

        # Add pagination buttons if needed
        if self.total_lora_pages > 1:
            # Previous page button
            if self.current_lora_page > 0:
                prev_button = discord.ui.Button(
                    label="◀ Previous LoRAs",
                    style=discord.ButtonStyle.secondary,
                    custom_id="prev_lora_page",
                    row=3
                )
                prev_button.callback = self.prev_lora_page_callback
                self.add_item(prev_button)

            # Next page button
            if self.current_lora_page < self.total_lora_pages - 1:
                next_button = discord.ui.Button(
                    label="Next LoRAs ▶",
                    style=discord.ButtonStyle.secondary,
                    custom_id="next_lora_page",
                    row=3
                )
                next_button.callback = self.next_lora_page_callback
                self.add_item(next_button)

    def _load_resolutions(self) -> List[str]:
        """Load available resolutions from config"""
        try:
            config_manager = ConfigManager()
            ratios_data = config_manager.load_json("config/ratios.json")
            return list(ratios_data.get("ratios", {}).keys())
        except Exception as e:
            logger.error(f"Error loading resolutions: {str(e)}")
            return ["1:1 [1024x1024 square]"]  # Default fallback

    def _load_loras(self) -> List[Dict[str, Any]]:
        """Load available LoRAs from config"""
        try:
            config_manager = ConfigManager()
            lora_data = config_manager.load_json("config/lora.json")
            return lora_data.get("available_loras", [])
        except Exception as e:
            logger.error(f"Error loading LoRAs: {str(e)}")
            return []  # Empty list as fallback

    async def resolution_callback(self, interaction: discord.Interaction):
        """Handle resolution selection"""
        self.selected_resolution = interaction.data["values"][0]

        # Create updated embed and view
        embed = self.create_embed()
        self.update_lora_dropdown()
        self.update_pagination_buttons()

        # Update the message
        await interaction.response.edit_message(embed=embed, view=self)

    async def lora_callback(self, interaction: discord.Interaction):
        """Handle LoRA selection"""
        # Get the selected LoRAs from this page
        page_selections = interaction.data["values"]

        # Get LoRAs for the current page (to know what was deselected)
        start_idx = self.current_lora_page * self.loras_per_page
        end_idx = min(start_idx + self.loras_per_page, len(self.loras))
        page_loras = [lora["name"] for lora in self.loras[start_idx:end_idx]]

        # Remove any LoRAs from this page that aren't in the selection
        self.selected_loras = [lora for lora in self.selected_loras if lora not in page_loras]

        # Add the newly selected LoRAs
        self.selected_loras.extend(page_selections)

        # Ensure we don't exceed 5 LoRAs total
        if len(self.selected_loras) > 5:
            self.selected_loras = self.selected_loras[:5]

        # Create updated embed and view
        embed = self.create_embed()
        self.update_lora_dropdown()
        self.update_pagination_buttons()

        # Update the message
        await interaction.response.edit_message(embed=embed, view=self)

    async def upscale_callback(self, interaction: discord.Interaction):
        """Handle upscale factor selection"""
        # Extract the upscale factor from the custom_id
        custom_id = interaction.data["custom_id"]
        upscale_factor = int(custom_id.split("_")[1])
        self.selected_upscale_factor = upscale_factor

        # Update the upscale factor label
        self.upscale_row.label = f"Upscale Factor: {upscale_factor}"

        # Create updated embed and view
        embed = self.create_embed()
        self.update_lora_dropdown()
        self.update_pagination_buttons()

        # Update the message
        await interaction.response.edit_message(embed=embed, view=self)

    async def prev_lora_page_callback(self, interaction: discord.Interaction):
        """Handle previous page button click"""
        if self.current_lora_page > 0:
            self.current_lora_page -= 1
            self.update_lora_dropdown()
            self.update_pagination_buttons()

            # Create updated embed
            embed = self.create_embed()

            # Update the message
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    async def next_lora_page_callback(self, interaction: discord.Interaction):
        """Handle next page button click"""
        if self.current_lora_page < self.total_lora_pages - 1:
            self.current_lora_page += 1
            self.update_lora_dropdown()
            self.update_pagination_buttons()

            # Create updated embed
            embed = self.create_embed()

            # Update the message
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    def create_embed(self):
        """Create an embed with the current selections"""
        # Create a summary embed
        embed = discord.Embed(
            title="Image Options",
            description=f"Select options for regenerating the image (LoRA Page {self.current_lora_page + 1}/{self.total_lora_pages}):",
            color=discord.Color.blue()
        )

        # Add current selections
        embed.add_field(name="Resolution", value=self.selected_resolution, inline=True)
        embed.add_field(name="Upscale Factor", value=str(self.selected_upscale_factor), inline=True)

        # Add LoRAs
        lora_count = len(self.selected_loras)
        lora_text = ", ".join(self.selected_loras) if lora_count > 0 else "None"
        embed.add_field(name="LoRAs Selected", value=f"{lora_count}/5 LoRA(s)", inline=True)
        embed.add_field(name="LoRA Details", value=lora_text, inline=False)

        return embed

    async def confirm_callback(self, interaction: discord.Interaction):
        """Handle confirmation button click"""
        try:
            # Update the parent view with the new values
            self.parent_view.selected_resolution = self.selected_resolution
            self.parent_view.selected_loras = self.selected_loras
            self.parent_view.selected_upscale_factor = self.selected_upscale_factor

            # Create a confirmation message
            embed = discord.Embed(
                title="Options Selected",
                description="The following options will be used for regeneration:",
                color=discord.Color.green()
            )
            embed.add_field(name="Resolution", value=self.selected_resolution, inline=True)
            embed.add_field(name="Upscale Factor", value=str(self.selected_upscale_factor), inline=True)
            embed.add_field(name="LoRAs Selected", value=f"{len(self.selected_loras)}/5 LoRA(s)", inline=True)
            embed.add_field(name="LoRA Details", value=", ".join(self.selected_loras) if self.selected_loras else "None", inline=False)

            # Disable all components
            for item in self.children:
                item.disabled = True

            # Update the message
            await interaction.response.edit_message(embed=embed, view=self)

            # Call the regenerate_with_options method on the parent view
            await self.parent_view.regenerate_with_options(interaction)

        except Exception as e:
            logger.error(f"Error confirming options: {str(e)}", exc_info=True)
            await interaction.response.send_message(
                "An error occurred while processing your options.",
                ephemeral=True
            )
