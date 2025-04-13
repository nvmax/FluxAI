import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class LoraManager:
    """
    Manages LoRA operations including loading configurations, applying LoRAs to workflows,
    and handling trigger words.
    """

    def __init__(self, config_paths=None):
        """
        Initialize the LoRA manager.

        Args:
            config_paths: List of possible paths to look for lora.json
        """
        self.config_paths = config_paths or [
            os.path.join('config', 'lora.json')
        ]
        self.lora_config = None
        self.lora_info = {}
        self.load_config()

    def load_config(self) -> bool:
        """
        Load the LoRA configuration from one of the possible paths.

        Returns:
            bool: True if configuration was loaded successfully, False otherwise.
        """
        for path in self.config_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        self.lora_config = json.load(f)

                    # Create a lookup dictionary for quick access
                    self.lora_info = {lora['file']: lora for lora in self.lora_config.get('available_loras', [])}
                    logger.info(f"Loaded LoRA configuration from {path} with {len(self.lora_info)} LoRAs")
                    return True
                except Exception as e:
                    logger.error(f"Error loading LoRA configuration from {path}: {str(e)}")

        logger.warning("No valid LoRA configuration found")
        return False

    def get_lora_info(self, lora_file: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific LoRA.

        Args:
            lora_file: The filename of the LoRA

        Returns:
            Dict or None: LoRA information if found, None otherwise
        """
        return self.lora_info.get(lora_file)

    def get_all_loras(self) -> List[Dict[str, Any]]:
        """
        Get all available LoRAs.

        Returns:
            List: List of all LoRA configurations
        """
        return self.lora_config.get('available_loras', []) if self.lora_config else []

    def apply_loras_to_workflow(self, workflow: Dict[str, Any], loras: List[str],
                               lora_node_id: str = '271', prompt_node_id: str = '69') -> Dict[str, Any]:
        """
        Apply selected LoRAs to a workflow.

        Args:
            workflow: The ComfyUI workflow to modify
            loras: List of LoRA filenames to apply
            lora_node_id: The node ID in the workflow that handles LoRAs
            prompt_node_id: The node ID in the workflow that contains the prompt

        Returns:
            Dict: The modified workflow
        """
        if not loras or lora_node_id not in workflow:
            return workflow

        try:
            # Clear existing LoRAs
            lora_loader = workflow[lora_node_id]['inputs']
            for key in list(lora_loader.keys()):
                if key.startswith('lora_'):
                    del lora_loader[key]

            # Add new LoRA entries to the workflow
            for i, lora_file in enumerate(loras, start=1):
                if lora_file in self.lora_info:
                    lora_key = f'lora_{i}'
                    # Get base strength from config
                    base_strength = float(self.lora_info[lora_file].get('weight', 1.0))

                    # If multiple LoRAs are selected, scale down to 0.5 unless already lower
                    if len(loras) > 1:
                        lora_strength = min(base_strength, 0.5)
                    else:
                        lora_strength = base_strength

                    lora_loader[lora_key] = {
                        'on': True,
                        'lora': lora_file,
                        'strength': lora_strength
                    }
                    logger.info(f"Added LoRA {lora_file} with strength {lora_strength}")

                    # Add trigger words to prompt if available
                    if prompt_node_id in workflow and self.lora_info[lora_file].get('add_prompt'):
                        trigger_words = self.lora_info[lora_file]['add_prompt']

                        # Check if this is a PuLID workflow (node 6 uses 'text' instead of 'prompt')
                        if prompt_node_id == '6' and 'text' in workflow[prompt_node_id]['inputs']:
                            # PuLID workflow uses 'text' instead of 'prompt'
                            if trigger_words and trigger_words not in workflow[prompt_node_id]['inputs']['text']:
                                workflow[prompt_node_id]['inputs']['text'] = f"{workflow[prompt_node_id]['inputs']['text']}, {trigger_words}"
                                logger.info(f"Added trigger words '{trigger_words}' for LoRA {lora_file} to PuLID workflow")
                        elif 'prompt' in workflow[prompt_node_id]['inputs']:
                            # Standard workflow uses 'prompt'
                            if trigger_words and trigger_words not in workflow[prompt_node_id]['inputs']['prompt']:
                                workflow[prompt_node_id]['inputs']['prompt'] = f"{workflow[prompt_node_id]['inputs']['prompt']}, {trigger_words}"
                                logger.info(f"Added trigger words '{trigger_words}' for LoRA {lora_file} to standard workflow")
                        else:
                            logger.warning(f"Could not add trigger words for LoRA {lora_file} - no 'prompt' or 'text' field found in node {prompt_node_id}")
                else:
                    logger.warning(f"LoRA {lora_file} not found in configuration")

            logger.info(f"Updated workflow with {len(loras)} LoRAs")

        except Exception as e:
            logger.error(f"Error applying LoRAs to workflow: {str(e)}")

        return workflow

    def get_lora_trigger_words(self, lora_file: str) -> str:
        """
        Get the trigger words for a specific LoRA.

        Args:
            lora_file: The filename of the LoRA

        Returns:
            str: The trigger words for the LoRA, or empty string if not found
        """
        lora_info = self.get_lora_info(lora_file)
        return lora_info.get('add_prompt', '') if lora_info else ''

    def add_trigger_words_to_prompt(self, prompt: str, loras: List[str]) -> str:
        """
        Add LoRA trigger words to a prompt.

        Args:
            prompt: The original prompt
            loras: List of LoRA filenames

        Returns:
            str: The prompt with trigger words added
        """
        modified_prompt = prompt

        for lora_file in loras:
            trigger_words = self.get_lora_trigger_words(lora_file)
            if trigger_words and trigger_words not in modified_prompt:
                modified_prompt = f"{modified_prompt}, {trigger_words}"
                logger.debug(f"Added trigger words '{trigger_words}' for LoRA {lora_file}")

        return modified_prompt
