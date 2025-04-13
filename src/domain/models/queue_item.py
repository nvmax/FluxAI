"""
Queue item model.
"""

import time
import json
from typing import Dict, Any, Optional, Union, List
from enum import IntEnum, Enum

class QueuePriority(IntEnum):
    """Priority levels for queue items"""
    HIGH = 1
    NORMAL = 2
    LOW = 3

class QueueStatus(str, Enum):
    """Status values for queue items"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class RequestItem:
    """Base request item model"""

    def __init__(self,
                 id: str,
                 user_id: str,
                 channel_id: str,
                 interaction_id: str,
                 original_message_id: str,
                 prompt: str,
                 resolution: str,
                 loras: List[Dict[str, Any]],
                 upscale_factor: int = 1,
                 workflow_filename: Optional[str] = None,
                 seed: Optional[int] = None,
                 is_pulid: bool = False,
                 is_video: bool = False):
        self.id = id
        self.user_id = user_id
        self.channel_id = channel_id
        self.interaction_id = interaction_id
        self.original_message_id = original_message_id
        self.prompt = prompt
        self.resolution = resolution
        self.loras = loras
        self.upscale_factor = upscale_factor
        self.workflow_filename = workflow_filename
        self.seed = seed
        self.is_pulid = is_pulid
        self.is_video = is_video

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "interaction_id": self.interaction_id,
            "original_message_id": self.original_message_id,
            "prompt": self.prompt,
            "resolution": self.resolution,
            "loras": self.loras,
            "upscale_factor": self.upscale_factor,
            "workflow_filename": self.workflow_filename,
            "seed": self.seed,
            "is_pulid": self.is_pulid,
            "is_video": self.is_video
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RequestItem':
        """Create from dictionary"""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            channel_id=data["channel_id"],
            interaction_id=data["interaction_id"],
            original_message_id=data["original_message_id"],
            prompt=data["prompt"],
            resolution=data["resolution"],
            loras=data["loras"],
            upscale_factor=data["upscale_factor"],
            workflow_filename=data.get("workflow_filename"),
            seed=data.get("seed"),
            is_pulid=data.get("is_pulid", False),
            is_video=data.get("is_video", False)
        )

class ReduxRequestItem(RequestItem):
    """Redux request item model"""

    def __init__(self,
                 id: str,
                 user_id: str,
                 channel_id: str,
                 interaction_id: str,
                 original_message_id: str,
                 resolution: str,
                 strength1: float,
                 strength2: float,
                 workflow_filename: str,
                 image1_path: str,
                 image2_path: str,
                 is_redux: bool = False,
                 seed: int = None):
        super().__init__(
            id=id,
            user_id=user_id,
            channel_id=channel_id,
            interaction_id=interaction_id,
            original_message_id=original_message_id,
            prompt="",  # Redux doesn't use a prompt
            resolution=resolution,
            loras=[],  # Redux doesn't use LoRAs directly
            workflow_filename=workflow_filename,
            is_video=False,
            is_pulid=False,
            seed=seed  # Pass the seed to the parent class
        )
        # Always set is_redux to True for ReduxRequestItem instances
        self.is_redux = True
        self.strength1 = strength1
        self.strength2 = strength2
        self.image1_path = image1_path
        self.image2_path = image2_path

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = super().to_dict()
        data.update({
            "strength1": self.strength1,
            "strength2": self.strength2,
            "image1_path": self.image1_path,
            "image2_path": self.image2_path,
            "is_redux": self.is_redux,
            "type": "redux"
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReduxRequestItem':
        """Create from dictionary"""
        # Create the instance with is_redux=True to ensure it's always set
        instance = cls(
            id=data["id"],
            user_id=data["user_id"],
            channel_id=data["channel_id"],
            interaction_id=data["interaction_id"],
            original_message_id=data["original_message_id"],
            resolution=data["resolution"],
            strength1=data["strength1"],
            strength2=data["strength2"],
            workflow_filename=data["workflow_filename"],
            image1_path=data["image1_path"],
            image2_path=data["image2_path"],
            is_redux=True,  # Always set to True for ReduxRequestItem
            seed=data.get("seed", None)
        )

        # Explicitly set the is_redux attribute to ensure it's properly set
        instance.is_redux = True

        return instance

class ReduxPromptRequestItem(RequestItem):
    """Redux prompt request item model"""

    def __init__(self,
                 id: str,
                 user_id: str,
                 channel_id: str,
                 interaction_id: str,
                 original_message_id: str,
                 prompt: str,
                 resolution: str,
                 loras: List[Dict[str, Any]],
                 upscale_factor: int,
                 workflow_filename: str,
                 image_path: str,
                 strength: float):
        super().__init__(
            id=id,
            user_id=user_id,
            channel_id=channel_id,
            interaction_id=interaction_id,
            original_message_id=original_message_id,
            prompt=prompt,
            resolution=resolution,
            loras=loras,
            upscale_factor=upscale_factor,
            workflow_filename=workflow_filename
        )
        self.image_path = image_path
        self.strength = strength

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = super().to_dict()
        data.update({
            "image_path": self.image_path,
            "strength": self.strength,
            "type": "reduxprompt"
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReduxPromptRequestItem':
        """Create from dictionary"""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            channel_id=data["channel_id"],
            interaction_id=data["interaction_id"],
            original_message_id=data["original_message_id"],
            prompt=data["prompt"],
            resolution=data["resolution"],
            loras=data["loras"],
            upscale_factor=data["upscale_factor"],
            workflow_filename=data["workflow_filename"],
            image_path=data["image_path"],
            strength=data["strength"]
        )

class QueueItem:
    """Queue item model"""

    def __init__(self,
                 request_id: str,
                 request_item: Union[RequestItem, ReduxRequestItem, ReduxPromptRequestItem],
                 priority: int = QueuePriority.NORMAL,
                 user_id: Optional[str] = None,
                 added_at: Optional[float] = None):
        self.request_id = request_id
        self.request_item = request_item
        self.priority = priority
        self.user_id = user_id or request_item.user_id
        self.added_at = added_at or time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.status = QueueStatus.PENDING
        self.error_message: Optional[str] = None

    def __lt__(self, other):
        """Less than comparison for priority queue"""
        if not isinstance(other, QueueItem):
            return NotImplemented
        return (self.priority, self.added_at) < (other.priority, other.added_at)

    def __eq__(self, other):
        """Equality comparison"""
        if not isinstance(other, QueueItem):
            return NotImplemented
        return self.request_id == other.request_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "request_id": self.request_id,
            "request_item": self.request_item.to_dict(),
            "priority": self.priority,
            "user_id": self.user_id,
            "added_at": self.added_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status.value,
            "error_message": self.error_message
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueueItem':
        """Create from dictionary"""
        request_data = data["request_item"]

        # Determine the type of request item
        if request_data.get("type") == "redux":
            request_item = ReduxRequestItem.from_dict(request_data)
        elif request_data.get("type") == "reduxprompt":
            request_item = ReduxPromptRequestItem.from_dict(request_data)
        else:
            request_item = RequestItem.from_dict(request_data)

        item = cls(
            request_id=data["request_id"],
            request_item=request_item,
            priority=data["priority"],
            user_id=data["user_id"],
            added_at=data["added_at"]
        )

        item.started_at = data.get("started_at")
        item.completed_at = data.get("completed_at")
        item.status = QueueStatus(data["status"])
        item.error_message = data.get("error_message")

        return item
