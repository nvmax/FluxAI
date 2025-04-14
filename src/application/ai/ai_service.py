"""
AI service for enhancing prompts.
"""

import logging
import os
import json
import google.generativeai as genai
import openai
from typing import Optional, Dict, Any, Tuple

from src.infrastructure.config.config_manager import ConfigManager
from src.infrastructure.ai_providers.provider_factory import AIProviderFactory

logger = logging.getLogger(__name__)

class AIService:
    """Service for AI-related functionality"""

    def __init__(self):
        """Initialize the AI service"""
        config_manager = ConfigManager()
        self.config = {}

        # Get AI configuration
        self.ai_provider = config_manager.ai_provider.lower() if config_manager.ai_provider else 'gemini'
        self.enable_prompt_enhancement = config_manager.enable_prompt_enhancement

        # Store configuration values
        self.config['ai_provider'] = self.ai_provider
        self.config['enable_prompt_enhancement'] = self.enable_prompt_enhancement

        # Get model configurations from environment variables directly
        import os
        gemini_model = os.getenv('GEMINI_MODEL', 'gemini-pro')
        logger.info(f"Read GEMINI_MODEL from environment: {gemini_model}")

        self.config['gemini_model'] = gemini_model
        self.config['openai_model'] = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        self.config['xai_model'] = os.getenv('XAI_MODEL', 'grok-beta')
        self.config['gemini_api_key'] = os.getenv('GEMINI_API_KEY')
        self.config['openai_api_key'] = os.getenv('OPENAI_API_KEY')
        self.config['xai_api_key'] = os.getenv('XAI_API_KEY')

        # Initialize the appropriate AI provider
        if self.ai_provider == 'gemini':
            self._init_gemini()
        elif self.ai_provider == 'openai':
            self._init_openai()
        elif self.ai_provider == 'xai':
            self._init_xai()
        else:
            logger.warning(f"Unknown AI provider: {self.ai_provider}. Defaulting to Gemini.")
            self.ai_provider = 'gemini'
            self._init_gemini()

        logger.info(f"AI service initialized with provider: {self.ai_provider}")
        logger.info(f"Prompt enhancement enabled: {self.enable_prompt_enhancement}")

    def _init_gemini(self):
        """Initialize Gemini API"""
        api_key = self.config.get('gemini_api_key')
        if not api_key:
            logger.error("Gemini API key not found in configuration")
            return

        # Get the model name from configuration
        model_name = self.config.get('gemini_model', 'gemini-pro')
        logger.info(f"Using Gemini model from config: {model_name}")

        genai.configure(api_key=api_key)
        self.gemini_model = genai.GenerativeModel(model_name)
        logger.info(f"Gemini API initialized with model: {model_name}")

    def _init_openai(self):
        """Initialize OpenAI API"""
        api_key = self.config.get('openai_api_key')
        if not api_key:
            logger.error("OpenAI API key not found in configuration")
            return

        openai.api_key = api_key
        self.openai_model = self.config.get('openai_model', 'gpt-3.5-turbo')
        logger.info(f"OpenAI API initialized with model: {self.openai_model}")

    def _init_xai(self):
        """Initialize XAI (Grok) API"""
        api_key = self.config.get('xai_api_key')
        if not api_key:
            logger.error("XAI API key not found in configuration")
            return

        # XAI implementation would go here
        self.xai_model = self.config.get('xai_model', 'grok-beta')
        logger.info(f"XAI API initialized with model: {self.xai_model}")

    async def enhance_prompt(self, prompt: str, enhancement_level: int = 1) -> str:
        """
        Enhance a prompt using AI.

        Args:
            prompt: The original prompt to enhance
            enhancement_level: Level of enhancement from 1-10 (1 = minimal, 10 = maximum)

        Returns:
            Enhanced prompt
        """
        if not self.enable_prompt_enhancement:
            logger.info("Prompt enhancement is disabled")
            return prompt

        try:
            # Normalize enhancement level
            enhancement_level = max(1, min(10, enhancement_level))

            # For level 1, return the original prompt without any enhancement
            if enhancement_level == 1:
                logger.info("Enhancement level 1: Using original prompt without enhancement")
                return prompt

            # Store enhancement level for use in provider-specific methods
            self.__dict__["enhancement_level"] = enhancement_level

            # Create system prompt based on enhancement level
            system_prompt = self._create_system_prompt(enhancement_level)

            # Call the appropriate AI provider
            if self.ai_provider == 'gemini':
                return await self._enhance_with_gemini(prompt, system_prompt)
            elif self.ai_provider == 'openai':
                return await self._enhance_with_openai(prompt, system_prompt)
            elif self.ai_provider == 'xai':
                return await self._enhance_with_xai(prompt, system_prompt)
            else:
                logger.warning(f"Unknown AI provider: {self.ai_provider}. Returning original prompt.")
                return prompt

        except Exception as e:
            logger.error(f"Error enhancing prompt: {str(e)}", exc_info=True)
            return prompt

    def _create_system_prompt(self, enhancement_level: int) -> str:
        """
        Create a system prompt based on the enhancement level.

        Args:
            enhancement_level: Level of enhancement from 1-10

        Returns:
            System prompt for the AI
        """
        base_prompt = (
            "You are an expert at enhancing prompts for image generation. "
            "Your task is to take a simple prompt and make it more detailed and descriptive "
            "to help generate better images. "
            "Focus on adding details about lighting, composition, style, mood, and visual elements. "
            "Do not change the core subject or theme of the original prompt. "
            "Do not add any explanations or comments - just return the enhanced prompt. "
            "Do not use any negative prompts or words like 'no', 'without', etc."
        )

        if enhancement_level <= 3:
            return base_prompt + " Make minimal enhancements, keeping very close to the original prompt."
        elif enhancement_level <= 6:
            return base_prompt + " Make moderate enhancements, adding some details while preserving the original intent."
        else:
            return base_prompt + " Make significant enhancements, adding many details to create a rich, vivid description."

    async def _enhance_with_gemini(self, prompt: str, system_prompt: str) -> str:
        """
        Enhance a prompt using Gemini.

        Args:
            prompt: The original prompt
            system_prompt: The system prompt

        Returns:
            Enhanced prompt
        """
        try:
            # Combine system prompt and user prompt
            full_prompt = f"{system_prompt}\n\nOriginal prompt: {prompt}\n\nEnhanced prompt:"

            # Generate response
            response = await self.gemini_model.generate_content_async(full_prompt)

            # Extract and return the enhanced prompt
            enhanced_prompt = response.text.strip()

            logger.info(f"Enhanced prompt with Gemini: {enhanced_prompt}")
            return enhanced_prompt

        except Exception as e:
            logger.error(f"Error enhancing prompt with Gemini: {str(e)}", exc_info=True)
            return prompt

    async def _enhance_with_openai(self, prompt: str, system_prompt: str) -> str:
        """
        Enhance a prompt using OpenAI.

        Args:
            prompt: The original prompt
            system_prompt: The system prompt

        Returns:
            Enhanced prompt
        """
        try:
            # Create messages for the API
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]

            # Generate response
            response = await openai.ChatCompletion.acreate(
                model=self.openai_model,
                messages=messages,
                temperature=0.7,
                max_tokens=300
            )

            # Extract and return the enhanced prompt
            enhanced_prompt = response.choices[0].message.content.strip()

            logger.info(f"Enhanced prompt with OpenAI: {enhanced_prompt}")
            return enhanced_prompt

        except Exception as e:
            logger.error(f"Error enhancing prompt with OpenAI: {str(e)}", exc_info=True)
            return prompt

    async def _enhance_with_xai(self, prompt: str, system_prompt: str) -> str:
        """
        Enhance a prompt using XAI (Grok).

        Args:
            prompt: The original prompt
            system_prompt: The system prompt

        Returns:
            Enhanced prompt
        """
        try:
            # Get the XAI provider from the factory
            xai_provider = AIProviderFactory.get_provider('xai')
            if not xai_provider:
                logger.error("Failed to get XAI provider")
                return prompt

            # Extract enhancement level from system prompt
            enhancement_level = 1  # Default to no enhancement

            # Get enhancement level if available
            if "enhancement_level" in self.__dict__:
                enhancement_level = self.__dict__["enhancement_level"]

            # Map enhancement level directly to temperature
            # This ensures each level gets the exact temperature needed for the corresponding system prompt
            # Note: Level 1 is handled directly in enhance_prompt method and should never reach here
            # This is just a fallback in case it somehow does
            if enhancement_level == 1:
                # Level 1: No enhancement - return original prompt
                logger.warning("Enhancement level 1 reached _enhance_with_xai, which should not happen")
                return prompt
            elif enhancement_level == 2:
                temperature = 0.2  # Level 2: Minimal enhancements
            elif enhancement_level == 3:
                temperature = 0.3  # Level 3: Light enhancements
            elif enhancement_level == 4:
                temperature = 0.4  # Level 4: Moderate enhancements
            elif enhancement_level == 5:
                temperature = 0.5  # Level 5: Balanced enhancements
            elif enhancement_level == 6:
                temperature = 0.6  # Level 6: Notable enhancements
            elif enhancement_level == 7:
                temperature = 0.7  # Level 7: Significant enhancements
            elif enhancement_level == 8:
                temperature = 0.8  # Level 8: Extensive enhancements
            elif enhancement_level == 9:
                temperature = 0.9  # Level 9: Substantial enhancements
            else:  # enhancement_level == 10
                temperature = 1.0  # Level 10: Maximum enhancements

            # We don't use the system_prompt parameter directly because
            # the XAI provider generates its own system prompt based on temperature
            # Generate the enhanced prompt
            enhanced_prompt = await xai_provider.generate_response(prompt, temperature)

            logger.info(f"Enhanced prompt with XAI: {enhanced_prompt}")
            return enhanced_prompt

        except Exception as e:
            logger.error(f"Error enhancing prompt with XAI: {str(e)}", exc_info=True)
            return prompt
