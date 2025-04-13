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
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        logger.debug(f"Sending request to ComfyUI prompt endpoint")
        logger.debug(f"Client ID: {client_id}")
        logger.debug(f"Request size: {len(json_str)} bytes")

        # Encode as UTF-8
        data = json_str.encode('utf-8')

        # Create and configure the request
        url = f"http://{server_address}/prompt"
        headers = {
            'Content-Type': 'application/json',
            'Content-Length': str(len(data))
        }

        logger.info(f"Sending request to URL: {url}")
        logger.debug(f"Headers: {headers}")

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
    except Exception as e:
        logger.error(f"Error in queue_prompt: {str(e)}")
        raise

def get_image(server_address, filename, subfolder, folder_type="output"):
    """Gets an image file from ComfyUI's output directory"""
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    url = f"http://{server_address}/view?{url_values}"
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            return response.read(), filename
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
    logger.debug("Sent clear_cache message to ComfyUI")

def send_progress_update(bot_server, request_id, progress_data):
    try:
        retries = 3
        retry_delay = 1
        data = {
            'request_id': request_id,
            'progress_data': progress_data
        }

        for attempt in range(retries):
            try:
                response = requests.post(
                    f"http://{bot_server}:8090/update_progress",
                    json=data,
                    timeout=120
                )
                if response.status_code == 200:
                    logger.debug(f"Progress update sent: {progress_data}")
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

def get_images(server_address, bot_server, request_id, ws, workflow):
    try:
        prompt_response = queue_prompt(server_address, workflow, str(uuid.uuid4()))
        if 'prompt_id' not in prompt_response:
            raise ValueError("No prompt_id in response from queue_prompt")

        prompt_id = prompt_response['prompt_id']
        logger.info(f"Queued prompt with ID: {prompt_id}")

        output_images = {}
        last_milestone = 0

        # Send initial progress update
        send_progress_update(bot_server, request_id, {
            "status": "execution",
            "message": "Starting execution..."
        })

        # Set a maximum wait time
        max_wait_time = 600  # 10 minutes
        start_time = time.time()

        while True:
            # Check if we've waited too long
            if time.time() - start_time > max_wait_time:
                logger.warning(f"Waited too long for generation, timing out after {max_wait_time} seconds")
                send_progress_update(bot_server, request_id, {
                    "status": "error",
                    "message": f"Timed out after {max_wait_time} seconds"
                })
                raise TimeoutError(f"Timed out waiting for ComfyUI to generate images after {max_wait_time} seconds")

            try:
                # Set a timeout for the websocket receive operation
                ws.settimeout(5.0)  # 5 second timeout

                try:
                    out = ws.recv()
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
                            send_progress_update(bot_server, request_id, {
                                "status": "generating",
                                "progress": progress,
                                "message": f"Generating image... {progress}%"
                            })

                    elif message['type'] == 'executing':
                        if 'prompt_id' in message['data']:
                            prompt_id = message['data']['prompt_id']
                            logger.info(f"Executing prompt {prompt_id}")

                    elif message['type'] == 'executed':
                        send_progress_update(bot_server, request_id, {
                            "status": "processing",
                            "message": "Processing output..."
                        })

                        # Get the outputs
                        history = get_history(server_address, prompt_id)[prompt_id]
                        logger.info(f"Got history for prompt {prompt_id}")

                        # Debug log the available outputs
                        logger.debug(f"Available outputs in history: {list(history['outputs'].keys())}")

                        for node_id, node_output in history['outputs'].items():
                            logger.debug(f"Processing output from node {node_id}")
                            logger.debug(f"Node output keys: {list(node_output.keys())}")

                            if 'images' in node_output:
                                images = []
                                for image in node_output['images']:
                                    image_data, filename = get_image(
                                        server_address,
                                        image['filename'],
                                        image.get('subfolder', ''),
                                        image.get('type', 'output')
                                    )
                                    images.append((image_data, filename))
                                output_images[node_id] = images

                        if not output_images:
                            logger.error("No outputs found in workflow execution")
                            logger.error(f"History outputs: {history['outputs']}")
                            raise ValueError("No outputs generated from workflow")

                        # Send final image
                        send_final_image(bot_server, request_id, output_images)
                        return output_images

                    elif message['type'] == 'error':
                        error_message = message['data']['message']
                        logger.error(f"Error generating images: {error_message}")

                        send_progress_update(bot_server, request_id, {
                            "status": "error",
                            "message": f"Error: {error_message}"
                        })

                        raise Exception(f"ComfyUI error: {error_message}")

                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing WebSocket message: {e}")
                    continue

            except websocket.WebSocketTimeoutException:
                logger.warning("Websocket receive timed out, retrying...")
                continue

            except Exception as e:
                logger.error(f"Error processing websocket message: {e}")
                send_progress_update(bot_server, request_id, {
                    "status": "error",
                    "message": f"Error: {str(e)}"
                })
                raise

    except Exception as e:
        logger.error(f"Error in get_images: {str(e)}")
        send_progress_update(bot_server, request_id, {
            "status": "error",
            "message": str(e)
        })
        raise

