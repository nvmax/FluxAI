"""
Script to fix image commands to match the old code.
"""

import os
import sys
from pathlib import Path

def fix_image_commands():
    """Fix image commands to match the old code"""
    # Get the path to the image_commands.py file
    commands_path = Path(__file__).parent.parent / "src" / "presentation" / "discord" / "commands" / "image_commands.py"
    
    # Read the file
    with open(commands_path, "r") as f:
        content = f.read()
    
    # Rename the generate_command function to comfy
    content = content.replace("async def generate_command(self,", "async def comfy(self,")
    
    # Update references to the function in the file
    content = content.replace("self.event_bus.publish(CommandExecutedEvent(\n                command_name=\"generate\",", 
                             "self.event_bus.publish(CommandExecutedEvent(\n                command_name=\"comfy\",")
    
    # Write the file
    with open(commands_path, "w") as f:
        f.write(content)
    
    print(f"Updated image_commands.py to use comfy command name")

if __name__ == "__main__":
    fix_image_commands()
