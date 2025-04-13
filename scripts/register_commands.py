"""
Script to register commands directly with the Discord API.
"""

import os
import sys
import json
import requests
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import application components
from src.infrastructure.config.config_manager import ConfigManager

def register_commands():
    """Register commands directly with the Discord API"""
    # Get configuration
    config = ConfigManager()

    # Get Discord token and application ID
    token = config.discord_token

    # Get application ID from Discord API
    headers = {
        "Authorization": f"Bot {token}"
    }

    response = requests.get("https://discord.com/api/v10/users/@me", headers=headers)
    if response.status_code != 200:
        print(f"Failed to get application info: {response.status_code} {response.text}")
        return

    application_id = response.json()["id"]
    print(f"Application ID: {application_id}")

    # Define commands
    commands = [
        {
            "name": "comfy",
            "description": "Generate an image based on a prompt",
            "options": [
                {
                    "name": "prompt",
                    "description": "Enter your prompt",
                    "type": 3,
                    "required": True
                },
                {
                    "name": "resolution",
                    "description": "Choose the resolution",
                    "type": 3,
                    "required": True
                },
                {
                    "name": "upscale_factor",
                    "description": "Choose upscale factor (1-4, default is 1)",
                    "type": 4,
                    "required": False,
                    "choices": [
                        {
                            "name": "1x (No upscale)",
                            "value": 1
                        },
                        {
                            "name": "2x",
                            "value": 2
                        },
                        {
                            "name": "3x",
                            "value": 3
                        },
                        {
                            "name": "4x",
                            "value": 4
                        }
                    ]
                },
                {
                    "name": "seed",
                    "description": "Enter a seed for reproducibility (optional)",
                    "type": 4,
                    "required": False
                }
            ]
        },
        {
            "name": "redux",
            "description": "Generate an image using two reference images",
            "options": [
                {
                    "name": "resolution",
                    "description": "Choose the resolution for the output image",
                    "type": 3,
                    "required": False
                }
            ]
        },
        {
            "name": "pulid",
            "description": "Generate an image using a reference image and a prompt",
            "options": [
                {
                    "name": "prompt",
                    "description": "The prompt to guide the image generation",
                    "type": 3,
                    "required": False
                },
                {
                    "name": "resolution",
                    "description": "Choose the resolution for the output image",
                    "type": 3,
                    "required": False
                }
            ]
        },
        {
            "name": "stats",
            "description": "Show usage statistics",
            "options": [
                {
                    "name": "days",
                    "description": "Number of days to show statistics for (default: 7)",
                    "type": 4,
                    "required": False
                }
            ]
        },
        {
            "name": "reset_stats",
            "description": "Reset usage statistics"
        },
        {
            "name": "lorainfo",
            "description": "Show information about available LoRAs",
            "options": [
                {
                    "name": "lora_name",
                    "description": "Name of the LoRA to show information for (optional)",
                    "type": 3,
                    "required": False
                }
            ]
        },
        {
            "name": "queue",
            "description": "Show the current queue status"
        },
        {
            "name": "clear_queue",
            "description": "Clear the queue"
        },
        {
            "name": "set_queue_priority",
            "description": "Set the priority for a user in the queue",
            "options": [
                {
                    "name": "user",
                    "description": "The user to set priority for",
                    "type": 6,
                    "required": True
                },
                {
                    "name": "priority",
                    "description": "The priority level",
                    "type": 4,
                    "required": False,
                    "choices": [
                        {
                            "name": "High",
                            "value": 0
                        },
                        {
                            "name": "Normal",
                            "value": 1
                        },
                        {
                            "name": "Low",
                            "value": 2
                        }
                    ]
                }
            ]
        },
        {
            "name": "add_banned_word",
            "description": "Add a word to the banned words list",
            "options": [
                {
                    "name": "word",
                    "description": "The word to ban",
                    "type": 3,
                    "required": True
                }
            ]
        },
        {
            "name": "remove_banned_word",
            "description": "Remove a word from the banned words list",
            "options": [
                {
                    "name": "word",
                    "description": "The word to unban",
                    "type": 3,
                    "required": True
                }
            ]
        },
        {
            "name": "list_banned_words",
            "description": "List all banned words"
        },
        {
            "name": "add_regex_pattern",
            "description": "Add a regex pattern to the content filter",
            "options": [
                {
                    "name": "name",
                    "description": "Name of the pattern",
                    "type": 3,
                    "required": True
                },
                {
                    "name": "pattern",
                    "description": "Regex pattern",
                    "type": 3,
                    "required": True
                },
                {
                    "name": "description",
                    "description": "Description of the pattern",
                    "type": 3,
                    "required": True
                },
                {
                    "name": "severity",
                    "description": "Severity level (high, medium, low)",
                    "type": 3,
                    "required": False
                }
            ]
        },
        {
            "name": "sync",
            "description": "Sync commands with Discord"
        }
    ]

    # Register commands with Discord
    if not config.allowed_servers:
        # Register globally
        url = f"https://discord.com/api/v10/applications/{application_id}/commands"
        response = requests.put(url, headers=headers, json=commands)

        if response.status_code == 200:
            print(f"Registered {len(commands)} commands globally")
        else:
            print(f"Failed to register commands globally: {response.status_code} {response.text}")
    else:
        # Register for each server
        for server_id in config.allowed_servers:
            url = f"https://discord.com/api/v10/applications/{application_id}/guilds/{server_id}/commands"
            response = requests.put(url, headers=headers, json=commands)

            if response.status_code == 200:
                print(f"Registered {len(commands)} commands for server {server_id}")
            else:
                print(f"Failed to register commands for server {server_id}: {response.status_code} {response.text}")

if __name__ == "__main__":
    register_commands()