def send_final_image(bot_server, request_id, images):
    try:
        # Find the final image (usually the last one)
        final_image = None
        for _, image_data_list in reversed(images.items()):
            for image_data, filename in reversed(image_data_list):
                if not filename.startswith('ComfyUI_temp'):
                    final_image = (image_data, filename)
                    break
            if final_image:
                break

        if not final_image:
            logger.error("No final image found to send")
            send_progress_update(bot_server, request_id, {
                "status": "error",
                "message": "No final image generated"
            })
            return

        image_data, filename = final_image

        retries = 3
        retry_delay = 1

        # For multipart/form-data, we need to use the files parameter
        files = {'image_data': (filename, image_data)}

        # The request_id is sent as form data
        data = {
            'request_id': request_id,
        }

        logger.info(f"Sending image to http://{bot_server}:8090/send_image")
        logger.info(f"Image filename: {filename}, size: {len(image_data)} bytes")

        for attempt in range(retries):
            try:
                response = requests.post(
                    f"http://{bot_server}:8090/send_image",
                    files=files,
                    data=data,
                    timeout=120
                )

                if response.status_code == 200:
                    logger.info(f"Successfully sent image")
                    send_progress_update(bot_server, request_id, {
                        "status": "complete",
                        "message": "Generation complete!"
                    })
                    return
                else:
                    logger.warning(f"Failed to send image, status code: {response.status_code}")
                    logger.warning(f"Response content: {response.text}")

            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"All retry attempts failed: {str(e)}")
                    raise

    except Exception as e:
        logger.error(f"Error sending final image: {str(e)}")
        send_progress_update(bot_server, request_id, {
            "status": "error",
            "message": f"Error sending final image: {str(e)}"
        })
        raise

def main():
    try:
        # Log all arguments for debugging
        logger.info(f"comfygen.py called with {len(sys.argv) - 1} arguments")
        for i, arg in enumerate(sys.argv):
            logger.info(f"Argument {i}: {arg}")

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
        if request_type == 'standard': # Standard /comfy command
            full_prompt = sys.argv[7]
            resolution = sys.argv[8]
            loras = json.loads(sys.argv[9])
            upscale_factor = int(sys.argv[10])
            workflow_filename = sys.argv[11]
            seed = sys.argv[12] if len(sys.argv) > 12 else None

            # Send initial status
            send_progress_update("localhost", request_id, {
                'status': 'starting',
                'message': 'Starting Generation process...'
            })

            # Load workflow
            with open(workflow_filename, 'r') as f:
                workflow = json.load(f)

            # Connect to websocket
            server_address = "127.0.0.1:8188"
            client_id = str(uuid.uuid4())
            ws_url = f"ws://{server_address}/ws?clientId={client_id}"
            logger.info(f"Connecting to ComfyUI server at {ws_url}")

            ws = websocket.create_connection(ws_url, timeout=120)
            logger.info(f"Successfully connected to ComfyUI server with client ID {client_id}")

            # Clear cache
            clear_cache(ws)

            # Generate images
            get_images(server_address, "localhost", request_id, ws, workflow)

    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        if 'request_id' in locals():
            send_progress_update("localhost", request_id, {
                "status": "error",
                "message": f"Error: {str(e)}"
            })
    finally:
        # Close websocket
        if 'ws' in locals():
            try:
                ws.close()
                logger.info("WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error closing WebSocket: {str(e)}")

if __name__ == "__main__":
    main()
