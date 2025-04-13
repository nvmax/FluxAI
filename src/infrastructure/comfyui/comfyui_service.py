"""
Service for interacting with ComfyUI.
"""

import os
import json
import logging
import asyncio
import uuid
import time
import random
import websocket
from typing import Dict, Any, List, Optional, Tuple, Callable
from pathlib import Path

logger = logging.getLogger(__name__)

class ComfyUIService:
    """
    Service for interacting with ComfyUI.
    Provides methods for generating images and managing workflows.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one ComfyUI service exists"""
        if cls._instance is None:
            cls._instance = super(ComfyUIService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, server_address: str = "127.0.0.1:8188"):
        """
        Initialize the ComfyUI service.

        Args:
            server_address: Address of the ComfyUI server
        """
        # Only initialize once (singleton pattern)
        if self._initialized:
            return

        self.server_address = server_address
        self._initialized = True

    def connect(self):
        """
        Connect to the ComfyUI server.

        Returns:
            WebSocket connection
        """
        try:
            # Generate a client ID
            client_id = str(uuid.uuid4())

            # Connect to the WebSocket with the client ID
            ws_url = f"ws://{self.server_address}/ws?clientId={client_id}"
            logger.info(f"Connecting to ComfyUI server at {ws_url}")
            connection = websocket.create_connection(ws_url, timeout=120)
            logger.info(f"Successfully connected to ComfyUI server with client ID {client_id}")
            return connection
        except Exception as e:
            logger.error(f"Error connecting to ComfyUI server: {e}")
            raise

    def clear_cache(self, ws):
        """
        Clear the ComfyUI cache.

        Args:
            ws: WebSocket connection
        """
        try:
            ws.send(json.dumps({"type": "clear"}))
            logger.debug("Cleared ComfyUI cache")
        except Exception as e:
            logger.error(f"Error clearing ComfyUI cache: {e}")
            raise

    def queue_prompt(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Queue a prompt with ComfyUI using the HTTP API.

        Args:
            workflow: Workflow to use for generation

        Returns:
            Response from ComfyUI
        """
        try:
            # Create a client ID
            client_id = str(uuid.uuid4())

            # Create the request data
            request_data = {
                "prompt": workflow,
                "client_id": client_id
            }

            # Convert to JSON with minimal whitespace
            json_str = json.dumps(request_data, ensure_ascii=False, separators=(',', ':'))

            # Log the request data for debugging
            logger.debug(f"Sending request to ComfyUI prompt endpoint")
            logger.debug(f"Client ID: {client_id}")
            logger.debug(f"Request size: {len(json_str)} bytes")

            # Encode as UTF-8
            data = json_str.encode('utf-8')

            # Create and configure the request
            url = f"http://{self.server_address}/prompt"
            headers = {
                'Content-Type': 'application/json',
                'Content-Length': str(len(data))
            }

            logger.info(f"Sending request to URL: {url}")
            logger.debug(f"Headers: {headers}")

            import urllib.request
            req = urllib.request.Request(
                url,
                data=data,
                method="POST",
                headers=headers
            )

            # Send the request with error handling
            try:
                with urllib.request.urlopen(req, timeout=120) as response:
                    response_data = response.read().decode('utf-8')
                    result = json.loads(response_data)
                    if not isinstance(result, dict):
                        raise ValueError("Expected dictionary response from ComfyUI")
                    logger.info("Successfully queued prompt with ComfyUI")
                    return result
            except urllib.error.HTTPError as e:
                logger.error(f"HTTP Error: {e.code} - {e.reason}")
                logger.error(f"Response body: {e.read().decode('utf-8')}")
                raise
            except urllib.error.URLError as e:
                logger.error(f"URL Error: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"Error in queue_prompt: {str(e)}")
            raise

    def get_images(self,
                  ws,
                  workflow: Dict[str, Any],
                  progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Tuple[Dict[str, List[Tuple[bytes, str]]], float]:
        """
        Generate images using ComfyUI.

        Args:
            ws: WebSocket connection
            workflow: Workflow to use for generation
            progress_callback: Callback function for progress updates

        Returns:
            Tuple of (images, generation_time)
        """
        try:
            # Start timing
            start_time = time.time()

            # Queue the prompt using HTTP API
            prompt_response = self.queue_prompt(workflow)
            if 'prompt_id' not in prompt_response:
                raise ValueError("No prompt_id in response from queue_prompt")

            prompt_id = prompt_response['prompt_id']
            logger.info(f"Queued prompt with ID: {prompt_id}")

            # Create a result container
            import threading
            import queue
            result_queue = queue.Queue()
            error_queue = queue.Queue()

            # Define a function to run in a separate thread
            def websocket_thread():
                try:
                    last_milestone = 0

                    while True:
                        try:
                            # Set a timeout for the websocket receive operation
                            ws.settimeout(5.0)  # 5 second timeout

                            try:
                                logger.debug("Waiting for websocket message...")
                                out = ws.recv()
                                logger.debug(f"Received websocket message: {out[:100] if isinstance(out, str) else 'binary data'}...")
                            except websocket.WebSocketTimeoutException:
                                logger.warning("Websocket receive timed out, retrying...")
                                continue

                            if not isinstance(out, str):
                                continue

                            try:
                                message = json.loads(out)

                                # Skip monitoring messages
                                if message.get('type') == 'crystools.monitor':
                                    continue

                                # Log important messages
                                if message.get('type') not in ['status']:
                                    logger.info(f"Received important websocket message: {message}")
                            except json.JSONDecodeError as e:
                                logger.error(f"Error parsing WebSocket message: {e}")
                                continue

                            # Process the message based on its type
                            if message['type'] == 'execution_start':
                                if progress_callback:
                                    progress_callback({
                                        "status": "execution",
                                        "message": "Starting execution..."
                                    })

                            elif message['type'] == 'execution_cached':
                                if progress_callback:
                                    progress_callback({
                                        "status": "cached",
                                        "message": "Using cached result..."
                                    })

                            elif message['type'] == 'progress':
                                value = message['data']['value']
                                max_value = message['data'].get('max_value', 1)
                                if max_value == 0:
                                    max_value = 1  # Avoid division by zero

                                progress = int((value / max_value) * 100)

                                # Only update progress at 5% intervals to reduce spam
                                milestone = progress // 5
                                if milestone > last_milestone:
                                    last_milestone = milestone
                                    if progress_callback:
                                        progress_callback({
                                            "status": "generating",
                                            "progress": progress,
                                            "message": f"Generating image... {progress}%"
                                        })

                            elif message['type'] == 'executing':
                                if 'prompt_id' in message['data']:
                                    prompt_id = message['data']['prompt_id']
                                    logger.info(f"Executing prompt {prompt_id}")

                            elif message['type'] == 'executed':
                                if progress_callback:
                                    progress_callback({
                                        "status": "processing",
                                        "message": "Processing output..."
                                    })

                                # Get the outputs
                                outputs = {}
                                for node_id, node_output in message["data"]["output"].items():
                                    if "images" in node_output:
                                        images = []
                                        for image in node_output["images"]:
                                            image_data = self.get_image(image["filename"], image["subfolder"])
                                            images.append((image_data, image["filename"]))
                                        outputs[node_id] = images

                                # Put the outputs in the result queue
                                result_queue.put(outputs)
                                return

                            elif message['type'] == 'error':
                                error_message = message['data']['message']
                                logger.error(f"Error generating images: {error_message}")

                                if progress_callback:
                                    progress_callback({
                                        "status": "error",
                                        "message": f"Error: {error_message}"
                                    })

                                error_queue.put(Exception(f"ComfyUI error: {error_message}"))
                                return

                        except Exception as e:
                            logger.error(f"Error processing websocket message: {e}")
                            error_queue.put(e)
                            return

                except Exception as e:
                    logger.error(f"Error in websocket thread: {e}")
                    error_queue.put(e)

            # Start the websocket thread
            thread = threading.Thread(target=websocket_thread)
            thread.daemon = True
            thread.start()

            # Wait for the thread to finish or timeout
            timeout = 300  # 5 minutes
            start_wait_time = time.time()

            # Set a maximum time to wait for the thread
            max_wait_time = 300  # 5 minutes

            while thread.is_alive() and time.time() - start_wait_time < timeout:
                # Check if we have a result
                try:
                    outputs = result_queue.get_nowait()
                    generation_time = time.time() - start_time
                    logger.info(f"Generated images in {generation_time:.2f} seconds")

                    if progress_callback:
                        progress_callback({
                            "status": "complete",
                            "message": f"Generation complete in {generation_time:.2f} seconds"
                        })

                    return outputs, generation_time
                except queue.Empty:
                    pass

                # Check if we have an error
                try:
                    error = error_queue.get_nowait()
                    raise error
                except queue.Empty:
                    pass

                # Check if we've waited too long
                if time.time() - start_wait_time > max_wait_time:
                    logger.warning(f"Waited too long for websocket thread, timing out")
                    # Force the thread to stop
                    if thread.is_alive():
                        # We can't actually kill the thread, but we can raise an exception
                        logger.warning(f"Forcing timeout after {max_wait_time} seconds")
                        raise TimeoutError(f"Timed out waiting for ComfyUI to generate images after {max_wait_time} seconds")

                # Sleep a bit to avoid busy waiting
                time.sleep(0.1)

            # If we get here, either the thread is still running (timeout) or it finished without putting anything in the queues
            if thread.is_alive():
                logger.error(f"Timeout waiting for ComfyUI to generate images")
                raise Exception("Timeout waiting for ComfyUI to generate images")
            else:
                logger.error(f"Thread finished without result or error")
                raise Exception("Thread finished without result or error")
        except Exception as e:
            logger.error(f"Error generating images: {e}")
            raise

    def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """
        Get an image from ComfyUI.

        Args:
            filename: Name of the image file
            subfolder: Subfolder containing the image
            folder_type: Type of folder (output, input, temp)

        Returns:
            Image data
        """
        try:
            # Create URL parameters
            import urllib.parse
            data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
            url_values = urllib.parse.urlencode(data)
            url = f"http://{self.server_address}/view?{url_values}"

            logger.debug(f"Getting image from URL: {url}")

            # Use urllib to get the image
            import urllib.request
            with urllib.request.urlopen(url, timeout=120) as response:
                return response.read()
        except Exception as e:
            logger.error(f"Error getting image {filename}: {e}")
            raise

    def update_workflow(self,
                       workflow: Dict[str, Any],
                       prompt: str,
                       resolution: str,
                       loras: List[Dict[str, Any]],
                       upscale_factor: int = 1,
                       seed: Optional[int] = None,
                       is_video: bool = False,
                       is_pulid: bool = False) -> Dict[str, Any]:
        """
        Update a workflow with new parameters.

        Args:
            workflow: Workflow to update
            prompt: Prompt for image generation
            resolution: Resolution for image generation
            loras: LoRAs to use
            upscale_factor: Upscale factor
            seed: Seed for generation
            is_video: Whether this is a video workflow
            is_pulid: Whether this is a PuLID workflow

        Returns:
            Updated workflow
        """
        try:
            # Create a deep copy to avoid modifying the original
            workflow = json.loads(json.dumps(workflow))

            # If this is a video workflow, use different node IDs
            if is_video:
                # Update prompt - for video, node 44 is the prompt node
                if '44' in workflow:
                    workflow['44']['inputs']['text'] = prompt
                    logger.debug(f"Updated video prompt: {prompt}")
                else:
                    logger.warning("Node 44 (video prompt node) not found in workflow")

                # Update seed - for video, node 3 is the KSampler node
                if seed is None:
                    seed = random.randint(0, 2**32 - 1)

                if '3' in workflow:
                    workflow['3']['inputs']['seed'] = seed
                    logger.debug(f"Updated video seed: {seed}")
                else:
                    logger.warning("Node 3 (video KSampler node) not found in workflow")

                # For video, we don't update resolution or upscale factor
                # Just log that we're using the default values
                logger.debug(f"Using default video resolution and no upscale for video")

                # For video, we don't update LoRAs
                # Just log that we're not using LoRAs for video
                logger.debug(f"LoRAs not supported for video generation")
            elif is_pulid:
                # PuLID workflow
                # Update prompt - for PuLID, node 6 is the prompt node
                if '6' in workflow:
                    workflow['6']['inputs']['text'] = prompt
                    logger.debug(f"Updated PuLID prompt: {prompt}")
                else:
                    logger.warning("Node 6 (PuLID prompt node) not found in workflow")

                # Update resolution - for PuLID, node 70 is the resolution node
                if '70' in workflow:
                    workflow['70']['inputs']['ratio_selected'] = resolution
                    logger.debug(f"Updated PuLID resolution: {resolution}")
                else:
                    logger.warning("Node 70 (PuLID resolution node) not found in workflow")

                # Update seed - for PuLID, we need to find the appropriate seed node
                if seed is None:
                    seed = random.randint(0, 2**32 - 1)

                # Always generate a new random seed for PuLID workflows
                random_seed = random.randint(0, 2**32 - 1)
                logger.debug(f"Generated new random seed for PuLID workflow: {random_seed}")

                # Try different seed nodes that might be in the PuLID workflow
                seed_updated = False

                # Check for node 25 (RandomNoise) which uses noise_seed
                if '25' in workflow and 'noise_seed' in workflow['25']['inputs']:
                    workflow['25']['inputs']['noise_seed'] = random_seed
                    logger.debug(f"Updated PuLID noise_seed in node 25: {random_seed}")
                    seed_updated = True

                # Also check for other seed nodes that might use 'seed' parameter
                for seed_node_id in ['73']:
                    if seed_node_id in workflow and 'seed' in workflow[seed_node_id]['inputs']:
                        workflow[seed_node_id]['inputs']['seed'] = random_seed
                        logger.debug(f"Updated PuLID seed in node {seed_node_id}: {random_seed}")
                        seed_updated = True

                if not seed_updated:
                    logger.warning("No suitable seed node found in PuLID workflow")

                # Update strength in the ApplyPulidFlux node
                if '62' in workflow:
                    workflow['62']['inputs']['weight'] = 0.5  # Default strength for PuLID
                    logger.debug(f"Updated PuLID strength in node 62")
                else:
                    logger.warning("Node 62 (ApplyPulidFlux node) not found in PuLID workflow")

                # Update upscale factor - for PuLID, node 77 is the upscale factor node
                if '77' in workflow:
                    # Limit upscale factor to a maximum of 3 for PuLID workflows
                    limited_upscale = min(upscale_factor, 3)
                    workflow['77']['inputs']['float'] = limited_upscale
                    logger.debug(f"Updated PuLID upscale factor in node 77: {limited_upscale} (limited from {upscale_factor})")
                else:
                    logger.warning("Node 77 (PuLID upscale node) not found in PuLID workflow")

                # LoRAs are handled by the LoraManager
                logger.debug(f"Using LoRAs in PuLID workflow: {loras}")
            else:
                # Standard image workflow
                # Update prompt
                if '69' in workflow:
                    workflow['69']['inputs']['prompt'] = prompt
                    logger.debug(f"Updated prompt: {prompt}")
                else:
                    logger.warning("Node 69 (prompt node) not found in workflow")

                # Update resolution
                if '258' in workflow:
                    workflow['258']['inputs']['ratio_selected'] = resolution
                    logger.debug(f"Updated resolution: {resolution}")
                else:
                    logger.warning("Node 258 (resolution node) not found in workflow")

                # Update seed
                if seed is None:
                    seed = random.randint(0, 2**32 - 1)

                # Update seed in the RandomNoise node
                if '198:2' in workflow:
                    workflow['198:2']['inputs']['noise_seed'] = seed
                    logger.debug(f"Updated seed: {seed}")
                else:
                    logger.warning("Node 198:2 (RandomNoise node) not found in workflow")

                # Update LoRAs
                # The workflow uses Power Lora Loader which has a different structure
                # We don't need to update LoRAs directly in the workflow as they're handled by the prompt
                # Just log that we're using the LoRAs
                logger.debug(f"Using LoRAs: {loras}")

                # Update upscale factor in the CR Upscale Image node
                if '279' in workflow:
                    workflow['279']['inputs']['rescale_factor'] = upscale_factor
                    logger.debug(f"Updated upscale factor: {upscale_factor}")
                else:
                    logger.warning("Node 279 (CR Upscale Image node) not found in workflow")

            return workflow
        except Exception as e:
            logger.error(f"Error updating workflow: {e}")
            raise

    def update_redux_workflow(self,
                             workflow: Dict[str, Any],
                             image1_path: str,
                             image2_path: str,
                             strength1: float,
                             strength2: float,
                             resolution: str,
                             seed: Optional[int] = None) -> Dict[str, Any]:
        """
        Update a Redux workflow with new parameters.

        Args:
            workflow: Workflow to update
            image1_path: Path to the first image
            image2_path: Path to the second image
            strength1: Strength of the first image
            strength2: Strength of the second image
            resolution: Resolution for image generation
            seed: Seed for generation

        Returns:
            Updated workflow
        """
        try:
            # Create a deep copy to avoid modifying the original
            workflow = json.loads(json.dumps(workflow))

            # Ensure paths are absolute with forward slashes
            image1_path = os.path.abspath(image1_path).replace('\\', '/')
            image2_path = os.path.abspath(image2_path).replace('\\', '/')

            # Verify that the image files exist
            if not os.path.exists(image1_path):
                logger.error(f"Image 1 file does not exist: {image1_path}")
            else:
                logger.info(f"Image 1 file exists: {image1_path}")

            if not os.path.exists(image2_path):
                logger.error(f"Image 2 file does not exist: {image2_path}")
            else:
                logger.info(f"Image 2 file exists: {image2_path}")

            # Update image paths based on the Redux.json workflow structure
            # First image is in node 40
            if '40' in workflow and 'inputs' in workflow['40'] and 'image' in workflow['40']['inputs']:
                workflow['40']['inputs']['image'] = image1_path
                logger.info(f"Updated image 1 path in node 40: {image1_path}")
            else:
                logger.warning("Node 40 (image 1 node) not found in workflow or has unexpected structure")

            # Second image is in node 46
            if '46' in workflow and 'inputs' in workflow['46'] and 'image' in workflow['46']['inputs']:
                workflow['46']['inputs']['image'] = image2_path
                logger.info(f"Updated image 2 path in node 46: {image2_path}")
            else:
                logger.warning("Node 46 (image 2 node) not found in workflow or has unexpected structure")

            # Update strengths
            # Strength 1 is in node 41 (StyleModelApply)
            if '41' in workflow and 'inputs' in workflow['41'] and 'strength' in workflow['41']['inputs']:
                workflow['41']['inputs']['strength'] = strength1
                logger.info(f"Updated strength 1 in node 41: {strength1}")
            else:
                logger.warning("Node 41 (strength 1 node) not found in workflow or has unexpected structure")

            # Strength 2 is in node 48 (StyleModelApply)
            if '48' in workflow and 'inputs' in workflow['48'] and 'strength' in workflow['48']['inputs']:
                workflow['48']['inputs']['strength'] = strength2
                logger.info(f"Updated strength 2 in node 48: {strength2}")
            else:
                logger.warning("Node 48 (strength 2 node) not found in workflow or has unexpected structure")

            # Update resolution in node 49 (Empty Latent Ratio Select SDXL)
            if '49' in workflow and 'inputs' in workflow['49'] and 'ratio_selected' in workflow['49']['inputs']:
                workflow['49']['inputs']['ratio_selected'] = resolution
                logger.info(f"Updated resolution in node 49: {resolution}")
            else:
                logger.warning("Node 49 (resolution node) not found in workflow or has unexpected structure")

            # Always generate a new random seed for Redux workflows
            if seed is None:
                seed = random.randint(0, 2**32 - 1)
                logger.info(f"Generated new random seed: {seed}")
            else:
                logger.info(f"Using provided seed: {seed}")

            # Update seed in node 25 (RandomNoise)
            if '25' in workflow and 'inputs' in workflow['25'] and 'noise_seed' in workflow['25']['inputs']:
                # Store the old seed for debugging
                old_seed = workflow['25']['inputs']['noise_seed']
                # Update the seed
                workflow['25']['inputs']['noise_seed'] = seed
                logger.info(f"Updated noise_seed in node 25 from {old_seed} to {seed}")
            else:
                logger.warning("Node 25 (noise_seed node) not found in workflow or has unexpected structure")

            # Dump the workflow to a string for debugging
            workflow_str = json.dumps(workflow, indent=2)
            logger.info(f"Updated Redux workflow: {workflow_str[:200]}...")

            return workflow
        except Exception as e:
            logger.error(f"Error updating Redux workflow: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return workflow

    def update_reduxprompt_workflow(self,
                                   workflow: Dict[str, Any],
                                   image_path: str,
                                   prompt: str,
                                   strength: float,
                                   resolution: str,
                                   loras: List[Dict[str, Any]],
                                   upscale_factor: int = 1,
                                   seed: Optional[int] = None) -> Dict[str, Any]:
        """
        Update a ReduxPrompt workflow with new parameters.

        Args:
            workflow: Workflow to update
            image_path: Path to the image
            prompt: Prompt for image generation
            strength: Strength of the image
            resolution: Resolution for image generation
            loras: LoRAs to use
            upscale_factor: Upscale factor
            seed: Seed for generation

        Returns:
            Updated workflow
        """
        try:
            # Create a deep copy to avoid modifying the original
            workflow = json.loads(json.dumps(workflow))

            # Ensure path is absolute with forward slashes
            image_path = os.path.abspath(image_path).replace('\\', '/')

            # Update image path
            if '54' in workflow:
                workflow['54']['inputs']['image'] = image_path
                logger.debug(f"Updated image path: {image_path}")
            else:
                logger.warning("Node 54 (image node) not found in workflow")

            # Update prompt
            if '6' in workflow:
                workflow['6']['inputs']['text'] = prompt
                logger.debug(f"Updated prompt: {prompt}")
            else:
                logger.warning("Node 6 (prompt node) not found in workflow")

            # Update strength in the ApplyPulidFlux node
            if '62' in workflow:
                workflow['62']['inputs']['weight'] = strength
                logger.debug(f"Updated strength: {strength}")
            else:
                logger.warning("Node 62 (ApplyPulidFlux node) not found in workflow")

            # Update resolution
            if '70' in workflow:
                # Get the current resolution from the workflow to use as fallback
                current_resolution = workflow['70']['inputs'].get('ratio_selected', '9:16 [768x1344 portrait]')

                # Try to use the provided resolution, but fall back to the current one if it fails
                try:
                    # First attempt with the provided resolution
                    workflow['70']['inputs']['ratio_selected'] = resolution
                    logger.debug(f"Updated resolution to: {resolution}")
                except Exception as e:
                    # If that fails, use the current resolution from the workflow
                    logger.warning(f"Failed to set resolution to {resolution}, using current workflow resolution: {current_resolution}")
                    workflow['70']['inputs']['ratio_selected'] = current_resolution
            else:
                logger.warning("Node 70 (resolution node) not found in workflow")

            # Update seed
            if seed is None:
                seed = random.randint(0, 2**32 - 1)

            if '73' in workflow:
                workflow['73']['inputs']['seed'] = seed
                logger.debug(f"Updated seed: {seed}")
            else:
                logger.warning("Node 73 (seed node) not found in workflow")

            # Update LoRAs
            if '73' in workflow:
                lora_inputs = workflow['73']['inputs']

                # Clear existing LoRAs
                for key in list(lora_inputs.keys()):
                    if key.startswith('lora_'):
                        del lora_inputs[key]

                # Add new LoRAs
                # First, convert string LoRAs to dictionaries if needed
                processed_loras = []
                for lora in loras:
                    if isinstance(lora, str):
                        # This is just a LoRA filename, convert to dict format
                        try:
                            # Try to get LoRA info from LoraManager
                            from src.domain.lora_management import LoraManager
                            lora_manager = LoraManager()
                            lora_info = lora_manager.get_lora_info(lora)

                            if lora_info:
                                processed_loras.append({
                                    "name": lora,
                                    "model_strength": float(lora_info.get('weight', 1.0)),
                                    "clip_strength": float(lora_info.get('weight', 1.0))
                                })
                            else:
                                # Fallback if LoRA info not found
                                processed_loras.append({
                                    "name": lora,
                                    "model_strength": 1.0,
                                    "clip_strength": 1.0
                                })
                        except Exception as e:
                            logger.warning(f"Error processing LoRA {lora}: {e}")
                            # Use default values
                            processed_loras.append({
                                "name": lora,
                                "model_strength": 1.0,
                                "clip_strength": 1.0
                            })
                    else:
                        # This is already a dictionary
                        processed_loras.append(lora)

                # Now add the processed LoRAs to the workflow
                for i, lora in enumerate(processed_loras):
                    lora_key = f"lora_{i+1}"
                    lora_inputs[lora_key] = {
                        "lora": lora["name"],
                        "strength_model": lora["model_strength"],
                        "strength_clip": lora["clip_strength"]
                    }

                logger.debug(f"Updated LoRAs: {processed_loras}")
            else:
                logger.warning("Node 73 (LoRA node) not found in workflow")

            # Update upscale factor
            # For PuLID workflow, use node 77 which is a Primitive float for upscale factor
            if '77' in workflow:
                # Limit upscale factor to a maximum of 3 for PuLID workflows
                limited_upscale = min(upscale_factor, 3)
                workflow['77']['inputs']['float'] = limited_upscale
                logger.debug(f"Updated upscale factor in node 77: {limited_upscale} (limited from {upscale_factor})")
            else:
                logger.warning("Node 77 (upscale node) not found in PuLID workflow")

            return workflow
        except Exception as e:
            logger.error(f"Error updating ReduxPrompt workflow: {e}")
            raise
