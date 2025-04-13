import websocket
import uuid
import json
import urllib.request
import urllib.parse
import requests
import sys
import logging
import os
import time
from dotenv import load_dotenv

# Import the LoraManager
try:
    from src.domain.lora_management import LoraManager
    lora_manager = LoraManager()
except ImportError:
    # Fallback for standalone usage
    lora_manager = None
    logging.warning("LoraManager not available, LoRA functionality will be limited")

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client_id = str(uuid.uuid4())

def queue_prompt(server_address, workflow, client_id):
    """Queue a prompt for processing with enhanced validation and debugging"""
    try:
        # Validate workflow is a dictionary
        if not isinstance(workflow, dict):
            raise ValueError("Workflow must be a dictionary")

        # Create the request data
        request_data = {
            "prompt": workflow,
            "client_id": client_id
        }

        # Convert to JSON with minimal whitespace
        json_str = json.dumps(request_data, ensure_ascii=False, separators=(',', ':'))

        # Log the request data for debugging
        logger.info(f"Sending request to ComfyUI prompt endpoint")
        logger.info(f"Client ID: {client_id}")
        logger.info(f"Request size: {len(json_str)} bytes")

        # Encode as UTF-8
        data = json_str.encode('utf-8')

        # Create and configure the request
        url = f"http://{server_address}/prompt"
        headers = {
            'Content-Type': 'application/json',
            'Content-Length': str(len(data))
        }

        logger.info(f"Sending request to URL: {url}")
        logger.info(f"Headers: {headers}")

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
        except json.JSONDecodeError as e:
            logger.error(f"JSON encoding/decoding error: {str(e)}")
            logger.error(f"Problem data: {str(request_data)[:200]}...")
            raise ValueError(f"Invalid JSON format: {str(e)}")

    except Exception as e:
        logger.error(f"Error in queue_prompt: {str(e)}")
        raise

def get_image(server_address, filename, subfolder, folder_type):
    """Gets an image file from ComfyUI's output directory"""
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    url = f"http://{server_address}/view?{url_values}"

    logger.info(f"Retrieving image from URL: {url}")

    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            image_data = response.read()
            logger.info(f"Successfully retrieved image: {filename}, size: {len(image_data)} bytes")
            return image_data, filename
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP Error in get_image: {e.code} - {e.reason} for URL {url}")

        # Try alternative approaches
        if folder_type == 'output':
            # Try with 'temp' folder type
            logger.info(f"Retrying with 'temp' folder type")
            try:
                return get_image(server_address, filename, subfolder, 'temp')
            except Exception as inner_e:
                logger.error(f"Retry failed: {str(inner_e)}")

                # If the filename starts with 'ComfyUI_', try to find any ComfyUI_ file
                if filename.startswith('ComfyUI_'):
                    logger.info(f"Trying to find any ComfyUI_ file in the output directory")
                    try:
                        # Get the history endpoint to find available files
                        history_url = f"http://{server_address}/history"
                        with urllib.request.urlopen(history_url, timeout=10) as response:
                            history_data = json.loads(response.read())

                            # Look for the most recent ComfyUI_ file
                            for prompt_id, prompt_data in reversed(list(history_data.items())):
                                if 'outputs' in prompt_data:
                                    for node_id, node_output in prompt_data['outputs'].items():
                                        if 'images' in node_output:
                                            for image in node_output['images']:
                                                if image['filename'].startswith('ComfyUI_'):
                                                    logger.info(f"Found alternative ComfyUI file: {image['filename']}")
                                                    return get_image(server_address, image['filename'], image.get('subfolder', ''), image.get('type', 'output'))
                    except Exception as history_e:
                        logger.error(f"Error trying to find alternative ComfyUI file: {str(history_e)}")
        raise
    except Exception as e:
        logger.error(f"Error in get_image: {str(e)}")
        raise

def get_history(server_address, prompt_id):
    url = f"http://{server_address}/history/{prompt_id}"
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            return json.loads(response.read())
    except Exception as e:
        logger.error(f"Error in get_history: {str(e)}")
        raise

def clear_cache(ws):
    clear_message = json.dumps({"type": "clear_cache"})
    ws.send(clear_message)
    logger.info("Sent clear_cache message to ComfyUI")

def send_progress_update(bot_server, request_id, progress_data):
    try:
        # Prepare the data - EXACTLY like GitHub version
        data = {
            'request_id': request_id,
            'progress_data': progress_data
        }

        # Send the update with retries - EXACTLY like GitHub version
        retries = 3
        retry_delay = 1

        for attempt in range(retries):
            try:
                response = requests.post(
                    f"http://{bot_server}:8090/update_progress",
                    json=data,
                    timeout=120
                )
                if response.status_code == 200:
                    logger.info(f"Progress update sent: {progress_data}")
                    return
                else:
                    logger.warning(f"Progress update failed with status {response.status_code}: {response.text}")
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"All retry attempts failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error sending progress update: {str(e)}")

