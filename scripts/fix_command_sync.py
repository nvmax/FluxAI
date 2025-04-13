"""
Script to fix command syncing issues.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

def fix_bot_class():
    """Fix the bot class to properly sync commands"""
    # Get the path to the bot.py file
    bot_path = Path(__file__).parent.parent / "src" / "presentation" / "discord" / "bot.py"
    
    # Read the file
    with open(bot_path, "r") as f:
        content = f.read()
    
    # Update the on_ready method
    if "async def on_ready(self):" in content:
        # Find the start of the method
        start = content.find("async def on_ready(self):")
        # Find the end of the method (next def or end of file)
        next_def = content.find("async def", start + 1)
        if next_def == -1:
            next_def = len(content)
        
        # Extract the method
        method = content[start:next_def]
        
        # Create the new method
        new_method = """async def on_ready(self):
        \"\"\"Called when the bot is ready\"\"\"
        logger.info(f"=== Bot Ready: {self.user} ===")
        await self.change_presence(activity=discord.Game(name="with image generation"))
        
        # Sync commands with Discord
        try:
            if not self.config.allowed_servers:
                logger.warning("No allowed servers configured, syncing globally")
                synced = await self.tree.sync()
                logger.info(f"Synced {len(synced)} commands globally")
            else:
                for server_id in self.config.allowed_servers:
                    try:
                        guild = discord.Object(id=int(server_id))
                        synced = await self.tree.sync(guild=guild)
                        logger.info(f"Synced {len(synced)} commands to guild {server_id}")
                    except Exception as e:
                        logger.error(f"Failed to sync commands to guild {server_id}: {e}")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")"""
        
        # Replace the method
        content = content.replace(method, new_method)
        
        # Write the file
        with open(bot_path, "w") as f:
            f.write(content)
        
        print(f"Updated on_ready method in {bot_path}")
    else:
        print("Could not find on_ready method in bot.py")

def add_sync_command():
    """Add a sync command to the bot"""
    # Get the path to the image_commands.py file
    commands_path = Path(__file__).parent.parent / "src" / "presentation" / "discord" / "commands" / "image_commands.py"
    
    # Read the file
    with open(commands_path, "r") as f:
        content = f.read()
    
    # Check if the sync command already exists
    if "@app_commands.command(name=\"sync\"" in content:
        print("Sync command already exists")
        return
    
    # Find the end of the class
    end_of_class = content.rfind(")")
    
    # Create the sync command
    sync_command = """
    @app_commands.command(
        name="sync",
        description="Sync commands with Discord"
    )
    async def sync_command(self, interaction: discord.Interaction):
        \"\"\"
        Sync commands with Discord.
        
        Args:
            interaction: Discord interaction
        \"\"\"
        start_time = time.time()
        
        try:
            # Check if user has admin permissions
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "You don't have permission to use this command.",
                    ephemeral=True
                )
                
                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="sync",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))
                
                return
                
            # Defer response to give us time to process
            await interaction.response.defer(ephemeral=True)
            
            # Sync commands
            try:
                synced = await self.bot.tree.sync(guild=interaction.guild)
                await interaction.followup.send(
                    f"Synced {len(synced)} commands to this server.",
                    ephemeral=True
                )
                
                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="sync",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=True
                ))
            except Exception as e:
                await interaction.followup.send(
                    f"Error syncing commands: {str(e)}",
                    ephemeral=True
                )
                
                # Record command execution
                self.event_bus.publish(CommandExecutedEvent(
                    command_name="sync",
                    user_id=str(interaction.user.id),
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id),
                    execution_time=time.time() - start_time,
                    success=False
                ))
                
        except Exception as e:
            logger.error(f"Error in sync command: {e}", exc_info=True)
            
            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
            
            # Record command execution
            self.event_bus.publish(CommandExecutedEvent(
                command_name="sync",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                channel_id=str(interaction.channel_id),
                execution_time=time.time() - start_time,
                success=False
            ))"""
    
    # Add the sync command to the end of the class
    content = content[:end_of_class] + sync_command + content[end_of_class:]
    
    # Write the file
    with open(commands_path, "w") as f:
        f.write(content)
    
    print(f"Added sync command to {commands_path}")

def main():
    """Main function"""
    # Fix the bot class
    fix_bot_class()
    
    # Add the sync command
    add_sync_command()
    
    print("Command sync issues fixed!")

if __name__ == "__main__":
    main()
