"""
Interface for analytics data access.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

class AnalyticsRepository(ABC):
    """Interface for analytics data access"""
    
    @abstractmethod
    async def record_command_usage(self, 
                                  command_name: str, 
                                  user_id: str,
                                  guild_id: Optional[str] = None,
                                  channel_id: Optional[str] = None,
                                  execution_time: Optional[float] = None,
                                  success: bool = True) -> bool:
        """
        Record command usage.
        
        Args:
            command_name: Name of the command
            user_id: ID of the user who executed the command
            guild_id: ID of the guild where the command was executed
            channel_id: ID of the channel where the command was executed
            execution_time: Time taken to execute the command
            success: Whether the command was successful
            
        Returns:
            True if successful, False otherwise
        """
        pass
        
    @abstractmethod
    async def record_user_activity(self,
                                  user_id: str,
                                  action_type: str,
                                  guild_id: Optional[str] = None,
                                  details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Record user activity.
        
        Args:
            user_id: ID of the user
            action_type: Type of action
            guild_id: ID of the guild where the action occurred
            details: Additional details about the action
            
        Returns:
            True if successful, False otherwise
        """
        pass
        
    @abstractmethod
    async def record_image_generation(self,
                                     user_id: str,
                                     prompt: str,
                                     resolution: str,
                                     loras: str,
                                     upscale_factor: int,
                                     generation_time: float,
                                     is_video: bool = False,
                                     generation_type: str = "standard") -> bool:
        """
        Record image generation.
        
        Args:
            user_id: ID of the user
            prompt: Prompt used for generation
            resolution: Resolution of the generated image
            loras: LoRAs used for generation
            upscale_factor: Upscale factor
            generation_time: Time taken to generate the image
            is_video: Whether the generation is a video
            generation_type: Type of generation (standard, redux, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        pass
        
    @abstractmethod
    async def get_command_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get command usage statistics.
        
        Args:
            days: Number of days to get statistics for
            
        Returns:
            Command usage statistics
        """
        pass
        
    @abstractmethod
    async def get_user_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get user activity statistics.
        
        Args:
            days: Number of days to get statistics for
            
        Returns:
            User activity statistics
        """
        pass
        
    @abstractmethod
    async def get_image_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get image generation statistics.
        
        Args:
            days: Number of days to get statistics for
            
        Returns:
            Image generation statistics
        """
        pass
        
    @abstractmethod
    async def get_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get daily statistics.
        
        Args:
            days: Number of days to get statistics for
            
        Returns:
            Daily statistics
        """
        pass
        
    @abstractmethod
    async def reset_analytics(self) -> bool:
        """
        Reset all analytics data.
        
        Returns:
            True if successful, False otherwise
        """
        pass
