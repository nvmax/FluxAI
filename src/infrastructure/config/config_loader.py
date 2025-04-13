"""
Configuration loader for the application.
"""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

def get_config() -> Dict[str, Any]:
    """
    Get the application configuration.

    Returns:
        Dictionary containing configuration values
    """
    config = {
        # Discord configuration
        'command_prefix': os.getenv('COMMAND_PREFIX', '/'),
        'discord_token': os.getenv('DISCORD_TOKEN'),
        'allowed_servers': os.getenv('ALLOWED_SERVERS', '').split(','),
        'channel_ids': os.getenv('CHANNEL_IDS', '').split(','),
        'bot_manager_role_id': os.getenv('BOT_MANAGER_ROLE_ID'),

        # ComfyUI configuration
        'comfyui_dir': os.getenv('COMFYUI_DIR'),
        'comfyui_models_path': os.getenv('COMFYUI_MODELS_PATH'),
        'server_address': os.getenv('SERVER_ADDRESS', '127.0.0.1:8188'),
        'workflow_file': os.getenv('fluxversion', 'config/FluxDev24GB.json'),
        'pulid_workflow': os.getenv('PULIDWORKFLOW', 'config/PulidFluxDev.json'),

        # AI configuration
        'enable_prompt_enhancement': os.getenv('ENABLE_PROMPT_ENHANCEMENT', 'False'),
        'ai_provider': os.getenv('AI_PROVIDER', 'gemini'),
        'gemini_model': os.getenv('GEMINI_MODEL', 'gemini-pro'),
        'openai_model': os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
        'xai_model': os.getenv('XAI_MODEL', 'grok-beta'),
        'embedding_model': os.getenv('EMBEDDING_MODEL', 'text-embedding-ada-002'),
        'openai_api_key': os.getenv('OPENAI_API_KEY'),
        'gemini_api_key': os.getenv('GEMINI_API_KEY'),
        'xai_api_key': os.getenv('XAI_API_KEY'),

        # API tokens
        'huggingface_token': os.getenv('HUGGINGFACE_TOKEN'),
        'civitai_api_token': os.getenv('CIVITAI_API_TOKEN'),

        # Server configuration
        'bot_server': os.getenv('BOT_SERVER', '127.0.0.1'),
    }

    return config
