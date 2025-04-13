"""
Anthropic provider for AI services.
"""

import logging
import json
import aiohttp
from typing import Dict, Any, Optional

from src.domain.interfaces.ai_provider import AIProvider
from src.infrastructure.config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class AnthropicProvider(AIProvider):
    """
    Anthropic provider for AI services.
    Uses the Anthropic API for prompt enhancement.
    """
    
    def __init__(self):
        """Initialize the Anthropic provider"""
        self.config = ConfigManager()
        self.api_key = self.config.anthropic_api_key
        self.model = self.config.anthropic_model
        self._base_url = "https://api.anthropic.com/v1"
        
    @property
    def base_url(self) -> str:
        """
        Get the base URL for the provider's API.
        
        Returns:
            The base URL
        """
        return self._base_url
        
    async def test_connection(self) -> bool:
        """
        Test the connection to the provider.
        
        Returns:
            True if the connection is successful, False otherwise
        """
        try:
            # Use a simple completion request to test the connection
            url = f"{self.base_url}/messages"
            
            payload = {
                "model": self.model,
                "max_tokens": 10,
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello"
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json=payload
                ) as response:
                    if response.status == 200:
                        return True
                    else:
                        logger.error(f"Anthropic connection test failed: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Error testing Anthropic connection: {e}")
            return False
            
    async def generate_response(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Generate an enhanced prompt using the Anthropic API.
        
        Args:
            prompt: The prompt to enhance
            temperature: Temperature for generation (controls creativity)
            
        Returns:
            The enhanced prompt
        """
        try:
            url = f"{self.base_url}/messages"
            
            # Create the request payload
            payload = {
                "model": self.model,
                "max_tokens": 1000,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": f"{self.get_system_prompt(temperature)}\n\nUser prompt: {prompt}"
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["content"][0]["text"].strip()
                    else:
                        error_data = await response.text()
                        logger.error(f"Anthropic API error: {response.status} - {error_data}")
                        return f"Error: {response.status}"
        except Exception as e:
            logger.error(f"Error generating response from Anthropic: {e}")
            return f"Error: {str(e)}"
            
    def get_system_prompt(self, temperature: float) -> str:
        """
        Get the system prompt for the provider.
        
        Args:
            temperature: Temperature for generation (controls creativity)
            
        Returns:
            The system prompt
        """
        creativity_level = "highly creative" if temperature > 0.7 else "balanced"
        
        return f"""You are an expert prompt engineer for image generation models like Stable Diffusion.
Your task is to enhance the user's prompt to create a more detailed and effective prompt for image generation.
Be {creativity_level} in your enhancements, adding details about style, lighting, composition, and other relevant aspects.
Focus on creating a prompt that will generate a high-quality, visually appealing image.
Do not include any explanations or notes in your response, just the enhanced prompt.
Do not use any special formatting or markup in your response."""
