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
            if temperature <= 0.1:
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
        
        base_prompt = """You are an expert AI image prompt enhancer. Your task is to enhance the user's image generation prompt to create more detailed, vivid, and creative descriptions that will result in better AI-generated images.

Follow these guidelines:
1. Maintain the original intent and subject matter
2. Add descriptive details about lighting, style, mood, and composition
3. Include artistic references or specific rendering styles when appropriate
4. Use language that is clear and specific
5. Do not add NSFW or inappropriate content"""

        if creativity_level <= 3:
            return base_prompt + """
6. Make minimal enhancements, staying very close to the original prompt
7. Focus on clarity and minor detail additions only
8. Maintain a conservative approach to modifications"""
        elif creativity_level <= 6:
            return base_prompt + """
6. Make moderate enhancements that expand on the original prompt
7. Add meaningful details that improve the visual quality
8. Suggest appropriate artistic styles or rendering techniques"""
        else:
            return base_prompt + """
6. Make significant enhancements that transform the original prompt
7. Add rich, detailed descriptions and creative elements
8. Incorporate advanced artistic concepts and composition techniques
9. Suggest unexpected but fitting stylistic choices"""
            
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
