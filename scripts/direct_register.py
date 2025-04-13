"""
Script to directly register commands with Discord using the Discord.py library.
"""

import asyncio
import sys
import os
import logging
import json
from pathlib import Path
import discord
from discord import app_commands

# Load resolution options from ratios.json
resolution_options = []
try:
    with open('config/ratios.json', 'r') as f:
        ratios_data = json.load(f)
        resolution_options = list(ratios_data.get('ratios', {}).keys())
except Exception as e:
    print(f"Error loading resolution options: {e}")

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import application components
from src.infrastructure.config.config_manager import ConfigManager

async def register_commands():
    """Register commands directly with Discord"""
    # Get configuration
    config = ConfigManager()

    # Create a bot instance
    intents = discord.Intents.default()
    intents.message_content = True

    bot = discord.Client(intents=intents)
    tree = app_commands.CommandTree(bot)

    # Define commands
    @tree.command(name="comfy", description="Generate an image based on a prompt")
    @app_commands.describe(
        prompt="Enter your prompt",
        resolution="Choose the resolution",
        upscale_factor="Choose upscale factor (1-4, default is 1)",
        seed="Enter a seed for reproducibility (optional)"
    )


    @app_commands.choices(resolution=[
        app_commands.Choice(name=name, value=name) for name in resolution_options
    ])
    @app_commands.choices(upscale_factor=[
        app_commands.Choice(name="1x (No upscale)", value=1),
        app_commands.Choice(name="2x", value=2),
        app_commands.Choice(name="3x", value=3),
        app_commands.Choice(name="4x", value=4)
    ])
    async def comfy_command(interaction, prompt: str, resolution: str, upscale_factor: int = 1, seed: int = None):
        await interaction.response.send_message("This is a placeholder. Use the actual bot for image generation.")

    @tree.command(name="redux", description="Generate an image using two reference images")
    @app_commands.describe(
        resolution="Choose the resolution for the output image"
    )
    async def redux_command(interaction, resolution: str = None):
        await interaction.response.send_message("This is a placeholder. Use the actual bot for image generation.")

    @tree.command(name="pulid", description="Generate an image using a reference image and a prompt")
    @app_commands.describe(
        prompt="The prompt to guide the image generation",
        resolution="Choose the resolution for the output image"
    )
    async def pulid_command(interaction, prompt: str = None, resolution: str = None):
        await interaction.response.send_message("This is a placeholder. Use the actual bot for image generation.")

    @tree.command(name="stats", description="Show usage statistics")
    @app_commands.describe(
        days="Number of days to show statistics for (default: 7)"
    )
    async def stats_command(interaction, days: int = 7):
        await interaction.response.send_message("This is a placeholder. Use the actual bot for statistics.")

    @tree.command(name="reset_stats", description="Reset usage statistics")
    async def reset_stats_command(interaction):
        await interaction.response.send_message("This is a placeholder. Use the actual bot to reset statistics.")

    @tree.command(name="lorainfo", description="Show information about available LoRAs")
    @app_commands.describe(
        lora_name="Name of the LoRA to show information for (optional)"
    )
    async def lorainfo_command(interaction, lora_name: str = None):
        await interaction.response.send_message("This is a placeholder. Use the actual bot for LoRA information.")

    @tree.command(name="queue", description="Show the current queue status")
    async def queue_command(interaction):
        await interaction.response.send_message("This is a placeholder. Use the actual bot for queue status.")

    @tree.command(name="clear_queue", description="Clear the queue")
    async def clear_queue_command(interaction):
        await interaction.response.send_message("This is a placeholder. Use the actual bot to clear the queue.")

    @tree.command(name="set_queue_priority", description="Set the priority for a user in the queue")
    @app_commands.describe(
        user="The user to set priority for",
        priority="The priority level"
    )
    @app_commands.choices(priority=[
        app_commands.Choice(name="High", value=0),
        app_commands.Choice(name="Normal", value=1),
        app_commands.Choice(name="Low", value=2)
    ])
    async def set_queue_priority_command(interaction, user: discord.User, priority: int = 1):
        await interaction.response.send_message("This is a placeholder. Use the actual bot to set queue priority.")

    @tree.command(name="add_banned_word", description="Add a word to the banned words list")
    @app_commands.describe(
        word="The word to ban"
    )
    async def add_banned_word_command(interaction, word: str):
        await interaction.response.send_message("This is a placeholder. Use the actual bot to add banned words.")

    @tree.command(name="remove_banned_word", description="Remove a word from the banned words list")
    @app_commands.describe(
        word="The word to unban"
    )
    async def remove_banned_word_command(interaction, word: str):
        await interaction.response.send_message("This is a placeholder. Use the actual bot to remove banned words.")

    @tree.command(name="list_banned_words", description="List all banned words")
    async def list_banned_words_command(interaction):
        await interaction.response.send_message("This is a placeholder. Use the actual bot to list banned words.")

    @tree.command(name="add_regex_pattern", description="Add a regex pattern to the content filter")
    @app_commands.describe(
        name="Name of the pattern",
        pattern="Regex pattern",
        description="Description of the pattern",
        severity="Severity level (high, medium, low)"
    )
    async def add_regex_pattern_command(interaction, name: str, pattern: str, description: str, severity: str = "medium"):
        await interaction.response.send_message("This is a placeholder. Use the actual bot to add regex patterns.")

    @tree.command(name="sync", description="Sync commands with Discord")
    async def sync_command(interaction):
        await interaction.response.send_message("This is a placeholder. Use the actual bot to sync commands.")

    # Login to Discord
    await bot.login(config.discord_token)

    # Sync commands
    logger.info("Syncing commands...")

    if not config.allowed_servers:
        logger.info("No allowed servers configured, syncing globally")
        synced = await tree.sync()
        logger.info(f"Synced {len(synced)} commands globally")
    else:
        for server_id in config.allowed_servers:
            try:
                guild = discord.Object(id=int(server_id))
                synced = await tree.sync(guild=guild)
                logger.info(f"Synced {len(synced)} commands to guild {server_id}")
            except Exception as e:
                logger.error(f"Failed to sync commands to guild {server_id}: {e}")

    # Close the bot
    await bot.close()

    logger.info("Command registration complete")

if __name__ == "__main__":
    asyncio.run(register_commands())
