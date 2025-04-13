"""
Script to update the .env file.
"""

import os
import sys
from pathlib import Path

def update_env_file():
    """Update the .env file to use the correct paths"""
    # Get the path to the .env file
    env_path = Path(__file__).parent.parent / ".env"
    
    # Read the file
    with open(env_path, "r") as f:
        lines = f.readlines()
    
    # Update the lines
    updated_lines = []
    for line in lines:
        # Remove quotes from workflow paths and add config/ prefix
        if line.startswith("fluxversion="):
            filename = line.split("=", 1)[1].strip().strip('"')
            updated_lines.append(f"fluxversion=config/{filename}\n")
        elif line.startswith("PULIDWORKFLOW="):
            filename = line.split("=", 1)[1].strip().strip('"')
            updated_lines.append(f"PULIDWORKFLOW=config/{filename}\n")
        else:
            updated_lines.append(line)
    
    # Write the file
    with open(env_path, "w") as f:
        f.writelines(updated_lines)
    
    print(f"Updated .env file at {env_path}")

if __name__ == "__main__":
    update_env_file()
