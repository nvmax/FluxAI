# scripts/debug_config.py
import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.config.config_manager import ConfigManager

def debug_config():
    """Debug configuration loading"""
    config = ConfigManager()
    
    # Print environment variables
    print(f"DISCORD_TOKEN: {'*' * 10 if config.discord_token else 'Not set'}")
    print(f"COMMAND_PREFIX: {config.command_prefix}")
    print(f"CHANNEL_IDS: {config.channel_ids}")
    print(f"ALLOWED_SERVERS: {config.allowed_servers}")
    print(f"BOT_MANAGER_ROLE_ID: {config.bot_manager_role_id}")
    print(f"fluxversion: {config.flux_version}")
    print(f"PULIDWORKFLOW: {config.pulid_workflow}")
    
    # Try to load workflow files
    print("\nTrying to load workflow files:")
    
    # Try to load flux version workflow
    flux_path = config.flux_version
    print(f"Looking for flux workflow at: {flux_path}")
    print(f"Absolute path: {os.path.abspath(flux_path)}")
    print(f"File exists: {os.path.exists(flux_path)}")
    
    if os.path.exists(flux_path):
        try:
            flux_data = config.load_json(flux_path)
            print(f"Successfully loaded flux workflow with {len(flux_data)} nodes")
        except Exception as e:
            print(f"Error loading flux workflow: {e}")
    
    # Try to load PuLID workflow
    pulid_path = config.pulid_workflow
    print(f"\nLooking for PuLID workflow at: {pulid_path}")
    print(f"Absolute path: {os.path.abspath(pulid_path)}")
    print(f"File exists: {os.path.exists(pulid_path)}")
    
    if os.path.exists(pulid_path):
        try:
            pulid_data = config.load_json(pulid_path)
            print(f"Successfully loaded PuLID workflow with {len(pulid_data)} nodes")
        except Exception as e:
            print(f"Error loading PuLID workflow: {e}")
    
    # Try to load configuration files
    print("\nTrying to load configuration files:")
    
    # Try to load ratios.json
    ratios_path = os.path.join("config", "ratios.json")
    print(f"Looking for ratios.json at: {ratios_path}")
    print(f"Absolute path: {os.path.abspath(ratios_path)}")
    print(f"File exists: {os.path.exists(ratios_path)}")
    
    if os.path.exists(ratios_path):
        try:
            ratios_data = config.load_json(ratios_path)
            print(f"Successfully loaded ratios with {len(ratios_data.get('ratios', {}))} options")
        except Exception as e:
            print(f"Error loading ratios: {e}")
    
    # Try to load lora.json
    lora_path = os.path.join("config", "lora.json")
    print(f"Looking for lora.json at: {lora_path}")
    print(f"Absolute path: {os.path.abspath(lora_path)}")
    print(f"File exists: {os.path.exists(lora_path)}")
    
    if os.path.exists(lora_path):
        try:
            lora_data = config.load_json(lora_path)
            print(f"Successfully loaded LoRAs with {len(lora_data.get('available_loras', []))} options")
        except Exception as e:
            print(f"Error loading LoRAs: {e}")

if __name__ == "__main__":
    debug_config()