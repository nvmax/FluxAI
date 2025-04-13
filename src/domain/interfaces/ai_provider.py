"""
Interface for AI providers.
"""

from abc import ABC, abstractmethod
from typing import Optional

class AIProvider(ABC):
    """Interface for AI providers"""
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test the connection to the provider.
        
        Returns:
            True if the connection is successful, False otherwise
        """
        pass

    @abstractmethod
    async def generate_response(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Generate an enhanced prompt using the provider's API.
        
        Args:
            prompt: The prompt to enhance
            temperature: Temperature for generation (controls creativity)
            
        Returns:
            The enhanced prompt
        """
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """
        Get the base URL for the provider's API.
        
        Returns:
            The base URL
        """
        pass
        
    @abstractmethod
    def get_system_prompt(self, temperature: float) -> str:
        """
        Get the system prompt for the provider.
        
        Args:
            temperature: Temperature for generation (controls creativity)
            
        Returns:
            The system prompt
        """
        pass
