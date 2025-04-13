"""
Discord commands for analytics.
"""

import discord
import logging
import time
from discord import app_commands
from discord.ext import commands

from src.domain.events.event_bus import EventBus
from src.domain.events.common_events import CommandExecutedEvent
from src.infrastructure.database.image_repository import ImageRepository

logger = logging.getLogger(__name__)

class AnalyticsCommands(commands.Cog):
    """Commands for analytics"""

    def __init__(self, bot):
        """
        Initialize analytics commands.

        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.event_bus = EventBus()

    async def cog_load(self):
        """Called when the cog is loaded"""
        logger.info("Analytics commands loaded")

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info("Analytics commands ready")

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
    async def stats_command(self, interaction: discord.Interaction, days: int = 7):
        """
        Show usage statistics.

        Args:
            interaction: Discord interaction
            days: Number of days to show statistics for
        """
        start_time = time.time()

        try:
            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # We're not using the stats from the analytics service anymore
            # Instead, we're directly querying the database

            # Create embed
            embed = discord.Embed(
                title=f"Usage Statistics (Last {days} Days)",
                color=discord.Color.blue()
            )

            # Query the analytics.db database directly with detailed logging
            import sqlite3
            import os

            # Get the path to the analytics.db file
            analytics_db_path = os.path.join(os.getcwd(), 'analytics.db')
            logger.info(f"ANALYTICS: Stats command - Database path: {analytics_db_path}")

            # Check if the file exists
            if not os.path.exists(analytics_db_path):
                logger.error(f"ANALYTICS: Stats command - Analytics database not found at {analytics_db_path}")

                # Try to find the database file
                for root, dirs, files in os.walk(os.getcwd()):
                    if 'analytics.db' in files:
                        analytics_db_path = os.path.join(root, 'analytics.db')
                        logger.info(f"ANALYTICS: Stats command - Found database at {analytics_db_path}")
                        break
                else:
                    logger.error(f"ANALYTICS: Stats command - Could not find analytics.db anywhere in the project")
                    total_images = 0
                    avg_generation_time = 0
                    total_videos = 0
                    avg_video_time = 0
                    total_users = 0
                    return

            try:
                # Connect to the database
                conn = sqlite3.connect(analytics_db_path)
                c = conn.cursor()

                # Check if the table exists
                c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='image_stats'")
                if not c.fetchone():
                    logger.error(f"ANALYTICS: Stats command - image_stats table does not exist in {analytics_db_path}")
                    total_images = 0
                    avg_generation_time = 0
                    total_videos = 0
                    avg_video_time = 0
                    total_users = 0
                    return

                # Calculate cutoff time for the last N days
                cutoff_time = time.time() - (days * 24 * 60 * 60)
                logger.info(f"ANALYTICS: Stats command - Cutoff time: {cutoff_time}")

                # Get total records in the table
                c.execute("SELECT COUNT(*) FROM image_stats")
                total_records = c.fetchone()[0] or 0
                logger.info(f"ANALYTICS: Stats command - Total records in image_stats: {total_records}")

                # Get total images (non-video) - use a very simple query
                c.execute("SELECT COUNT(*) FROM image_stats WHERE is_video = 0")
                total_images = c.fetchone()[0] or 0
                logger.info(f"ANALYTICS: Stats command - Total images (all time): {total_images}")

                # Get average generation time for images - use a very simple query
                c.execute("SELECT AVG(generation_time) FROM image_stats WHERE is_video = 0 AND generation_time IS NOT NULL")
                avg_generation_time = c.fetchone()[0] or 0
                logger.info(f"ANALYTICS: Stats command - Avg generation time (all time): {avg_generation_time}")

                # Get total videos - use a very simple query
                c.execute("SELECT COUNT(*) FROM image_stats WHERE is_video = 1")
                total_videos = c.fetchone()[0] or 0
                logger.info(f"ANALYTICS: Stats command - Total videos (all time): {total_videos}")

                # Get average generation time for videos - use a very simple query
                c.execute("SELECT AVG(generation_time) FROM image_stats WHERE is_video = 1 AND generation_time IS NOT NULL")
                avg_video_time = c.fetchone()[0] or 0
                logger.info(f"ANALYTICS: Stats command - Avg video time (all time): {avg_video_time}")

                # Get total unique users - use a very simple query
                c.execute("SELECT COUNT(DISTINCT user_id) FROM image_stats")
                total_users = c.fetchone()[0] or 0
                logger.info(f"ANALYTICS: Stats command - Total users (all time): {total_users}")

                # Get the most recent records for debugging
                c.execute("SELECT id, user_id, generation_time, is_video, timestamp FROM image_stats ORDER BY timestamp DESC LIMIT 5")
                recent_records = c.fetchall()
                for record in recent_records:
                    logger.info(f"ANALYTICS: Stats command - Recent record: {record}")

                # Close the connection
                conn.close()

            except Exception as e:
                logger.error(f"ANALYTICS: Stats command - Error querying analytics database: {e}", exc_info=True)
                total_images = 0
                avg_generation_time = 0
                total_videos = 0
                avg_video_time = 0
                total_users = 0

            embed.add_field(
                name="Image Generation",
                value=f"Total Images: {total_images}\n"
                      f"Avg. Generation Time: {avg_generation_time:.2f}s\n"
                      f"Total Videos: {total_videos}\n"
                      f"Avg. Video Time: {avg_video_time:.2f}s",
                inline=False
            )

            # Command usage stats are no longer displayed

            # Total users is already retrieved from the direct database query above

            embed.add_field(
                name="User Activity",
                value=f"Total Users: {total_users}",
                inline=False
            )

            # Send response
            await interaction.followup.send(embed=embed, ephemeral=True)

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="stats",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=True
            ))

        except Exception as e:
            logger.error(f"Error in stats command: {e}", exc_info=True)

            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="stats",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    # Command is registered in bot.py
    async def reset_stats_command(self, interaction: discord.Interaction):
        """
        Reset usage statistics.

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
                    command_name="reset_stats",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # Reset statistics directly in the analytics.db database
            import sqlite3
            import os

            # Get the path to the analytics.db file
            analytics_db_path = os.path.join(os.getcwd(), 'analytics.db')

            # Check if the file exists
            if not os.path.exists(analytics_db_path):
                logger.error(f"Analytics database not found at {analytics_db_path}")
                success = False
            else:
                try:
                    # Connect to the database
                    conn = sqlite3.connect(analytics_db_path)
                    c = conn.cursor()

                    # Clear all tables
                    c.execute("DELETE FROM command_usage")
                    c.execute("DELETE FROM image_stats")
                    c.execute("DELETE FROM user_activity")
                    c.execute("DELETE FROM daily_stats")

                    # Commit changes and close connection
                    conn.commit()
                    conn.close()

                    logger.info("Analytics statistics have been reset")
                    success = True
                except Exception as e:
                    logger.error(f"Error resetting analytics database: {e}")
                    success = False

            if success:
                await interaction.followup.send(
                    "Usage statistics have been reset.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="reset_stats",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=True
                ))
            else:
                await interaction.followup.send(
                    "Failed to reset usage statistics.",
                    ephemeral=True
                )

                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="reset_stats",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))

        except Exception as e:
            logger.error(f"Error in reset_stats command: {e}", exc_info=True)

            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="reset_stats",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))

    @app_commands.command(name="image_stats", description="Show image generation statistics")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def image_stats_command(self, interaction: discord.Interaction):
        """
        Show image generation statistics.

        Args:
            interaction: Discord interaction
        """
        start_time = time.time()

        try:
            # Check if user has permission
            if not self._check_admin(interaction):
                await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
                return

            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)

            # Get image repository from the bot
            image_repository = None
            if hasattr(self.bot, 'image_repository'):
                image_repository = self.bot.image_repository
            else:
                # Try to get from DI container
                try:
                    from src.infrastructure.di.container import DIContainer
                    container = DIContainer()
                    image_repository = container.resolve(ImageRepository)
                except Exception as e:
                    logger.error(f"Error getting image repository: {e}")

            if not image_repository:
                await interaction.followup.send("Image repository not available.", ephemeral=True)
                return

            # Get statistics
            stats = await image_repository.get_stats()

            # Create embed
            embed = discord.Embed(
                title="Image Generation Statistics",
                color=discord.Color.blue()
            )

            # Add general stats
            embed.add_field(
                name="General Statistics",
                value=f"Total Generations: {stats.get('total_generations', 0)}\n"
                      f"Completed Generations: {stats.get('completed_generations', 0)}\n"
                      f"Unique Users: {stats.get('unique_users', 0)}",
                inline=False
            )

            # Add generation time stats
            embed.add_field(
                name="Generation Times",
                value=f"Average Generation Time: {stats.get('avg_generation_time', 0):.2f}s\n"
                      f"Average Image Generation Time: {stats.get('avg_image_generation_time', 0):.2f}s\n"
                      f"Average Video Generation Time: {stats.get('avg_video_generation_time', 0):.2f}s",
                inline=False
            )

            # Add popular resolutions
            popular_resolutions = stats.get('popular_resolutions', [])
            popular_resolutions_str = "\n".join([
                f"{res['resolution']}: {res['count']}"
                for res in popular_resolutions[:5]
            ]) if popular_resolutions else "No data"

            embed.add_field(
                name="Popular Resolutions",
                value=popular_resolutions_str,
                inline=False
            )

            # Add popular loras
            popular_loras = stats.get('popular_loras', [])
            popular_loras_str = "\n".join([
                f"{lora['name']}: {lora['count']}"
                for lora in popular_loras[:5]
            ]) if popular_loras else "No data"

            embed.add_field(
                name="Popular LoRAs",
                value=popular_loras_str,
                inline=False
            )

            # Add generation types
            generation_types = stats.get('generation_types', [])
            generation_types_str = "\n".join([
                f"{gen_type['type']}: {gen_type['count']}"
                for gen_type in generation_types[:5]
            ]) if generation_types else "No data"

            embed.add_field(
                name="Generation Types",
                value=generation_types_str,
                inline=False
            )

            # Send response
            await interaction.followup.send(embed=embed, ephemeral=True)

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="image_stats",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=True
            ))

        except Exception as e:
            logger.error(f"Error in image_stats command: {e}", exc_info=True)
            await interaction.followup.send("An error occurred while fetching image statistics.", ephemeral=True)

            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="image_stats",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))