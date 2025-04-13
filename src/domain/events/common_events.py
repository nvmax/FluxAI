"""
Common domain events used throughout the application.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from .event_bus import Event

class ImageGenerationRequestedEvent(Event):
    """Event raised when an image generation is requested"""
    
    def __init__(self, 
                 request_id: str, 
                 user_id: str, 
                 prompt: str, 
                 resolution: str,
                 loras: List[Dict[str, Any]] = None,
                 upscale_factor: int = 1,
                 seed: Optional[int] = None,
                 is_video: bool = False,
                 generation_type: str = "standard"):
        self.request_id = request_id
        self.user_id = user_id
        self.prompt = prompt
        self.resolution = resolution
        self.loras = loras or []
        self.upscale_factor = upscale_factor
        self.seed = seed
        self.timestamp = datetime.now()
        self.is_video = is_video
        self.generation_type = generation_type

class ImageGenerationCompletedEvent(Event):
    """Event raised when an image generation is completed"""
    
    def __init__(self, 
                 request_id: str, 
                 user_id: str,
                 image_path: str,
                 generation_time: float,
                 is_video: bool = False,
                 generation_type: str = "standard"):
        self.request_id = request_id
        self.user_id = user_id
        self.image_path = image_path
        self.generation_time = generation_time
        self.timestamp = datetime.now()
        self.is_video = is_video
        self.generation_type = generation_type

class ImageGenerationFailedEvent(Event):
    """Event raised when an image generation fails"""
    
    def __init__(self, 
                 request_id: str, 
                 user_id: str,
                 error_message: str,
                 is_video: bool = False,
                 generation_type: str = "standard"):
        self.request_id = request_id
        self.user_id = user_id
        self.error_message = error_message
        self.timestamp = datetime.now()
        self.is_video = is_video
        self.generation_type = generation_type

class CommandExecutedEvent(Event):
    """Event raised when a command is executed"""
    
    def __init__(self, 
                 command_name: str, 
                 user_id: str,
                 guild_id: Optional[str] = None,
                 channel_id: Optional[str] = None,
                 execution_time: Optional[float] = None,
                 success: bool = True):
        self.command_name = command_name
        self.user_id = user_id
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.execution_time = execution_time
        self.success = success
        self.timestamp = datetime.now()

class UserActivityEvent(Event):
    """Event raised when a user performs an activity"""
    
    def __init__(self, 
                 user_id: str,
                 action_type: str,
                 guild_id: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.user_id = user_id
        self.action_type = action_type
        self.guild_id = guild_id
        self.details = details or {}
        self.timestamp = datetime.now()

class ContentFilterViolationEvent(Event):
    """Event raised when a content filter violation is detected"""
    
    def __init__(self, 
                 user_id: str,
                 prompt: str,
                 violation_type: str,
                 violation_details: str):
        self.user_id = user_id
        self.prompt = prompt
        self.violation_type = violation_type
        self.violation_details = violation_details
        self.timestamp = datetime.now()
