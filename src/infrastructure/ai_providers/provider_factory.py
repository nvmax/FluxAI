"""
Factory for creating AI provider instances.
"""

import logging
from typing import Dict, Type, Optional
from src.domain.interfaces.ai_provider import AIProvider
from src.infrastructure.config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class AIProviderFactory:
    """
    Factory for creating AI provider instances.
    Manages the creation and caching of AI provider instances.
    """
    
    _providers: Dict[str, Type[AIProvider]] = {}
    _instances: Dict[str, AIProvider] = {}
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[AIProvider]):
        """
        Register a provider class.
        
        Args:
            name: Name of the provider
            provider_class: Provider class
        """
        cls._providers[name.lower()] = provider_class
        logger.debug(f"Registered AI provider: {name}")
        
    @classmethod
    def get_provider(cls, name: str) -> Optional[AIProvider]:
        """
        Get a provider instance.
        
        Args:
            name: Name of the provider
            
        Returns:
            Provider instance or None if not found
        """
        name = name.lower()
        
        # Return cached instance if available
        if name in cls._instances:
            return cls._instances[name]
            
        # Create new instance if provider is registered
        if name in cls._providers:
            try:
                provider = cls._providers[name]()
                cls._instances[name] = provider
                logger.debug(f"Created AI provider instance: {name}")
                return provider
            except Exception as e:
                logger.error(f"Error creating AI provider {name}: {e}")
                return None
                
        logger.warning(f"Unknown AI provider: {name}")
        return None
        
    @classmethod
    def get_default_provider(cls) -> Optional[AIProvider]:
        """
        Get the default provider instance.
        
        Returns:
            Default provider instance or None if not available
        """
        config = ConfigManager()
        return cls.get_provider(config.ai_provider)
