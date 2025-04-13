"""
Service for generating images using ComfyUI.
"""

import os
import json
import logging
import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple, Callable, Union

from src.domain.models.queue_item import QueueItem, RequestItem, ReduxRequestItem, ReduxPromptRequestItem
from src.domain.events.event_bus import EventBus
from src.domain.events.common_events import ImageGenerationCompletedEvent, ImageGenerationFailedEvent
from src.infrastructure.comfyui.comfyui_service import ComfyUIService
from src.infrastructure.config.config_manager import ConfigManager
from src.application.analytics.analytics_service import AnalyticsService
from src.infrastructure.database.image_repository import ImageRepository

logger = logging.getLogger(__name__)

class ImageGenerationService:
    """
    Service for generating images using ComfyUI.
    Handles the actual image generation process.
    """

    def __init__(self,
                 comfyui_service: ComfyUIService,
                 analytics_service: AnalyticsService,
                 config_manager: ConfigManager,
                 image_repository: Optional[ImageRepository] = None,
                 bot=None):
        """
        Initialize the image generation service.

        Args:
            comfyui_service: Service for interacting with ComfyUI
            analytics_service: Service for tracking analytics
            config_manager: Configuration manager
            image_repository: Repository for storing image generation data
            bot: Discord bot instance
        """
        self.comfyui_service = comfyui_service
        self.analytics_service = analytics_service
        self.config_manager = config_manager
        self.image_repository = image_repository
        self.bot = bot
        self.event_bus = EventBus()

    async def generate_image(self,
                            queue_item: QueueItem,
                            progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Generate an image using ComfyUI.

        Args:
            queue_item: Queue item containing the request
            progress_callback: Callback function for progress updates

        Returns:
            Tuple of (success, image_path, generation_time)
        """
        request_item = queue_item.request_item
        request_id = queue_item.request_id

        # Log the request ID for debugging
        if self.bot:
            logger.info(f"Processing request ID: {request_id} from pending_requests: {request_id in self.bot.pending_requests}")
            if request_id in self.bot.pending_requests:
                logger.info(f"Found request in pending_requests: {self.bot.pending_requests[request_id].channel_id}, {self.bot.pending_requests[request_id].original_message_id}")
        else:
            logger.warning(f"No bot reference available for request ID: {request_id}")

        try:
            logger.info(f"Starting image generation for request {request_id}")

            # Load workflow
            if isinstance(request_item, RequestItem):
                # Standard image generation
                workflow_file = request_item.workflow_filename or self.config_manager.flux_version
                workflow = self.config_manager.load_json(workflow_file)

                # Add LoRA trigger words to prompt if needed
                is_video = getattr(request_item, 'is_video', False)
                is_pulid = getattr(request_item, 'is_pulid', False)

                # Only add trigger words for standard and PuLID workflows, not for video
                if not is_video and request_item.loras:
                    # Import LoraManager here to avoid circular imports
                    from src.domain.lora_management.lora_manager import LoraManager
                    lora_manager = LoraManager()

                    # Get the list of LoRA filenames
                    lora_filenames = [lora['lora'] if isinstance(lora, dict) else lora for lora in request_item.loras]

                    # Add trigger words to prompt
                    enhanced_prompt = lora_manager.add_trigger_words_to_prompt(request_item.prompt, lora_filenames)
                    logger.info(f"Enhanced prompt with LoRA trigger words: {enhanced_prompt}")
                else:
                    enhanced_prompt = request_item.prompt

                # Update workflow with request parameters
                workflow = self.comfyui_service.update_workflow(
                    workflow=workflow,
                    prompt=enhanced_prompt,  # Use the enhanced prompt with trigger words
                    resolution=request_item.resolution,
                    loras=request_item.loras,
                    upscale_factor=request_item.upscale_factor,
                    seed=request_item.seed,
                    is_video=is_video,  # Pass is_video parameter
                    is_pulid=is_pulid   # Pass is_pulid parameter
                )

            elif isinstance(request_item, ReduxRequestItem):
                # Redux image generation
                workflow_file = request_item.workflow_filename
                logger.info(f"Loading Redux workflow from {workflow_file}")
                workflow = self.config_manager.load_json(workflow_file)

                if not workflow:
                    logger.error(f"Failed to load Redux workflow from {workflow_file}")
                    # Try loading directly from config directory as a fallback
                    direct_path = os.path.join('config', 'Redux.json')
                    logger.info(f"Trying to load Redux workflow directly from {direct_path}")
                    if os.path.exists(direct_path):
                        with open(direct_path, 'r', encoding='utf-8') as f:
                            workflow = json.loads(f.read())
                        logger.info(f"Successfully loaded Redux workflow directly from {direct_path}")
                    else:
                        logger.error(f"Could not find Redux workflow at {direct_path}")
                        return False, None, None

                # Log the seed value
                logger.info(f"Using seed {request_item.seed} for Redux workflow")

                # Update workflow with request parameters
                workflow = self.comfyui_service.update_redux_workflow(
                    workflow=workflow,
                    image1_path=request_item.image1_path,
                    image2_path=request_item.image2_path,
                    strength1=request_item.strength1,
                    strength2=request_item.strength2,
                    resolution=request_item.resolution,
                    seed=request_item.seed  # Pass the seed parameter
                )

            elif isinstance(request_item, ReduxPromptRequestItem):
                # Redux prompt image generation
                workflow_file = request_item.workflow_filename
                workflow = self.config_manager.load_json(workflow_file)

                # Add LoRA trigger words to prompt if needed
                if request_item.loras:
                    # Import LoraManager here to avoid circular imports
                    from src.domain.lora_management.lora_manager import LoraManager
                    lora_manager = LoraManager()

                    # Get the list of LoRA filenames
                    lora_filenames = [lora['lora'] if isinstance(lora, dict) else lora for lora in request_item.loras]

                    # Add trigger words to prompt
                    enhanced_prompt = lora_manager.add_trigger_words_to_prompt(request_item.prompt, lora_filenames)
                    logger.info(f"Enhanced ReduxPrompt prompt with LoRA trigger words: {enhanced_prompt}")
                else:
                    enhanced_prompt = request_item.prompt

                # Update workflow with request parameters
                workflow = self.comfyui_service.update_reduxprompt_workflow(
                    workflow=workflow,
                    image_path=request_item.image_path,
                    prompt=enhanced_prompt,  # Use the enhanced prompt with trigger words
                    strength=request_item.strength,
                    resolution=request_item.resolution,
                    loras=request_item.loras,
                    upscale_factor=request_item.upscale_factor
                )

            else:
                raise ValueError(f"Unknown request item type: {type(request_item)}")

            # Save the workflow to a temporary file in the output directory
            import json
            os.makedirs('output', exist_ok=True)
            temp_workflow_path = os.path.join('output', f"temp_workflow_{request_id}.json")

            # Check if workflow is valid
            if not workflow:
                logger.error("Workflow is empty or invalid")
                return False, None, None

            # For Redux requests, directly modify the workflow here to ensure it's updated
            if isinstance(request_item, ReduxRequestItem):
                logger.info(f"Directly updating Redux workflow before saving")

                # Ensure paths are absolute with forward slashes
                image1_path = os.path.abspath(request_item.image1_path).replace('\\', '/')
                image2_path = os.path.abspath(request_item.image2_path).replace('\\', '/')

                # Verify that the image files exist
                if not os.path.exists(image1_path):
                    logger.error(f"Image 1 file does not exist: {image1_path}")
                else:
                    logger.info(f"Image 1 file exists: {image1_path}")

                if not os.path.exists(image2_path):
                    logger.error(f"Image 2 file does not exist: {image2_path}")
                else:
                    logger.info(f"Image 2 file exists: {image2_path}")

                # Update image paths
                if '40' in workflow and 'inputs' in workflow['40']:
                    workflow['40']['inputs']['image'] = image1_path
                    logger.info(f"Directly updated image 1 path in node 40: {image1_path}")
                else:
                    logger.warning("Node 40 (image 1 node) not found in workflow")

                if '46' in workflow and 'inputs' in workflow['46']:
                    workflow['46']['inputs']['image'] = image2_path
                    logger.info(f"Directly updated image 2 path in node 46: {image2_path}")
                else:
                    logger.warning("Node 46 (image 2 node) not found in workflow")

                # Update strengths
                if '41' in workflow and 'inputs' in workflow['41'] and 'strength' in workflow['41']['inputs']:
                    workflow['41']['inputs']['strength'] = request_item.strength1
                    logger.info(f"Directly updated strength 1 in node 41: {request_item.strength1}")
                else:
                    logger.warning("Node 41 (strength 1 node) not found in workflow")

                if '48' in workflow and 'inputs' in workflow['48'] and 'strength' in workflow['48']['inputs']:
                    workflow['48']['inputs']['strength'] = request_item.strength2
                    logger.info(f"Directly updated strength 2 in node 48: {request_item.strength2}")
                else:
                    logger.warning("Node 48 (strength 2 node) not found in workflow")

                # Update resolution
                if '49' in workflow and 'inputs' in workflow['49'] and 'ratio_selected' in workflow['49']['inputs']:
                    workflow['49']['inputs']['ratio_selected'] = request_item.resolution
                    logger.info(f"Directly updated resolution in node 49: {request_item.resolution}")
                else:
                    logger.warning("Node 49 (resolution node) not found in workflow")

                # Update seed
                if '25' in workflow and 'inputs' in workflow['25'] and 'noise_seed' in workflow['25']['inputs']:
                    old_seed = workflow['25']['inputs']['noise_seed']
                    workflow['25']['inputs']['noise_seed'] = request_item.seed
                    logger.info(f"Directly updated seed in node 25 from {old_seed} to {request_item.seed}")
                else:
                    logger.warning("Node 25 (seed node) not found in workflow")

                # Log workflow details for debugging
                logger.info(f"Checking updated Redux workflow nodes:")
                logger.info(f"Node 25 (RandomNoise) exists: {'25' in workflow}")
                if '25' in workflow and 'inputs' in workflow['25']:
                    logger.info(f"Node 25 noise_seed: {workflow['25']['inputs'].get('noise_seed', 'not found')}")

                logger.info(f"Node 40 (Image1) exists: {'40' in workflow}")
                if '40' in workflow and 'inputs' in workflow['40']:
                    logger.info(f"Node 40 image path: {workflow['40']['inputs'].get('image', 'not found')}")

                logger.info(f"Node 46 (Image2) exists: {'46' in workflow}")
                if '46' in workflow and 'inputs' in workflow['46']:
                    logger.info(f"Node 46 image path: {workflow['46']['inputs'].get('image', 'not found')}")

                logger.info(f"Node 49 (Resolution) exists: {'49' in workflow}")
                if '49' in workflow and 'inputs' in workflow['49']:
                    logger.info(f"Node 49 resolution: {workflow['49']['inputs'].get('ratio_selected', 'not found')}")

            # Save the workflow
            with open(temp_workflow_path, 'w') as f:
                json.dump(workflow, f)
            logger.info(f"Saved temporary workflow to {temp_workflow_path}")

            # Get server address and bot server address
            server_address = "127.0.0.1:8188"
            bot_server = "localhost"

            # Add to pending requests for progress updates
            if self.bot and hasattr(self.bot, 'pending_requests'):
                self.bot.pending_requests[request_id] = request_item
                logger.info(f"Added request {request_id} to pending_requests from ImageGenerationService")

            # Save to database if image repository is available
            if self.image_repository:
                await self.image_repository.save_image_generation(
                    request_id=request_id,
                    request_item=request_item
                )

            # Launch a separate process to handle the image generation
            import subprocess
            # Determine the request type
            if request_item.is_video:
                request_type = "video"
            elif hasattr(request_item, 'is_pulid') and request_item.is_pulid:
                request_type = "pulid"
            else:
                request_type = "standard"

            subprocess.Popen([
                "python",
                "comfygen.py",
                request_id,
                request_item.user_id,
                str(request_item.channel_id),
                "0",  # interaction_id (not used in our case)
                str(request_item.original_message_id),
                request_type,
                request_item.prompt,
                request_item.resolution,
                json.dumps(request_item.loras),
                str(request_item.upscale_factor),
                temp_workflow_path,
                str(request_item.seed) if request_item.seed is not None else "None"
            ])

            # Send initial progress update
            if self.bot and request_id in self.bot.pending_requests:
                try:
                    # Get the request item from pending_requests
                    pending_request = self.bot.pending_requests[request_id]

                    # Get the channel and message
                    channel = await self.bot.fetch_channel(pending_request.channel_id)
                    message = await channel.fetch_message(pending_request.original_message_id)

                    # Update the message with initial progress
                    await message.edit(content=f"⚙️ Starting generation process...")
                except Exception as e:
                    logger.error(f"Error sending initial progress update: {e}")

            # Return success immediately, the separate process will handle the rest
            return True, None, 0

        except Exception as e:
            logger.error(f"Error generating image: {e}")

            # Publish event
            self.event_bus.publish(ImageGenerationFailedEvent(
                request_id=request_id,
                user_id=request_item.user_id,
                error_message=str(e)
            ))

            return False, None, None
