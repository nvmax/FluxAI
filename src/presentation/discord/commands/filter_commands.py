"""
Discord commands for content filtering.
"""

import discord
import logging
import time
import re
from typing import Dict, Any, List, Optional
from discord import app_commands
from discord.ext import commands

from src.domain.events.event_bus import EventBus
from src.domain.events.common_events import CommandExecutedEvent

logger = logging.getLogger(__name__)

class FilterCommands(commands.Cog):
    """Commands for managing content filters and user warnings/bans"""

    def __init__(self, bot):
        """
        Initialize filter commands.

        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.event_bus = EventBus()

    async def cog_load(self):
        """Called when the cog is loaded"""
        logger.info("Filter commands loaded")

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info("Filter commands ready")

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
    async def add_banned_word_command(self, interaction: discord.Interaction, word: str):
        """
        Add a word to the banned words list.

        Args:
            interaction: Discord interaction
            word: Word to ban
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
                    command_name="add_banned_word",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # Add banned word
            success = self.bot.content_filter_service.add_banned_word(word)

            if success:
                await interaction.followup.send(
                    f"Added '{word}' to the banned words list.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="add_banned_word",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=True
                ))
            else:
                await interaction.followup.send(
                    f"Failed to add '{word}' to the banned words list.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="add_banned_word",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

        except Exception as e:
            logger.error(f"Error in add_banned_word command: {e}", exc_info=True)

            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="add_banned_word",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    # Command is registered in bot.py
    async def remove_banned_word_command(self, interaction: discord.Interaction, word: str):
        """
        Remove a word from the banned words list.

        Args:
            interaction: Discord interaction
            word: Word to unban
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
                    command_name="remove_banned_word",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # Remove banned word
            success = self.bot.content_filter_service.remove_banned_word(word)

            if success:
                await interaction.followup.send(
                    f"Removed '{word}' from the banned words list.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="remove_banned_word",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=True
                ))
            else:
                await interaction.followup.send(
                    f"Failed to remove '{word}' from the banned words list.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="remove_banned_word",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

        except Exception as e:
            logger.error(f"Error in remove_banned_word command: {e}", exc_info=True)

            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="remove_banned_word",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    # Command is registered in bot.py
    async def list_banned_words_command(self, interaction: discord.Interaction):
        """
        List all banned words.

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
                    command_name="list_banned_words",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # Get banned words
            banned_words = self.bot.content_filter_service.get_banned_words()

            # Create embed
            embed = discord.Embed(
                title="Banned Words",
                color=discord.Color.red()
            )

            if banned_words:
                # Split into chunks of 20 words
                chunks = [banned_words[i:i+20] for i in range(0, len(banned_words), 20)]

                for i, chunk in enumerate(chunks):
                    embed.add_field(
                        name=f"Words {i*20+1}-{i*20+len(chunk)}",
                        value=", ".join(chunk),
                        inline=False
                    )
            else:
                embed.description = "No banned words found."

            # Send response
            await interaction.followup.send(embed=embed, ephemeral=True)

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="list_banned_words",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=True
            ))

        except Exception as e:
            logger.error(f"Error in list_banned_words command: {e}", exc_info=True)

            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="list_banned_words",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    # Command is registered in bot.py
    async def warnings_command(self, interaction: discord.Interaction, user: discord.User = None):
        """
        Check warnings for a user.

        Args:
            interaction: Discord interaction
            user: User to check warnings for (optional, defaults to the command user)
        """
        start_time = time.time()

        try:
            # If no user is specified, use the command user
            if user is None:
                user = interaction.user
            # If user is not the command user, check admin permissions
            elif user.id != interaction.user.id and not self._check_admin(interaction):
                await interaction.response.send_message(
                    "You don't have permission to check warnings for other users.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="warnings",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # Get warnings for the user
            warnings = self.bot.content_filter_service.get_user_warnings(str(user.id))

            # Create embed
            embed = discord.Embed(
                title=f"Warnings for {user.display_name}",
                color=discord.Color.orange()
            )

            if warnings:
                # Add warning count
                embed.description = f"Total warnings: {len(warnings)}"

                # Add each warning
                for i, warning in enumerate(warnings):
                    # Format the timestamp
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(warning["warned_at"]))

                    # Format the prompt (truncate if too long)
                    prompt = warning["prompt"]
                    if len(prompt) > 100:
                        prompt = prompt[:97] + "..."

                    embed.add_field(
                        name=f"Warning #{i+1} - {timestamp}",
                        value=f"Violation: {warning['violation']}\nPrompt: {prompt}",
                        inline=False
                    )
            else:
                embed.description = "No warnings found for this user."

            # Send response
            await interaction.followup.send(embed=embed, ephemeral=True)

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="warnings",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=True
            ))

        except Exception as e:
            logger.error(f"Error in warnings command: {e}", exc_info=True)

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"An error occurred: {str(e)}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"An error occurred: {str(e)}",
                    ephemeral=True
                )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="warnings",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    # Command is registered in bot.py
    async def warningremove_command(self, interaction: discord.Interaction, user: discord.User):
        """
        Remove all warnings from a user.

        Args:
            interaction: Discord interaction
            user: User to remove warnings from
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
                    command_name="warningremove",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # Remove all warnings for the user
            success = self.bot.content_filter_service.remove_all_user_warnings(str(user.id))

            if success:
                await interaction.followup.send(
                    f"Removed all warnings for {user.display_name}.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="warningremove",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=True
                ))
            else:
                await interaction.followup.send(
                    f"Failed to remove warnings for {user.display_name}.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="warningremove",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

        except Exception as e:
            logger.error(f"Error in warningremove command: {e}", exc_info=True)

            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="warningremove",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    # Command is registered in bot.py
    async def banned_command(self, interaction: discord.Interaction):
        """
        List all banned users.

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
                    command_name="banned",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # Get banned users
            banned_users = self.bot.content_filter_service.get_all_banned_users()

            # Create embed
            embed = discord.Embed(
                title="Banned Users",
                color=discord.Color.red()
            )

            if banned_users:
                # Add banned user count
                embed.description = f"Total banned users: {len(banned_users)}"

                # Add each banned user
                for i, ban_info in enumerate(banned_users):
                    # Format the timestamp
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ban_info["banned_at"]))

                    # Try to get the user from Discord
                    try:
                        user = await self.bot.fetch_user(int(ban_info["user_id"]))
                        user_display = f"{user.name} ({user.id})"
                    except:
                        user_display = f"Unknown User ({ban_info['user_id']})"

                    embed.add_field(
                        name=f"Ban #{i+1} - {timestamp}",
                        value=f"User: {user_display}\nReason: {ban_info['reason']}",
                        inline=False
                    )
            else:
                embed.description = "No banned users found."

            # Send response
            await interaction.followup.send(embed=embed, ephemeral=True)

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="banned",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=True
            ))

        except Exception as e:
            logger.error(f"Error in banned command: {e}", exc_info=True)

            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="banned",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    # Command is registered in bot.py
    async def ban_command(self, interaction: discord.Interaction, user: discord.User, reason: str):
        """
        Ban a user from using the bot.

        Args:
            interaction: Discord interaction
            user: User to ban
            reason: Reason for the ban
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
                    command_name="ban",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # Ban the user
            success = self.bot.content_filter_service.ban_user(str(user.id), reason)

            if success:
                await interaction.followup.send(
                    f"Banned {user.display_name} from using the bot. Reason: {reason}",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="ban",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=True
                ))
            else:
                await interaction.followup.send(
                    f"Failed to ban {user.display_name}.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="ban",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

        except Exception as e:
            logger.error(f"Error in ban command: {e}", exc_info=True)

            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="ban",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    # Command is registered in bot.py
    async def unban_command(self, interaction: discord.Interaction, user: discord.User):
        """
        Unban a user from using the bot.

        Args:
            interaction: Discord interaction
            user: User to unban
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
                    command_name="unban",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # Unban the user
            success = self.bot.content_filter_service.unban_user(str(user.id))

            if success:
                await interaction.followup.send(
                    f"Unbanned {user.display_name} from using the bot.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="unban",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=True
                ))
            else:
                await interaction.followup.send(
                    f"Failed to unban {user.display_name}. They may not be banned.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="unban",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

        except Exception as e:
            logger.error(f"Error in unban command: {e}", exc_info=True)

            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="unban",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    # Command is registered in bot.py
    async def add_regex_pattern_command(self,
                                       interaction: discord.Interaction,
                                       name: str,
                                       pattern: str,
                                       description: str,
                                       severity: str = "medium"):
        """
        Add a regex pattern to the content filter.

        Args:
            interaction: Discord interaction
            name: Name of the pattern
            pattern: Regex pattern
            description: Description of the pattern
            severity: Severity level (high, medium, low)
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
                    command_name="add_regex_pattern",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Validate pattern
            try:
                re.compile(pattern)
            except re.error:
                await interaction.response.send_message(
                    "Invalid regex pattern.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="add_regex_pattern",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Validate severity
            if severity not in ["high", "medium", "low"]:
                await interaction.response.send_message(
                    "Invalid severity level. Must be 'high', 'medium', or 'low'.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="add_regex_pattern",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # Add regex pattern
            success = self.bot.content_filter_service.add_regex_pattern(
                name=name,
                pattern=pattern,
                description=description,
                severity=severity
            )

            if success:
                await interaction.followup.send(
                    f"Added regex pattern '{name}'.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="add_regex_pattern",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=True
                ))
            else:
                await interaction.followup.send(
                    f"Failed to add regex pattern '{name}'.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="add_regex_pattern",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

        except Exception as e:
            logger.error(f"Error in add_regex_pattern command: {e}", exc_info=True)

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"An error occurred: {str(e)}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"An error occurred: {str(e)}",
                    ephemeral=True
                )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="add_regex_pattern",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))
