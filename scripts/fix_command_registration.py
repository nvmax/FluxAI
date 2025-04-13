"""
Script to fix command registration to match the old code.
"""

import os
import sys
from pathlib import Path

def fix_command_registration():
    """Fix command registration to match the old code"""
    # Get the path to the bot.py file
    bot_path = Path(__file__).parent.parent / "src" / "presentation" / "discord" / "bot.py"
    
    # Read the file
    with open(bot_path, "r") as f:
        content = f.read()
    
    # Update the _register_commands method
    if "async def _register_commands(self):" in content:
        # Find the start of the method
        start = content.find("async def _register_commands(self):")
        # Find the end of the method (next def or end of file)
        next_def = content.find("async def", start + 1)
        if next_def == -1:
            next_def = len(content)
        
        # Extract the method
        method = content[start:next_def]
        
        # Create the new method
        new_method = """async def _register_commands(self):
        \"\"\"Register commands with Discord\"\"\"
        # Import command modules
        from src.presentation.discord.commands import (
            image_commands,
            queue_commands,
            analytics_commands,
            filter_commands,
            lora_commands
        )
        
        # Create command instances
        image_cog = image_commands.ImageCommands(self)
        queue_cog = queue_commands.QueueCommands(self)
        analytics_cog = analytics_commands.AnalyticsCommands(self)
        filter_cog = filter_commands.FilterCommands(self)
        lora_cog = lora_commands.LoraCommands(self)
        
        # Register command modules
        await self.add_cog(image_cog)
        await self.add_cog(queue_cog)
        await self.add_cog(analytics_cog)
        await self.add_cog(filter_cog)
        await self.add_cog(lora_cog)
        
        # Directly add commands to the tree
        # This is how the old code did it
        self.tree.add_command(image_cog.comfy)
        self.tree.add_command(image_cog.redux_command)
        self.tree.add_command(image_cog.pulid_command)
        self.tree.add_command(image_cog.sync_command)
        self.tree.add_command(queue_cog.queue_command)
        self.tree.add_command(queue_cog.clear_queue_command)
        self.tree.add_command(queue_cog.set_queue_priority_command)
        self.tree.add_command(analytics_cog.stats_command)
        self.tree.add_command(analytics_cog.reset_stats_command)
        self.tree.add_command(filter_cog.add_banned_word_command)
        self.tree.add_command(filter_cog.remove_banned_word_command)
        self.tree.add_command(filter_cog.list_banned_words_command)
        self.tree.add_command(filter_cog.add_regex_pattern_command)
        self.tree.add_command(lora_cog.lorainfo_command)
        self.tree.add_command(lora_cog.reload_loras_command)
        
        logger.info("Registered command modules")"""
        
        # Replace the method
        content = content.replace(method, new_method)
        
        # Write the file
        with open(bot_path, "w") as f:
            f.write(content)
        
        print(f"Updated _register_commands method in {bot_path}")
    else:
        print("Could not find _register_commands method in bot.py")

if __name__ == "__main__":
    fix_command_registration()
