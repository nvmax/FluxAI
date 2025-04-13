import websocket
import json
import uuid
import time
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def monitor_comfyui_websocket():
    """
    Monitor the ComfyUI WebSocket API to see real-time progress updates.
    This script helps verify that ComfyUI is sending progress updates correctly.
    """
    try:
        # Connect to ComfyUI WebSocket
        server_address = "127.0.0.1:8188"
        client_id = str(uuid.uuid4())
        ws_url = f"ws://{server_address}/ws?clientId={client_id}"
        
        logger.info(f"Connecting to ComfyUI WebSocket at {ws_url}")
        ws = websocket.create_connection(ws_url, timeout=10)
        logger.info("Connected to ComfyUI WebSocket")
        
        # Monitor WebSocket messages
        logger.info("Monitoring WebSocket messages. Press Ctrl+C to stop.")
        start_time = time.time()
        
        while True:
            try:
                message = ws.recv()
                if not message:
                    continue
                
                # Parse the message
                data = json.loads(message)
                message_type = data.get('type', 'unknown')
                elapsed_time = time.time() - start_time
                
                # Handle different message types
                if message_type == 'progress':
                    progress_data = data.get('data', {})
                    current_step = progress_data.get('value', 0)
                    max_steps = progress_data.get('max', 1)
                    node = progress_data.get('node', 'unknown')
                    progress_percent = int((current_step / max_steps) * 100)
                    
                    logger.info(f"[{elapsed_time:.2f}s] PROGRESS: Node {node}: {current_step}/{max_steps} ({progress_percent}%)")
                
                elif message_type == 'executing':
                    node = data.get('data', {}).get('node')
                    prompt_id = data.get('data', {}).get('prompt_id', 'unknown')
                    
                    if node is None:
                        logger.info(f"[{elapsed_time:.2f}s] EXECUTION COMPLETE for prompt {prompt_id}")
                    else:
                        logger.info(f"[{elapsed_time:.2f}s] EXECUTING: Node {node}")
                
                elif message_type == 'executed':
                    node = data.get('data', {}).get('node')
                    prompt_id = data.get('data', {}).get('prompt_id', 'unknown')
                    logger.info(f"[{elapsed_time:.2f}s] EXECUTED: Node {node} for prompt {prompt_id}")
                
                elif message_type == 'execution_start':
                    logger.info(f"[{elapsed_time:.2f}s] EXECUTION STARTED")
                
                elif message_type == 'execution_cached':
                    nodes = data.get('data', {}).get('nodes', [])
                    logger.info(f"[{elapsed_time:.2f}s] CACHED EXECUTION: Nodes {', '.join(map(str, nodes))}")
                
                elif message_type == 'status':
                    # Status messages are frequent, so we'll only log them if they contain interesting info
                    queue_remaining = data.get('data', {}).get('status', {}).get('exec_info', {}).get('queue_remaining', 0)
                    if queue_remaining > 0:
                        logger.info(f"[{elapsed_time:.2f}s] STATUS: Queue remaining: {queue_remaining}")
                
                else:
                    # Log other message types
                    logger.info(f"[{elapsed_time:.2f}s] {message_type.upper()}: {json.dumps(data.get('data', {}))[:100]}...")
            
            except websocket.WebSocketTimeoutException:
                logger.info("WebSocket timeout, continuing...")
            except json.JSONDecodeError:
                logger.warning("Received invalid JSON")
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
    
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    finally:
        if 'ws' in locals():
            ws.close()
            logger.info("WebSocket connection closed")

if __name__ == "__main__":
    monitor_comfyui_websocket()