def get_images(server_address, bot_server, request_id, ws, workflow, client_id, is_video=False):
    try:
        # Record the start time when we send the request to ComfyUI
        generation_start_time = time.time()
        logger.info(f"Starting {'video' if is_video else 'image'} generation at {generation_start_time}")

        # Initialize variables
        output_images = {}
        last_milestone = 0

        # Queue the prompt to ComfyUI
        prompt_response = queue_prompt(server_address, workflow, client_id)
        if 'prompt_id' not in prompt_response:
            raise ValueError("No prompt_id in response from queue_prompt")

        prompt_id = prompt_response['prompt_id']
        logger.info(f"Queued prompt with ID: {prompt_id}")

        # Send initial progress update
        send_progress_update(bot_server, request_id, {
            "status": "execution",
            "message": "Starting execution..."
        })

        # Start monitoring for progress updates
        while True:
            out = ws.recv()
            if isinstance(out, str):
                try:
                    message = json.loads(out)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing WebSocket message: {e}")
                    continue

                if message['type'] == 'execution_start':
                    send_progress_update(bot_server, request_id, {
                        "status": "execution",
                        "message": "Starting execution..."
                    })

                elif message['type'] == 'execution_cached':
                    send_progress_update(bot_server, request_id, {
                        "status": "cached",
                        "message": "Using cached result..."
                    })

                elif message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        # Record the end time when generation is complete
                        generation_end_time = time.time()
                        generation_time = generation_end_time - generation_start_time
                        logger.info(f"Image generation completed in {generation_time:.2f} seconds")

                        send_progress_update(bot_server, request_id, {
                            "status": "complete",
                            "message": "Generation complete!",
                            "generation_time": generation_time
                        })

                        break

                    if "UNETLoader" in str(data) or "CLIPLoader" in str(data) or "VAELoader" in str(data):
                        send_progress_update(bot_server, request_id, {
                            "status": "loading_models",
                            "message": "Loading models and preparing generation..."
                        })

                elif message['type'] == 'progress':
                    data = message['data']
                    current_step = data['value']
                    max_steps = data['max']
                    progress = int((current_step / max_steps) * 100)

                    current_milestone = (progress // 10) * 10
                    if current_milestone > last_milestone:
                        send_progress_update(bot_server, request_id, {
                            "status": "generating",
                            "progress": progress
                        })
                        last_milestone = current_milestone

        # After breaking out of the WebSocket loop, get the history and process outputs
        history = get_history(server_address, prompt_id)[prompt_id]
        logger.info(f"Got history for prompt {prompt_id}")

        # Debug log the available outputs
        logger.info(f"Available outputs in history: {list(history['outputs'].keys())}")

        # For Redux workflows, we need to look for the SaveImage node (69)
        if request_type == 'redux':
            logger.info("Processing Redux workflow output")
            # Try to find the SaveImage node
            save_image_node = None

            # First, try node 69 (SaveImage)
            if '69' in history['outputs'] and 'images' in history['outputs']['69']:
                save_image_node = '69'
                logger.info(f"Found SaveImage node: {save_image_node}")
            else:
                logger.info("Node 69 (SaveImage) not found or has no images")

                # Try node 8 (VAEDecode) as a fallback
                if '8' in history['outputs'] and 'images' in history['outputs']['8']:
                    save_image_node = '8'
                    logger.info(f"Found VAEDecode node: {save_image_node}")
                else:
                    logger.info("Node 8 (VAEDecode) not found or has no images")

                    # Try to use any node with images as a fallback
                    for node_id, node_output in history['outputs'].items():
                        if 'images' in node_output and node_output['images']:
                            save_image_node = node_id
                            logger.info(f"Using fallback node {node_id} for Redux workflow")
                            break

            if save_image_node:
                logger.info(f"Using node {save_image_node} for Redux workflow")
            else:
                logger.error("Could not find any node with images in Redux workflow output")
                logger.error(f"Available nodes: {list(history['outputs'].keys())}")

                # Dump the entire history for debugging
                logger.info(f"Full history: {json.dumps(history, indent=2)}")

                # Try to use any node as a last resort
                for node_id, node_output in history['outputs'].items():
                    save_image_node = node_id
                    logger.info(f"Using last resort node {node_id} for Redux workflow")
                    break

        for node_id, node_output in history['outputs'].items():
            logger.info(f"Processing output from node {node_id}")
            logger.info(f"Node output keys: {list(node_output.keys())}")

            # For Redux workflows, only process the SaveImage node
            if request_type == 'redux' and save_image_node and node_id != save_image_node:
                logger.info(f"Skipping node {node_id} for Redux workflow (not the SaveImage node)")
                continue

            # Special handling for node 42 (VHS_VideoCombine)
            if node_id == '42':
                # Check all possible video output keys
                video_data = None
                if 'gifs' in node_output:
                    for gif in node_output['gifs']:
                        if gif['filename'].endswith('.mp4'):
                            video_data = gif
                            break

                if video_data:
                    logger.info(f"Found video data in node 42: {video_data}")
                    video_bytes, filename = get_image(
                        server_address,
                        video_data['filename'],
                        video_data.get('subfolder', ''),
                        video_data.get('type', 'output')
                    )
                    output_images[node_id] = [(video_bytes, filename)]
                    logger.info(f"Successfully processed video: {filename}")

            # Handle regular image outputs
            elif 'images' in node_output:
                images_output = []
                for image in node_output['images']:
                    try:
                        logger.info(f"Processing image: {image['filename']}")
                        image_data, filename = get_image(
                            server_address,
                            image['filename'],
                            image.get('subfolder', ''),
                            image.get('type', 'output')
                        )
                        images_output.append((image_data, filename))
                        logger.info(f"Successfully added image {filename} to output")
                    except Exception as e:
                        logger.error(f"Error processing image {image['filename']}: {str(e)}")
                        # Try to get the image from the temp directory as a fallback
                        try:
                            logger.info(f"Trying to get image from temp directory")
                            image_data, filename = get_image(
                                server_address,
                                image['filename'],
                                '',  # No subfolder
                                'temp'  # Use temp directory
                            )
                            images_output.append((image_data, filename))
                            logger.info(f"Successfully added image {filename} from temp directory")
                        except Exception as inner_e:
                            logger.error(f"Fallback also failed: {str(inner_e)}")
                            # Continue to the next image
                            continue

                if images_output:
                    output_images[node_id] = images_output
                    logger.info(f"Added {len(images_output)} images from node {node_id}")
                else:
                    logger.warning(f"No images could be processed from node {node_id}")

        if not output_images:
            logger.error("No outputs found in workflow execution")
            logger.error(f"History outputs: {history['outputs']}")

            # For Redux workflows, try to find any node with images as a last resort
            if request_type == 'redux':
                logger.info("Attempting to find any node with images for Redux workflow")
                for node_id, node_output in history['outputs'].items():
                    if 'images' in node_output and node_output['images']:
                        logger.info(f"Found node {node_id} with images as last resort")
                        try:
                            images_output = []
                            for image in node_output['images']:
                                try:
                                    # Try both output and temp directories
                                    for folder_type in ['output', 'temp']:
                                        try:
                                            logger.info(f"Trying to get image {image['filename']} from {folder_type} directory")
                                            image_data, filename = get_image(
                                                server_address,
                                                image['filename'],
                                                '',  # No subfolder
                                                folder_type
                                            )
                                            images_output.append((image_data, filename))
                                            logger.info(f"Successfully retrieved image {filename} from {folder_type} directory")
                                            break  # Break out of the folder_type loop if successful
                                        except Exception as e:
                                            logger.error(f"Error retrieving image from {folder_type} directory: {str(e)}")
                                except Exception as e:
                                    logger.error(f"Error processing image {image['filename']}: {str(e)}")

                            if images_output:
                                output_images[node_id] = images_output
                                logger.info(f"Added {len(images_output)} images from node {node_id} as last resort")
                                break  # Break out of the node_id loop if we found images
                        except Exception as e:
                            logger.error(f"Error processing node {node_id}: {str(e)}")

            # If we still have no outputs, raise an error
            if not output_images:
                raise ValueError("No outputs generated from workflow")

        # Calculate final generation time
        generation_end_time = time.time()
        generation_time = generation_end_time - generation_start_time
        logger.info(f"Total image processing completed in {generation_time:.2f} seconds")

        # Return both the images and the generation time
        return output_images, generation_time

    except Exception as e:
        logger.error(f"Error in get_images: {str(e)}")
        send_progress_update(bot_server, request_id, {
            "status": "error",
            "message": str(e)
        })
        raise

def cleanup_temp_files(workflow_filename, request_id=None, output_files=None, aggressive_cleanup=True):
    """
    Clean up temporary files and directories after successful image generation.

    Args:
        workflow_filename: The workflow file to delete
        request_id: The request ID to identify related files (optional)
        output_files: List of specific output files to delete (optional)
        aggressive_cleanup: If True, remove all files and directories in the output directory
    """
    try:
        # Clean up workflow file
        if workflow_filename and os.path.exists(workflow_filename):
            os.remove(workflow_filename)
            logger.info(f"Cleaned up workflow file: {workflow_filename}")

        # Clean up output files if provided
        if output_files:
            for file_path in output_files:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up output file: {file_path}")

        # Also clean up the workflow file in the output directory if it exists
        # This handles cases where the workflow file was saved in the output directory
        if workflow_filename:
            # Get just the filename without the path
            workflow_basename = os.path.basename(workflow_filename)
            output_workflow_path = os.path.join('output', workflow_basename)
            if os.path.exists(output_workflow_path):
                os.remove(output_workflow_path)
                logger.info(f"Cleaned up output workflow file: {output_workflow_path}")

        # Clean up all files in the output directory
        output_dirs = [
            os.path.join(os.getcwd(), 'output'),  # Our application's output directory
            os.path.join(os.getcwd(), 'ComfyUI', 'output') if os.path.exists(os.path.join(os.getcwd(), 'ComfyUI')) else None,  # ComfyUI's output directory if it exists
        ]

        # Special case: directly check for pulid_ and Video_ files in the output directory
        main_output_dir = os.path.join(os.getcwd(), 'output')
        if os.path.exists(main_output_dir) and os.path.isdir(main_output_dir):
            for filename in os.listdir(main_output_dir):
                if filename.lower().startswith('pulid_') or filename.lower().startswith('video_'):
                    file_path = os.path.join(main_output_dir, filename)
                    if os.path.isfile(file_path):
                        try:
                            os.remove(file_path)
                            if filename.lower().startswith('pulid_'):
                                logger.info(f"Directly removed PuLID file from output directory: {filename}")
                            else:
                                logger.info(f"Directly removed Video file from output directory: {filename}")
                        except Exception as e:
                            logger.warning(f"Failed to remove temporary file {file_path}: {str(e)}")

        # Add ComfyUI output directory from environment variables if available
        comfyui_dir = os.getenv('COMFYUI_DIR')
        if comfyui_dir and os.path.exists(comfyui_dir):
            output_dirs.append(os.path.join(comfyui_dir, 'output'))

        # Check for NVMax's specific ComfyUI directory
        nvmax_comfyui_dir = os.getenv('COMFYUI_DIR', 'C:/Users/NVMax/Desktop/ComfyUI_cu128_50XX/ComfyUI')
        if nvmax_comfyui_dir and os.path.exists(nvmax_comfyui_dir):
            # Add main output directory
            if os.path.exists(os.path.join(nvmax_comfyui_dir, 'output')):
                output_dirs.append(os.path.join(nvmax_comfyui_dir, 'output'))

            # Add FLUX_Output directory
            flux_output_dir = os.path.join(nvmax_comfyui_dir, 'output', 'FLUX_Output')
            if os.path.exists(flux_output_dir):
                output_dirs.append(flux_output_dir)

                # Add subdirectories
                for subdir in ['Basic', 'Video']:
                    subdir_path = os.path.join(flux_output_dir, subdir)
                    if os.path.exists(subdir_path):
                        output_dirs.append(subdir_path)

                        # Add Flux_gen directory
                        flux_gen_dir = os.path.join(subdir_path, 'Flux_gen')
                        if os.path.exists(flux_gen_dir):
                            output_dirs.append(flux_gen_dir)

        # Remove None values
        output_dirs = [d for d in output_dirs if d is not None]

        # Clean up files in all output directories
        total_files_removed = 0
        total_dirs_removed = 0

        # First pass: remove all files
        for output_dir in output_dirs:
            if os.path.exists(output_dir) and os.path.isdir(output_dir):
                # Get all files in the output directory
                files_removed = 0
                for root, dirs, files in os.walk(output_dir, topdown=False):  # Use topdown=False to process subdirectories first
                    for filename in files:
                        file_path = os.path.join(root, filename)

                        # Skip database files and other important files
                        if filename.endswith('.db') or filename.startswith('.'):
                            continue

                        # Always remove files starting with 'pulid_' or 'video_' regardless of other conditions
                        if filename.lower().startswith('pulid_') or filename.lower().startswith('video_'):
                            should_remove = True
                        # Skip JSON files unless they're temporary workflow files
                        elif filename.endswith('.json') and not ('temp_workflow' in filename or 'pulid' in filename.lower() or 'video_' in filename.lower()):
                            continue

                        # If aggressive_cleanup is True, remove all files regardless of request_id
                        # Otherwise, only remove files related to this request or recent files
                        else:
                            should_remove = aggressive_cleanup

                        if not should_remove and request_id is not None:
                            # Check if file is related to this request
                            should_remove = request_id in filename

                        if not should_remove:
                            # Check if file is recent
                            file_is_recent = False
                            try:
                                # Check if file was created in the last 5 minutes
                                file_creation_time = os.path.getctime(file_path)
                                file_is_recent = (time.time() - file_creation_time) < 300  # 5 minutes
                            except Exception:
                                file_is_recent = False

                            should_remove = file_is_recent

                        if should_remove:
                            try:
                                os.remove(file_path)
                                files_removed += 1
                                logger.debug(f"Cleaned up file: {file_path}")
                            except Exception as e:
                                logger.warning(f"Failed to remove file {file_path}: {str(e)}")

                logger.info(f"Cleaned up {files_removed} files from {output_dir}")
                total_files_removed += files_removed

        # Second pass: remove empty directories and hash code directories
        for output_dir in output_dirs:
            if os.path.exists(output_dir) and os.path.isdir(output_dir):
                dirs_removed = 0
                # Walk the directory tree bottom-up to remove empty directories
                for root, dirs, files in os.walk(output_dir, topdown=False):  # Use topdown=False to process subdirectories first
                    for dirname in dirs:
                        dir_path = os.path.join(root, dirname)

                        # Check if directory is empty or is a hash code directory (contains only a single hash)
                        is_empty = len(os.listdir(dir_path)) == 0
                        is_hash_dir = all(c in '0123456789abcdef-' for c in dirname) and len(dirname) >= 32

                        # Check if directory contains PuLID or Video-related files
                        has_special_files = False
                        if not is_empty:
                            for item in os.listdir(dir_path):
                                if (item.lower().startswith('pulid_') or 'pulid' in item.lower() or
                                    item.lower().startswith('video_') or 'video' in item.lower()):
                                    has_special_files = True
                                    break

                        # If aggressive_cleanup is True, remove all directories
                        # Otherwise, only remove empty directories, hash directories, or directories with special files
                        should_remove = aggressive_cleanup or is_empty or is_hash_dir or has_special_files

                        if should_remove:
                            try:
                                # If it's a hash directory or has special files, remove all files inside first
                                if (is_hash_dir or has_special_files) and not is_empty:
                                    for item in os.listdir(dir_path):
                                        item_path = os.path.join(dir_path, item)
                                        if os.path.isfile(item_path):
                                            os.remove(item_path)
                                            logger.debug(f"Cleaned up file in {'hash' if is_hash_dir else 'special'} directory: {item_path}")

                                # Now remove the directory
                                os.rmdir(dir_path)
                                dirs_removed += 1
                                logger.debug(f"Removed {'empty' if is_empty else 'hash'} directory: {dir_path}")
                            except Exception as e:
                                logger.warning(f"Failed to remove directory {dir_path}: {str(e)}")

                logger.info(f"Removed {dirs_removed} directories from {output_dir}")
                total_dirs_removed += dirs_removed

        logger.info(f"Total cleanup: {total_files_removed} files and {total_dirs_removed} directories removed")
    except Exception as e:
        logger.error(f"Error cleaning up temporary files: {str(e)}")

def send_final_image(bot_server, request_id, images, is_video=False, workflow_filename=None):
    try:
        # Import required modules
        import os
        import json
        import sqlite3
        # Find the final image or video (usually the last one)
        final_output = None
        output_files = []

        # For PuLID workflows, ALWAYS use node 72 and NEVER use node 74:2
        if is_video == False and is_pulid_workflow:
            logger.info(f"Processing PuLID workflow: {workflow_filename}")
            logger.info(f"Available nodes in images: {list(images.keys())}")

            # Force using node 72 for PuLID workflows
            if '72' in images and images['72']:
                for image_data, filename in reversed(images['72']):
                    if not filename.startswith('ComfyUI_temp'):
                        final_output = (image_data, filename)
                        logger.info(f"Using image from node 72 (PuLID workflow): {filename}")

                        # Add to output files list for cleanup
                        full_path = os.path.join(os.getcwd(), 'output', filename)
                        if os.path.exists(full_path):
                            output_files.append(full_path)
                        break

                # If we found an image from node 72, skip the standard approach
                if final_output:
                    logger.info("Successfully found image from node 72, skipping other nodes")
                    # Explicitly remove node 74:2 from consideration to avoid using it
                    if '74:2' in images:
                        logger.info("Removing node 74:2 from consideration for PuLID workflow")
                        del images['74:2']
            else:
                logger.warning("Node 72 not found in PuLID workflow outputs or has no images")

        # If we didn't find an image from node 72 (or this isn't a PuLID workflow), use the standard approach
        if not final_output:
            # Look for the final output node
            for node_id, image_data_list in reversed(images.items()):
                if image_data_list:  # Make sure the list is not empty
                    for image_data, filename in reversed(image_data_list):
                        if not filename.startswith('ComfyUI_temp'):
                            final_output = (image_data, filename)
                            logger.info(f"Using image from node {node_id}: {filename}")

                            # Add to output files list for cleanup
                            full_path = os.path.join(os.getcwd(), 'output', filename)
                            if os.path.exists(full_path):
                                output_files.append(full_path)

                            break
                    if final_output:
                        break

        if not final_output:
            logger.error(f"No final {'video' if is_video else 'image'} found to send")
            send_progress_update(bot_server, request_id, {
                "status": "error",
                "message": f"No final {'video' if is_video else 'image'} generated"
            })
            return

        output_data, filename = final_output

        # Double-check for PuLID workflows that we're using the correct node
        if is_video == False and is_pulid_workflow:
            node_id = None
            # Find which node this image came from
            for nid, image_list in images.items():
                for _, img_filename in image_list:  # Use _ for unused variable
                    if img_filename == filename:
                        node_id = nid
                        break
                if node_id:
                    break

            if node_id != '72':
                logger.warning(f"WARNING: Using image from node {node_id} instead of node 72 for PuLID workflow")
                # If node 72 exists and has images, force using it
                if '72' in images and images['72']:
                    for image_data, img_filename in reversed(images['72']):
                        if not img_filename.startswith('ComfyUI_temp'):
                            logger.info(f"Forcing use of image from node 72: {img_filename} instead of {filename}")
                            output_data = image_data
                            filename = img_filename
                            break

        logger.info(f"Selected final {'video' if is_video else 'image'}: {filename}, size: {len(output_data)} bytes")

        # For multipart/form-data, we need to use the files parameter
        # Use different parameter name for video files
        if is_video:
            files = {'video_data': (filename, output_data, 'video/mp4')}
        else:
            files = {'image_data': (filename, output_data)}

        # The request_id is sent as form data
        data = {
            'request_id': request_id,
        }

        logger.info(f"Sending image to http://{bot_server}:8090/send_image")

        try:
            # OPTIMIZATION: Use a single attempt with a short timeout
            response = requests.post(
                f"http://{bot_server}:8090/send_image",
                files=files,
                data=data,
                timeout=10  # Short timeout for faster response
            )

            if response.status_code == 200:
                logger.info(f"Successfully sent {'video' if is_video else 'image'}")

                # Directly update the analytics database
                try:
                    logger.info(f"ANALYTICS: Directly updating analytics database from comfygen.py for request {request_id}")
                    import sqlite3
                    import os
                    import json

                    # Get the path to the analytics.db file
                    analytics_db_path = os.path.join(os.getcwd(), 'analytics.db')
                    logger.info(f"ANALYTICS: Database path: {analytics_db_path}")

                    # Check if the file exists
                    if not os.path.exists(analytics_db_path):
                        logger.error(f"ANALYTICS: Analytics database not found at {analytics_db_path}")

                        # Try to find the database file
                        for root, dirs, files in os.walk(os.getcwd()):
                            if 'analytics.db' in files:
                                analytics_db_path = os.path.join(root, 'analytics.db')
                                logger.info(f"ANALYTICS: Found database at {analytics_db_path}")
                                break
                        else:
                            logger.error(f"ANALYTICS: Could not find analytics.db anywhere in the project")

                    if os.path.exists(analytics_db_path):
                        # Connect to the database
                        conn = sqlite3.connect(analytics_db_path)
                        c = conn.cursor()

                        # Check if the table exists
                        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='image_stats'")
                        if not c.fetchone():
                            logger.error(f"ANALYTICS: image_stats table does not exist in {analytics_db_path}")
                        else:
                            # Get the current timestamp
                            current_time = time.time()

                            # Get the user_id from the command line arguments
                            # The user_id is the second argument (index 2) in the command line
                            user_id = sys.argv[2] if len(sys.argv) > 2 else "unknown"
                            logger.info(f"ANALYTICS: Using user_id: {user_id} for request {request_id}")

                            # Insert the image generation record
                            c.execute(
                                "INSERT INTO image_stats (user_id, prompt, resolution, loras, upscale_factor, generation_time, is_video, generation_type, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (user_id, "", "", json.dumps([]), 1, generation_time, 1 if is_video else 0, "standard", current_time)
                            )

                            # Commit changes and close connection
                            conn.commit()
                            conn.close()

                            logger.info(f"ANALYTICS: Successfully recorded image generation for request {request_id}")
                except Exception as e:
                    logger.error(f"ANALYTICS: Error directly updating analytics database: {e}")

                # Clean up temporary files after successful send
                # Use aggressive cleanup to remove all files and directories
                cleanup_temp_files(workflow_filename, request_id, output_files, aggressive_cleanup=True)

                return response
            else:
                logger.warning(f"Failed to send {'video' if is_video else 'image'}, status code: {response.status_code}")
                logger.warning(f"Response content: {response.text}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending {'video' if is_video else 'image'}: {str(e)}")
            raise

    except Exception as e:
        logger.error(f"Error in send_final_image: {str(e)}")
        raise

if __name__ == "__main__":
    ws = None  # Define ws at the module level
    is_pulid_workflow = False  # Default value for PuLID workflow flag

    try:
        if len(sys.argv) < 7:
            raise ValueError(f"Expected at least 7 arguments, but got {len(sys.argv) - 1}")

        request_id = sys.argv[1]
        user_id = sys.argv[2]
        channel_id = sys.argv[3]
        interaction_id = sys.argv[4]
        original_message_id = sys.argv[5]
        request_type = sys.argv[6]

        logger.info(f"Processing request: {request_id}, type: {request_type}")

        # Create temp directory if needed
        os.makedirs('output', exist_ok=True)

        # Process based on request type
        if request_type in ['standard', 'video', 'pulid', 'redux']:
            # Standard /comfy command, /video command, or /pulid command
            full_prompt = sys.argv[7]
            resolution = sys.argv[8]
            loras = json.loads(sys.argv[9])
            upscale_factor = int(sys.argv[10])
            workflow_filename = sys.argv[11]
            seed = sys.argv[12] if len(sys.argv) > 12 else None

            # Set is_video flag based on request_type
            is_video = (request_type == 'video')
            is_pulid = (request_type == 'pulid')

            # For PuLID requests, set a flag to indicate this is a PuLID workflow
            if is_pulid and 'Pulid' not in workflow_filename:
                logger.warning(f"PuLID request but workflow doesn't contain 'Pulid': {workflow_filename}")
                logger.info("Setting internal flag to indicate this is a PuLID workflow")
                # Instead of modifying the filename, set a flag
                is_pulid_workflow = True
            else:
                is_pulid_workflow = 'Pulid' in workflow_filename or is_pulid

            # Define bot_server
            bot_server = "127.0.0.1"

            # Send initial status
            send_progress_update(bot_server, request_id, {
                'status': 'starting',
                'message': 'Starting Generation process...'
            })

            # Load workflow
            with open(workflow_filename, 'r') as f:
                workflow = json.load(f)

            # For Redux workflows, double-check and update the workflow again
            if request_type == 'redux':
                logger.info("Double-checking Redux workflow in comfygen.py")

                # Ensure paths are absolute with forward slashes
                image1_path = os.path.abspath(os.path.join('output', request_id, 'image1.png')).replace('\\', '/')
                image2_path = os.path.abspath(os.path.join('output', request_id, 'image2.png')).replace('\\', '/')

                # Verify that the image files exist
                if not os.path.exists(image1_path):
                    logger.error(f"Image 1 file does not exist: {image1_path}")
                    # Try to find the image in the output directory
                    for root, dirs, files in os.walk('output'):
                        for file in files:
                            if file == 'image1.png':
                                image1_path = os.path.abspath(os.path.join(root, file)).replace('\\', '/')
                                logger.info(f"Found image1.png at: {image1_path}")
                                break
                else:
                    logger.info(f"Image 1 file exists: {image1_path}")

                if not os.path.exists(image2_path):
                    logger.error(f"Image 2 file does not exist: {image2_path}")
                    # Try to find the image in the output directory
                    for root, dirs, files in os.walk('output'):
                        for file in files:
                            if file == 'image2.png':
                                image2_path = os.path.abspath(os.path.join(root, file)).replace('\\', '/')
                                logger.info(f"Found image2.png at: {image2_path}")
                                break
                else:
                    logger.info(f"Image 2 file exists: {image2_path}")

                # Update image paths
                if '40' in workflow and 'inputs' in workflow['40']:
                    workflow['40']['inputs']['image'] = image1_path
                    logger.info(f"Updated image 1 path in node 40: {image1_path}")
                else:
                    logger.warning("Node 40 (image 1 node) not found in workflow")

                if '46' in workflow and 'inputs' in workflow['46']:
                    workflow['46']['inputs']['image'] = image2_path
                    logger.info(f"Updated image 2 path in node 46: {image2_path}")
                else:
                    logger.warning("Node 46 (image 2 node) not found in workflow")

                # Update resolution
                if '49' in workflow and 'inputs' in workflow['49'] and 'ratio_selected' in workflow['49']['inputs']:
                    workflow['49']['inputs']['ratio_selected'] = resolution
                    logger.info(f"Updated resolution in node 49: {resolution}")
                else:
                    logger.warning("Node 49 (resolution node) not found in workflow")

                # Update seed
                if '25' in workflow and 'inputs' in workflow['25'] and 'noise_seed' in workflow['25']['inputs']:
                    old_seed = workflow['25']['inputs']['noise_seed']
                    workflow['25']['inputs']['noise_seed'] = seed
                    logger.info(f"Updated seed in node 25 from {old_seed} to {seed}")
                else:
                    logger.warning("Node 25 (seed node) not found in workflow")

                # Save the updated workflow back to the file
                with open(workflow_filename, 'w') as f:
                    json.dump(workflow, f)
                logger.info(f"Saved updated Redux workflow to {workflow_filename}")

            # Process seed
            try:
                if seed and seed != "None":
                    seed = int(seed)
                else:
                    # Generate a random seed if none is provided
                    seed = int(time.time() * 1000) % 2147483647
                logger.info(f"Using seed: {seed}")
            except ValueError:
                # Generate a random seed if conversion fails
                seed = int(time.time() * 1000) % 2147483647
                logger.info(f"Invalid seed value, using random seed: {seed}")

            # Add LoRA trigger words to prompt if needed
            if not is_video and loras:
                # Load LoRA configuration
                lora_config_path = os.path.join('config', 'lora.json')
                if os.path.exists(lora_config_path):
                    try:
                        with open(lora_config_path, 'r') as f:
                            lora_config = json.load(f)
                            lora_info = {lora['file']: lora for lora in lora_config['available_loras']}

                            # Add LoRA trigger words to prompt
                            modified_prompt = full_prompt
                            for lora_file in loras:
                                if lora_file in lora_info and lora_info[lora_file].get('add_prompt'):
                                    trigger_words = lora_info[lora_file]['add_prompt']
                                    if trigger_words and trigger_words not in modified_prompt:
                                        modified_prompt = f"{modified_prompt}, {trigger_words}"
                                        logger.info(f"Added trigger words '{trigger_words}' for LoRA {lora_file}")

                            # Use the modified prompt
                            full_prompt = modified_prompt
                            logger.info(f"Enhanced prompt with LoRA trigger words: {full_prompt}")
                    except Exception as e:
                        logger.error(f"Error adding LoRA trigger words to prompt: {e}")

            # Update workflow with parameters
            # Update prompt based on workflow type
            if request_type == 'redux':
                # For Redux workflow, check key nodes
                logger.info(f"Processing Redux workflow")

                # Check for key nodes
                if '25' in workflow and 'inputs' in workflow['25'] and 'noise_seed' in workflow['25']['inputs']:
                    old_seed = workflow['25']['inputs']['noise_seed']
                    workflow['25']['inputs']['noise_seed'] = seed
                    logger.info(f"Updated node 25 (RandomNoise) seed from {old_seed} to {seed}")
                else:
                    logger.warning("Node 25 (RandomNoise) not found or missing noise_seed input")

                # Check resolution node
                if '49' in workflow and 'inputs' in workflow['49'] and 'ratio_selected' in workflow['49']['inputs']:
                    old_resolution = workflow['49']['inputs']['ratio_selected']
                    workflow['49']['inputs']['ratio_selected'] = resolution
                    logger.info(f"Updated node 49 (Resolution) from {old_resolution} to {resolution}")
                else:
                    logger.warning("Node 49 (Resolution) not found or missing ratio_selected input")

                # Check for image nodes (40 and 46)
                # These should be updated by the bot.py before calling comfygen.py
                # But let's check them here to make sure they're set correctly
                if '40' in workflow and 'inputs' in workflow['40'] and 'image' in workflow['40']['inputs']:
                    image1_path = workflow['40']['inputs']['image']
                    logger.info(f"Image 1 path in node 40: {image1_path}")
                    # Make sure the path exists
                    if not os.path.exists(image1_path):
                        logger.error(f"Image 1 path does not exist: {image1_path}")
                else:
                    logger.warning("Node 40 (Image 1) not found or missing image input")

                if '46' in workflow and 'inputs' in workflow['46'] and 'image' in workflow['46']['inputs']:
                    image2_path = workflow['46']['inputs']['image']
                    logger.info(f"Image 2 path in node 46: {image2_path}")
                    # Make sure the path exists
                    if not os.path.exists(image2_path):
                        logger.error(f"Image 2 path does not exist: {image2_path}")
                else:
                    logger.warning("Node 46 (Image 2) not found or missing image input")

            elif is_pulid:
                # PuLID workflow uses node 6 for prompt
                if '6' in workflow:
                    workflow['6']['inputs']['text'] = full_prompt
                    logger.info(f"Updated prompt in PuLID workflow (node 6)")
                else:
                    logger.warning("Node 6 (prompt node) not found in PuLID workflow")
            else:
                # Standard workflow uses node 69 for prompt
                if '69' in workflow:
                    workflow['69']['inputs']['prompt'] = full_prompt
                    logger.info(f"Updated prompt in workflow (node 69)")
                else:
                    logger.warning("Node 69 (prompt node) not found in workflow")

            # Update resolution based on workflow type
            if is_pulid:
                # PuLID workflow uses node 70 for resolution
                if '70' in workflow:
                    workflow['70']['inputs']['ratio_selected'] = resolution
                    logger.info(f"Updated resolution in PuLID workflow (node 70)")
                else:
                    logger.warning("Node 70 (resolution node) not found in PuLID workflow")
            else:
                # Standard workflow uses node 258 for resolution
                if '258' in workflow:
                    workflow['258']['inputs']['ratio_selected'] = resolution
                    logger.info(f"Updated resolution in workflow (node 258)")
                else:
                    logger.warning("Node 258 (resolution node) not found in workflow")

            # Update LoRAs using the LoraManager if available
            if lora_manager is not None:
                # Use the LoraManager to apply LoRAs based on workflow type
                if is_pulid:
                    # PuLID workflow uses node 73 for LoRAs
                    workflow = lora_manager.apply_loras_to_workflow(workflow, loras, lora_node_id='73', prompt_node_id='6')
                    logger.info(f"Updated LoRAs in PuLID workflow using LoraManager: {len(loras)} LoRAs configured")
                else:
                    # Standard workflow uses node 271 for LoRAs
                    workflow = lora_manager.apply_loras_to_workflow(workflow, loras)
                    logger.info(f"Updated LoRAs in workflow using LoraManager: {len(loras)} LoRAs configured")
            else:
                # Fallback to existing implementation if LoraManager is not available
                if is_pulid and '73' in workflow:
                    # PuLID workflow uses node 73 for LoRAs
                    lora_loader = workflow['73']['inputs']
                    for key in list(lora_loader.keys()):
                        if key.startswith('lora_'):
                            del lora_loader[key]
                elif not is_pulid and '271' in workflow:
                    # Standard workflow uses node 271 for LoRAs
                    lora_loader = workflow['271']['inputs']
                    for key in list(lora_loader.keys()):
                        if key.startswith('lora_'):
                            del lora_loader[key]

                    # Add new LoRAs
                    # Load lora config to get weights
                    try:
                        lora_config_path = os.path.join('config', 'lora.json')
                        if not os.path.exists(lora_config_path):
                            lora_config_path = os.path.join('Main', 'Datasets', 'lora.json')

                        with open(lora_config_path, 'r') as f:
                            lora_config = json.load(f)

                        lora_info = {lora['file']: lora for lora in lora_config['available_loras']}

                        # Add LoRA entries to the workflow
                        for i, lora_file in enumerate(loras, start=1):
                            if lora_file in lora_info:
                                lora_key = f'lora_{i}'
                                # Get base strength from config
                                base_strength = float(lora_info[lora_file].get('weight', 1.0))

                                # If multiple LoRAs are selected, scale down to 0.5 unless already lower
                                if len(loras) > 1:
                                    lora_strength = min(base_strength, 0.5)
                                else:
                                    lora_strength = base_strength

                                lora_loader[lora_key] = {
                                    'on': True,
                                    'lora': lora_file,
                                    'strength': lora_strength
                                }
                                logger.info(f"Added LoRA {lora_file} with strength {lora_strength}")

                                # Add trigger words to prompt if available
                                if is_pulid:
                                    # PuLID workflow uses node 6 for prompt
                                    if '6' in workflow and lora_info[lora_file].get('add_prompt'):
                                        trigger_words = lora_info[lora_file]['add_prompt']
                                        if trigger_words and trigger_words not in workflow['6']['inputs']['text']:
                                            workflow['6']['inputs']['text'] = f"{workflow['6']['inputs']['text']}, {trigger_words}"
                                            logger.info(f"Added trigger words '{trigger_words}' for LoRA {lora_file} in PuLID workflow")
                                else:
                                    # Standard workflow uses node 69 for prompt
                                    if '69' in workflow and lora_info[lora_file].get('add_prompt'):
                                        trigger_words = lora_info[lora_file]['add_prompt']
                                        if trigger_words and trigger_words not in workflow['69']['inputs']['prompt']:
                                            workflow['69']['inputs']['prompt'] = f"{workflow['69']['inputs']['prompt']}, {trigger_words}"
                                            logger.info(f"Added trigger words '{trigger_words}' for LoRA {lora_file}")
                            else:
                                logger.warning(f"LoRA {lora_file} not found in configuration")
                    except Exception as e:
                        logger.error(f"Error configuring LoRAs: {str(e)}")

                    logger.info(f"Updated LoRAs in workflow: {len(loras)} LoRAs configured")

            # Update upscale factor based on workflow type
            if is_pulid:
                # PuLID workflow uses node 77 for upscale factor (Primitive float)
                if '77' in workflow:
                    # Limit upscale factor to a maximum of 3 for PuLID workflows
                    limited_upscale = min(upscale_factor, 3)
                    workflow['77']['inputs']['float'] = limited_upscale
                    logger.info(f"Updated upscale factor in PuLID workflow (node 77): {limited_upscale} (limited from {upscale_factor})")
                else:
                    logger.warning("Node 77 (upscale node) not found in PuLID workflow")
            else:
                # Standard workflow uses node 279 for upscale factor
                if '279' in workflow:
                    workflow['279']['inputs']['rescale_factor'] = upscale_factor
                    logger.info(f"Updated upscale factor in workflow (node 279)")
                else:
                    logger.warning("Node 279 (upscale node) not found in workflow")

            # Update seed - always set a valid integer seed
            # Ensure seed is a valid integer
            if seed is None:
                seed = int(time.time() * 1000) % 2147483647

            # Always generate a new random seed for PuLID workflows
            if is_pulid:
                # Generate a new random seed for each PuLID request
                random_seed = int(time.time() * 1000) % 2147483647
                logger.info(f"Generated new random seed for PuLID workflow: {random_seed}")

                # PuLID workflow uses node 62 for strength
                if '62' in workflow:
                    # Update strength in the ApplyPulidFlux node
                    workflow['62']['inputs']['weight'] = 0.5  # Default strength for PuLID
                    logger.info(f"Updated strength in PuLID workflow (node 62)")
                else:
                    logger.warning("Node 62 (ApplyPulidFlux node) not found in PuLID workflow")

                # PuLID workflow uses node 25 for seed
                if '25' in workflow:
                    workflow['25']['inputs']['noise_seed'] = random_seed
                    logger.info(f"Updated seed in PuLID workflow: {random_seed} (node 25)")
                else:
                    logger.warning("Node 25 (RandomNoise node) not found in PuLID workflow")
            else:
                # Standard workflow uses node 198:2 for seed
                if '198:2' in workflow:
                    workflow['198:2']['inputs']['noise_seed'] = seed
                    logger.info(f"Updated seed in workflow: {seed} (node 198:2)")
                else:
                    logger.warning("Node 198:2 (seed node) not found in workflow")

            # Connect to WebSocket
            server_address = "127.0.0.1:8188"
            bot_server = "127.0.0.1"

            ws = websocket.create_connection(
                f"ws://{server_address}/ws?clientId={client_id}"
            )
            ws.settimeout(5.0)  # 5 second timeout
            logger.info(f"Successfully connected to ComfyUI server with client ID {client_id}")

            # Clear cache
            clear_cache(ws)

            # Generate images or video
            images, generation_time = get_images(server_address, bot_server, request_id, ws, workflow, client_id, is_video=is_video)

            # Process output images
            final_image = None
            for node_id, image_data_list in reversed(images.items()):
                for image_data, filename in reversed(image_data_list):
                    if not filename.startswith('ComfyUI_temp'):
                        final_image = (image_data, filename)
                        break
                if final_image:
                    break

            if final_image:
                image_data, filename = final_image
                send_final_image(bot_server, request_id, images, is_video=is_video, workflow_filename=workflow_filename)

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if 'request_id' in locals() and 'bot_server' in locals():
            send_progress_update(bot_server, request_id, {
                'status': 'error',
                'message': f'Error: {str(e)}'
            })
    finally:
        # Clean up WebSocket connection
        if ws:
            try:
                ws.close()
                logger.info("WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error closing WebSocket: {str(e)}")
