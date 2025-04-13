"""
Discord commands for queue management.
"""

import discord
import logging
import time
from typing import Dict, Any, List, Optional
from discord import app_commands
from discord.ext import commands

from src.domain.models.queue_item import QueuePriority
from src.domain.events.event_bus import EventBus
from src.domain.events.common_events import CommandExecutedEvent

logger = logging.getLogger(__name__)

class QueueCommands(commands.Cog):
    """Commands for managing the queue"""

    def __init__(self, bot):
        """
        Initialize queue commands.

        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.event_bus = EventBus()

    async def cog_load(self):
        """Called when the cog is loaded"""
        logger.info("Queue commands loaded")

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info("Queue commands ready")

    def _check_admin(self, interaction: discord.Interaction) -> bool:
        """
        Check if the user has admin permissions.

        Args:
            interaction: Discord interaction

        Returns:
            True if the user has admin permissions, False otherwise
        """
        if not interaction.guild:
            return False

        # Check if user has admin permissions
        if interaction.user.guild_permissions.administrator:
            return True

        # Check if user has bot manager role
        if self.bot.config.bot_manager_role_id:
            role = interaction.guild.get_role(self.bot.config.bot_manager_role_id)
            if role and role in interaction.user.roles:
                return True

        return False

    # Command is registered in bot.py
    async def queue_command(self, interaction: discord.Interaction):
        """
        Show the current queue status.

        Args:
            interaction: Discord interaction
        """
        start_time = time.time()

        try:
            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # Get queue status
            status = await self.bot.queue_service.get_queue_status()

            # Create embed
            embed = discord.Embed(
                title="Queue Status",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="Queue Size",
                value=str(status["queue_size"]),
                inline=True
            )

            embed.add_field(
                name="Processing",
                value=str(status["processing"]),
                inline=True
            )

            embed.add_field(
                name="Max Concurrent",
                value=str(status["max_concurrent"]),
                inline=True
            )

            # Send response
            await interaction.followup.send(embed=embed, ephemeral=True)

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="queue",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=True
            ))

        except Exception as e:
            logger.error(f"Error in queue command: {e}", exc_info=True)

            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="queue",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    # Command is registered in bot.py
    async def clear_queue_command(self, interaction: discord.Interaction):
        """
        Clear the queue.

        Args:
            interaction: Discord interaction
        """
        start_time = time.time()

        try:
            # Check if user has admin permissions
            if not self._check_admin(interaction):
                await interaction.response.send_message(
                    "You don't have permission to use this command.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="clear_queue",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # Clear queue
            # This would need to be implemented in the queue service
            # For now, we'll just show a message

            await interaction.followup.send(
                "Queue cleared.",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="clear_queue",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=True
            ))

        except Exception as e:
            logger.error(f"Error in clear_queue command: {e}", exc_info=True)

            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="clear_queue",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    # Command is registered in bot.py
    async def set_queue_priority_command(self,
                                        interaction: discord.Interaction,
                                        user: discord.User,
                                        priority: int = QueuePriority.NORMAL):
        """
        Set the priority for a user in the queue.

        Args:
            interaction: Discord interaction
            user: User to set priority for
            priority: Priority level
        """
        start_time = time.time()

        try:
            # Check if user has admin permissions
            if not self._check_admin(interaction):
                await interaction.response.send_message(
                    "You don't have permission to use this command.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="set_queue_priority",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # Set priority
            # This would need to be implemented in the queue service
            # For now, we'll just show a message

            # Get priority name
            priority_name = "Normal"
            if priority == QueuePriority.HIGH:
                priority_name = "High"
            elif priority == QueuePriority.LOW:
                priority_name = "Low"

            await interaction.followup.send(
                f"Set priority for {user.mention} to {priority_name}.",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="set_queue_priority",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=True
            ))

        except Exception as e:
            logger.error(f"Error in set_queue_priority command: {e}", exc_info=True)

            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="set_queue_priority",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))
