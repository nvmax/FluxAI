"""
AI providers for the application.
"""

from src.infrastructure.ai_providers.provider_factory import AIProviderFactory
from src.infrastructure.ai_providers.openai_provider import OpenAIProvider
from src.infrastructure.ai_providers.anthropic_provider import AnthropicProvider
from src.infrastructure.ai_providers.lmstudio_provider import LMStudioProvider
from src.infrastructure.ai_providers.xai_provider import XAIProvider

# Register providers
AIProviderFactory.register_provider("openai", OpenAIProvider)
AIProviderFactory.register_provider("anthropic", AnthropicProvider)
AIProviderFactory.register_provider("lmstudio", LMStudioProvider)
AIProviderFactory.register_provider("xai", XAIProvider)