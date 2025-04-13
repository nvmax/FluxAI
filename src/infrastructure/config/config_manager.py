"""
Configuration management for the application.
Centralizes all configuration loading and access.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Centralized configuration management for the application.
    Loads configuration from environment variables and JSON files.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one config manager exists"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, env_file: str = '.env', config_dir: str = 'config'):
        """
        Initialize the configuration manager.

        Args:
            env_file: Path to the .env file
            config_dir: Directory containing configuration files
        """
        # Only initialize once (singleton pattern)
        if self._initialized:
            return

        self.env_file = env_file
        self.config_dir = Path(config_dir)
        self.configs = {}

        # Load configurations
        self.load_env()
        self.load_configs()

        # Discord configurations
        self.discord_token = os.getenv('DISCORD_TOKEN')
        self.command_prefix = os.getenv('COMMAND_PREFIX')
        self.channel_ids = [int(id) for id in os.getenv('CHANNEL_IDS', '').split(',') if id]
        self.allowed_servers = [int(id) for id in os.getenv('ALLOWED_SERVERS', '').split(',') if id]
        self.bot_manager_role_id = int(os.getenv('BOT_MANAGER_ROLE_ID', '0'))
        self.flux_version = os.getenv('fluxversion')

        # Server configurations
        self.bot_server = os.getenv('BOT_SERVER', 'localhost')
        self.server_address = os.getenv('server_address')

        # Workflow configurations
        self.pulid_workflow = os.getenv('PULIDWORKFLOW', 'config/PulidFluxDev.json').strip('"')
        self.flux_version = os.getenv('fluxversion', 'config/FluxDev24GB.json').strip('"')

        # AI Integration
        self.enable_prompt_enhancement = os.getenv('ENABLE_PROMPT_ENHANCEMENT', 'false').lower() == 'true'
        self.ai_provider = os.getenv('AI_PROVIDER', 'lmstudio')

        # Provider settings
        self.lmstudio_host = os.getenv('LMSTUDIO_HOST', 'localhost')
        self.lmstudio_port = os.getenv('LMSTUDIO_PORT', '1234')
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'text-embedding-ada-002')
        self.xai_api_key = os.getenv('XAI_API_KEY', '')
        self.xai_model = os.getenv('XAI_MODEL', 'grok-beta')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')
        self.anthropic_model = os.getenv('ANTHROPIC_MODEL', 'claude-3-opus-20240229')
        self.mistral_api_key = os.getenv('MISTRAL_API_KEY', '')
        self.mistral_model = os.getenv('MISTRAL_MODEL', 'mistral-large-latest')

        self._initialized = True

    def load_env(self, env_file: Optional[str] = None):
        """
        Load environment variables from .env file.

        Args:
            env_file: Path to the .env file (optional, uses self.env_file if not provided)
        """
        try:
            load_dotenv(env_file or self.env_file)
            logger.info(f"Loaded environment variables from {env_file or self.env_file}")
        except Exception as e:
            logger.error(f"Error loading environment variables: {e}")

    def load_configs(self):
        """Load configuration from JSON files in the config directory"""
        try:
            if not self.config_dir.exists():
                logger.warning(f"Config directory {self.config_dir} does not exist")
                os.makedirs(self.config_dir, exist_ok=True)
                logger.info(f"Created config directory {self.config_dir}")

            for config_file in self.config_dir.glob('*.json'):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_name = config_file.stem
                        self.configs[config_name] = json.load(f)
                    logger.info(f"Loaded configuration from {config_file}")
                except Exception as e:
                    logger.error(f"Error loading configuration from {config_file}: {e}")
        except Exception as e:
            logger.error(f"Error loading configurations: {e}")

    def get_config(self, name: str) -> Dict[str, Any]:
        """
        Get a configuration by name.

        Args:
            name: Name of the configuration to get

        Returns:
            The configuration dictionary
        """
        return self.configs.get(name, {})

    def load_json(self, file_path: str) -> Dict[str, Any]:
        """
        Load a JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            The loaded JSON data
        """
        if file_path is None:
            logger.error("Cannot load JSON file: file_path is None")
            return {}

        try:
            # Try different paths
            paths_to_try = [
                file_path,  # Original path
                os.path.join('config', os.path.basename(file_path)),  # In config directory
                os.path.join(str(self.config_dir), os.path.basename(file_path)),  # Using config_dir
                os.path.basename(file_path),  # Just the filename
                'config/PulidFluxDev.json' if 'pulid' in file_path.lower() else None,  # Direct path for PuLID workflow
                'config/FluxDev24GB.json' if 'flux' in file_path.lower() else None  # Direct path for Flux workflow
            ]

            # Remove None values
            paths_to_try = [p for p in paths_to_try if p is not None]

            for path in paths_to_try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        logger.info(f"Successfully loaded JSON file from {path}")
                        return json.load(f)

            logger.error(f"Error loading JSON file {file_path}: File not found in any of the expected locations")
            logger.error(f"Tried paths: {paths_to_try}")
            return {}
        except Exception as e:
            logger.error(f"Error loading JSON file {file_path}: {e}")
            return {}

    def save_json(self, file_path: str, data: Dict[str, Any]):
        """
        Save data to a JSON file.

        Args:
            file_path: Path to the JSON file
            data: Data to save
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving JSON file {file_path}: {e}")
