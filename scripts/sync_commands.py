"""
Script to force sync commands with Discord.
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import Discord components
import discord
from discord import app_commands

# Import application components
from src.infrastructure.config.config_manager import ConfigManager

async def sync_commands():
    """Sync commands with Discord"""
    # Get configuration
    config = ConfigManager()
    
    # Create a bot instance
    intents = discord.Intents.default()
    intents.message_content = True
    
    bot = discord.Client(intents=intents)
    tree = app_commands.CommandTree(bot)
    
    # Define a simple command for testing
    @tree.command(name="ping", description="Ping the bot")
    async def ping_command(interaction: discord.Interaction):
        await interaction.response.send_message("Pong!")
    
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
    
    logger.info("Command sync complete")

if __name__ == "__main__":
    asyncio.run(sync_commands())
