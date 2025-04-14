"""
XAI (X.ai/Grok) provider for AI services.
"""

import logging
import aiohttp
import os
from typing import Dict, Any, Optional

from src.domain.interfaces.ai_provider import AIProvider
from src.infrastructure.config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class XAIProvider(AIProvider):
    """
    XAI provider for AI services.
    Uses the X.ai (Grok) API for prompt enhancement.
    """

    def __init__(self):
        """Initialize the XAI provider"""
        self.config = ConfigManager()
        self.api_key = self.config.xai_api_key
        self.model = self.config.xai_model
        self._base_url = "https://api.x.ai/v1"

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
            url = f"{self.base_url}/chat/completions"

            # Create a simple test request
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello"
                    }
                ],
                "max_tokens": 5
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Error testing connection to XAI: {e}")
            return False

    async def generate_response(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Generate an enhanced prompt using the XAI API.

        Args:
            prompt: The prompt to enhance
            temperature: Temperature for generation (controls creativity)

        Returns:
            The enhanced prompt
        """
        try:
            # If temperature is very low (creativity level 1), return original prompt
            # This is a fallback - level 1 should be handled by AIService.enhance_prompt directly
            if temperature <= 0.1 or round(1 + (temperature * 9)) == 1:
                logger.info("Creativity level 1: Using original prompt without enhancement")
                return prompt

            url = f"{self.base_url}/chat/completions"

            # Get word limit based on temperature
            word_limit = self._get_word_limit(temperature)

            # Add word limit instruction to system prompt
            system_prompt = self.get_system_prompt(temperature)
            word_limit_instruction = f"\n\nIMPORTANT: Your response must not exceed {word_limit} words. Be concise and precise."
            system_prompt = system_prompt + word_limit_instruction

            # Create the request payload
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"Original prompt: {prompt}\n\nEnhanced prompt:"
                    }
                ],
                "temperature": temperature,
                "max_tokens": 1024,
                "n": 1,
                "stop": ["\n"]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        enhanced_prompt = data["choices"][0]["message"]["content"].strip()

                        # Enforce word limit
                        enhanced_prompt = self._enforce_word_limit(enhanced_prompt, word_limit)

                        logger.info(f"Enhanced prompt with XAI: {enhanced_prompt}")
                        return enhanced_prompt
                    else:
                        error_data = await response.text()
                        logger.error(f"XAI API error: {response.status} - {error_data}")
                        return f"Error: {response.status}"
        except Exception as e:
            logger.error(f"Error generating response from XAI: {e}")
            return f"Error: {str(e)}"

    def get_system_prompt(self, temperature: float) -> str:
        """
        Get the system prompt for the provider.

        Args:
            temperature: Temperature for generation (controls creativity)

        Returns:
            The system prompt
        """
        # Map temperature to creativity level (1-10)
        creativity_level = round(1 + (temperature * 9))

        # Level 1 (temperature <= 0.1) doesn't need a system prompt as it returns the original prompt

        if temperature <= 0.2:  # Level 2
            system_prompt = (
                "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation. For this prompt, make minimal enhancements:"
                "\n1. Keep the original prompt almost entirely intact"
                "\n2. Only add basic descriptive details if absolutely necessary"
                "\n3. Do not change the core concept or style"
                "\n4. Return the prompt in a single sentence without any unnecessary information must be under 1999 characters"
            )
        elif temperature <= 0.3:  # Level 3
            system_prompt = (
                "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation, make light enhancements:"
                "\n1. Keep the original prompt almost entirely intact"
                "\n2. Add minimal artistic style suggestions"
                "\n3. Include basic descriptive details"
                "\n4. Return the prompt in a single sentence without any unnecessary information must be under 1999 characters"
            )
        elif temperature <= 0.4:  # Level 4
            system_prompt = (
                "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation. For this prompt, make moderate enhancements:"
                "\n1. Keep the original prompt almost entirely intact add some detail"
                "\n2. Add some artistic style elements"
                "\n3. Include additional descriptive details"
                "\n4. Return the prompt in a single sentence without any unnecessary information must be under 1999 characters"
            )
        elif temperature <= 0.5:  # Level 5
            system_prompt = (
                "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation. For this prompt, make balanced enhancements:"
                "\n1. Keep the original prompt almost entirely intact add flavor and enhance the concept"
                "\n2. Suggest complementary artistic styles"
                "\n3. Add meaningful descriptive elements"
                "\n4. Return the prompt in a single sentence without any unnecessary information must be under 1999 characters"
            )
        elif temperature <= 0.6:  # Level 6
            system_prompt = (
                "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation. For this prompt, make notable enhancements:"
                "\n1. Keep the original prompt almost entirely intact,Expand on the original concept"
                "\n2. Add specific artistic style recommendations"
                "\n3. Include detailed visual descriptions"
                "\n4. Return the prompt in a single sentence without any unnecessary information must be under 1999 characters"
            )
        elif temperature <= 0.7:  # Level 7
            system_prompt = (
                "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation. For this prompt, make significant enhancements:"
                "\n1. Keep the original prompt almost entirely intact,Build upon the core concept"
                "\n2. Add rich artistic style elements"
                "\n3. Include comprehensive visual details"
                "\n4. Return the prompt in a single sentence without any unnecessary information must be under 1999 characters"
            )
        elif temperature <= 0.8:  # Level 8
            system_prompt = (
                "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation. For this prompt, make extensive enhancements:"
                "\n1. Keep the original prompt almost entirely intact,Elaborate on the original concept"
                "\n2. Add detailed artistic direction"
                "\n3. Include rich visual descriptions"
                "\n4. Return the prompt in a single sentence without any unnecessary information must be under 1999 characters"
            )
        elif temperature <= 0.9:  # Level 9
            system_prompt = (
                "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation. For this prompt, make substantial enhancements:"
                "\n1. Keep the original prompt almost entirely intact,Significantly expand the concept"
                "\n2. Add comprehensive artistic direction"
                "\n3. Include intricate visual details"
                "\n4. Return the prompt in a single sentence without any unnecessary information must be under 1999 characters"
            )
        else:  # Level 10
            system_prompt = (
                "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation. For this prompt, make maximum enhancements:"
                "\n1. Keep the original prompt almost entirely intact,Fully develop and expand the concept"
                "\n2. Add extensive artistic direction"
                "\n3. Include highly detailed visual descriptions"
                "\n4. Return the prompt in a single sentence without any unnecessary information must be under 1999 characters"
            )

        return system_prompt

    def _get_word_limit(self, temperature: float) -> int:
        """
        Get the word limit based on temperature.

        Args:
            temperature: Temperature for generation

        Returns:
            Word limit
        """
        # Map temperature to creativity level (1-10)
        creativity_level = round(1 + (temperature * 9))

        # Define word limits for each creativity level
        word_limits = {
            1: 10,
            2: 20,
            3: 30,
            4: 40,
            5: 50,
            6: 60,
            7: 70,
            8: 80,
            9: 90,
            10: 100
        }

        return word_limits.get(creativity_level, 50)

    def _enforce_word_limit(self, text: str, limit: int) -> str:
        """
        Enforce word limit on text.

        Args:
            text: Text to limit
            limit: Maximum number of words

        Returns:
            Limited text
        """
        words = text.split()
        if len(words) <= limit:
            return text

        return ' '.join(words[:limit])
