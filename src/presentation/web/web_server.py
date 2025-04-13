from aiohttp import web
import logging
import discord
import io
import asyncio
import time
import os
import shutil
from aiohttp import web
from src.domain.models.queue_item import RequestItem
from src.presentation.web.image_handler import create_view_for_request, create_embed_for_image

logger = logging.getLogger(__name__)

async def register_request(request):
    """Register a request for progress updates"""
    try:
        data = await request.json()
        request_id = data.get('request_id')
        user_id = data.get('user_id')
        channel_id = data.get('channel_id')
        interaction_id = data.get('interaction_id')
        original_message_id = data.get('original_message_id')

        if not request_id or not user_id or not channel_id or not original_message_id:
            return web.Response(text="Missing required fields", status=400)

        # Create a RequestItem
        request_item = RequestItem(
            id=request_id,
            user_id=user_id,
            channel_id=channel_id,
            interaction_id=interaction_id,
            original_message_id=original_message_id,
            prompt="",  # These fields are required but not used for progress updates
            resolution="",
            loras=[],
            upscale_factor=1,
            workflow_filename=""
        )

        # Add to pending requests
        request.app['bot'].pending_requests[request_id] = request_item
        logger.info(f"Registered request {request_id} for progress updates")

        return web.Response(text="Request registered")
    except Exception as e:
        logger.error(f"Error registering request: {str(e)}")
        return web.Response(text=f"Error: {str(e)}", status=500)

async def update_progress(request):
    try:
        data = await request.json()
        request_id = data.get('request_id')
        progress_data = data.get('progress_data', {})

        if not request_id:
            return web.Response(text="Missing request_id", status=400)

        # Log all pending request IDs for debugging
        logger.info(f"Pending request IDs: {list(request.app['bot'].pending_requests.keys())}")

        # Try to get the request item from pending requests
        request_item = None
        if request_id in request.app['bot'].pending_requests:
            request_item = request.app['bot'].pending_requests[request_id]
        else:
            # If not in pending requests, try to get from database
            if 'image_repository' in request.app and request.app['image_repository']:
                image_data = await request.app['image_repository'].get_image_generation(request_id)
                if image_data:
                    # Create a RequestItem from the database data
                    request_item = await request.app['image_repository'].create_request_item_from_data(image_data)
                    # Add to pending requests for future updates
                    request.app['bot'].pending_requests[request_id] = request_item
                    logger.info(f"Loaded request {request_id} from database")

        if not request_item:
            logger.warning(f"Unknown request_id: {request_id}")
            return web.Response(text="Unknown request_id", status=404)

        try:
            # Get the channel and message
            channel = await request.app['bot'].fetch_channel(int(request_item.channel_id))
            message = await channel.fetch_message(int(request_item.original_message_id))

            # Get progress data
            status = progress_data.get('status', '')
            progress_message = progress_data.get('message', 'Processing...')
            progress = progress_data.get('progress', 0)

            # Import message constants
            try:
                from Main.custom_commands.message_constants import STATUS_MESSAGES
            except ImportError:
                # Fallback if import fails
                STATUS_MESSAGES = {
                    'starting': {'message': 'Starting Generation process...', 'emoji': '⚙️'},
                    'loading_workflow': {'message': 'Loading workflow...', 'emoji': '⚙️'},
                    'initializing': {'message': 'Initializing parameters...', 'emoji': '⚙️'},
                    'connecting': {'message': 'Connecting to ComfyUI...', 'emoji': '⚙️'},
                    'loading_models': {'message': 'Sending workflow and settings...', 'emoji': '⚙️'},
                    'execution': {'message': 'Loading Models...', 'emoji': '⚙️'},
                    'cached': {'message': 'Loading Cached Models...', 'emoji': '📦'},
                    'generating': {'message': 'Generating...', 'emoji': '🎨'},
                    'upscaling': {'message': 'Finalizing Generation...', 'emoji': '🔍'},
                    'complete': {'message': 'Generation complete!', 'emoji': '✅'},
                    'error': {'message': 'Error:', 'emoji': '❌'}
                }

            # Check if a custom message is provided
            if 'message' in progress_data:
                # Use the custom message with the appropriate emoji
                status_info = STATUS_MESSAGES.get(status, {
                    'message': progress_data['message'],
                    'emoji': '⚙️'
                })
                formatted_message = f"{status_info['emoji']} {progress_data['message']}"
            else:
                # Get status info from constants for standard messages
                status_info = STATUS_MESSAGES.get(status, {
                    'message': progress_message,
                    'emoji': '⚙️'
                })

                # Special case for 100% generation - switch to upscaling
                if status == 'generating' and progress == 100:
                    status = 'upscaling'
                    status_info = STATUS_MESSAGES['upscaling']
                    formatted_message = f"{status_info['emoji']} {status_info['message']}"
                elif status == 'generating':
                    formatted_message = f"{status_info['emoji']} {status_info['message']} {progress}%"
                elif status == 'error':
                    formatted_message = f"{status_info['emoji']} {status_info['message']} {progress_message}"
                    # Only remove on error
                    if request_id in request.app['bot'].pending_requests:
                        del request.app['bot'].pending_requests[request_id]
                else:
                    formatted_message = f"{status_info['emoji']} {status_info['message']}"

            # Update the message with rate limit handling
            try:
                # Use a short timeout to avoid blocking
                await asyncio.wait_for(
                    message.edit(content=formatted_message),
                    timeout=2.0  # 2 second timeout
                )
                logger.info(f"Updated progress message: {formatted_message}")
            except asyncio.TimeoutError:
                logger.warning("Message edit timed out, likely due to Discord rate limits")
            except discord.errors.HTTPException as e:
                if e.status == 429:  # Rate limit error
                    retry_after = e.retry_after
                    logger.warning(f"Rate limited by Discord. Retry after {retry_after} seconds")
                else:
                    logger.error(f"HTTP error updating message: {e}")

            return web.Response(text="Progress updated")

        except discord.errors.NotFound:
            logger.warning(f"Message {request_item.original_message_id} not found")
            return web.Response(text="Message not found", status=404)

        except discord.errors.Forbidden:
            logger.warning("Bot lacks permission to edit message")
            return web.Response(text="Permission denied", status=403)

        except Exception as e:
            logger.error(f"Error updating progress message: {str(e)}")
            return web.Response(text=f"Error: {str(e)}", status=500)

    except Exception as e:
        logger.error(f"Error in update_progress: {str(e)}")
        return web.Response(text="Internal server error", status=500)

async def send_image(request):
    try:
        logger.info("Received image send request")

        # Get multipart form data
        reader = await request.multipart()
        request_id = None
        image_data = None
        filename = None

        # Process all form fields
        while True:
            field = await reader.next()
            if field is None:
                break

            if field.name == 'request_id':
                request_id = await field.text()
                logger.info(f"Got request_id: {request_id}")
            elif field.name == 'image_data' or field.name == 'video_data':
                image_data = await field.read()
                filename = field.filename
                is_video = field.name == 'video_data'
                logger.info(f"Got {'video' if is_video else 'image'} data: {filename}, size: {len(image_data)} bytes")

        if not request_id:
            logger.error("Missing request_id")
            return web.Response(text="Missing request_id", status=400)

        if not image_data:
            logger.error("Missing image data")
            return web.Response(text="Missing image data", status=400)

        # Try to get the request item from pending requests
        request_item = None
        if request_id in request.app['bot'].pending_requests:
            request_item = request.app['bot'].pending_requests[request_id]
        else:
            # If not in pending requests, try to get from database
            if 'image_repository' in request.app and request.app['image_repository']:
                image_data = await request.app['image_repository'].get_image_generation(request_id)
                if image_data:
                    # Create a RequestItem from the database data
                    request_item = await request.app['image_repository'].create_request_item_from_data(image_data)
                    # Add to pending requests for future updates
                    request.app['bot'].pending_requests[request_id] = request_item
                    logger.info(f"Loaded request {request_id} from database")

        if not request_item:
            logger.warning(f"Unknown request_id: {request_id}")
            return web.Response(text="Unknown request_id", status=404)

        # Set is_video flag based on the field name or file extension
        if 'is_video' in locals() and is_video:
            request_item.is_video = True
        elif filename and filename.lower().endswith(('.mp4', '.webm', '.avi', '.mov', '.mkv')):
            request_item.is_video = True

        logger.info(f"Found request item: {request_item.channel_id}, {request_item.original_message_id}, is_video: {getattr(request_item, 'is_video', False)}")

        try:
            # Get the channel and message
            channel = await request.app['bot'].fetch_channel(int(request_item.channel_id))
            message = await channel.fetch_message(int(request_item.original_message_id))

            # Create a discord file from the image or video data
            is_video = request_item.is_video or filename.lower().endswith(('.mp4', '.webm', '.avi', '.mov', '.mkv'))

            # Log the image size for debugging
            image_size_mb = len(image_data) / (1024 * 1024)
            logger.info(f"Image size is {image_size_mb:.2f}MB")

            # Always create the discord file with the image data
            discord_file = discord.File(io.BytesIO(image_data), filename=filename)

            # Get the user who requested the image
            try:
                # First try to get the member from the guild to get their color
                guild = channel.guild if hasattr(channel, 'guild') else None
                if guild:
                    member = await guild.fetch_member(int(request_item.user_id))
                    user_name = member.display_name
                    user_color = member.color if member.color.value != 0 else discord.Color.green()
                    user = member
                else:
                    # Fallback to fetching just the user
                    user = await request.app['bot'].fetch_user(int(request_item.user_id))
                    user_name = user.display_name
                    user_color = discord.Color.green()
            except Exception as e:
                logger.warning(f"Could not fetch user {request_item.user_id}: {e}")
                user_name = "Unknown User"
                user_color = discord.Color.green()
                user = None

            # Create an embed for the image or video with detailed information
            is_video = getattr(request_item, 'is_video', False) or filename.lower().endswith(('.mp4', '.webm', '.avi', '.mov', '.mkv'))
            media_type = "Video" if is_video else "Image"
            embed = discord.Embed(title=f"{media_type} Generated by {user_name}", color=user_color)
            embed.add_field(name="Prompt", value=request_item.prompt, inline=False)
            embed.add_field(name="Resolution", value=request_item.resolution, inline=True)
            if request_item.seed:
                embed.add_field(name="Seed", value=str(request_item.seed), inline=True)
            embed.add_field(name="Upscale Factor", value=str(request_item.upscale_factor), inline=True)
            if request_item.loras and len(request_item.loras) > 0:
                lora_text = ", ".join(request_item.loras)
                embed.add_field(name="LoRAs", value=lora_text, inline=False)

            # For videos, we don't set the image in the embed
            # This allows Discord to show the video as a playable attachment
            if not is_video:
                embed.set_image(url=f"attachment://{filename}")

            # Set the footer with the user's name and avatar
            if user and hasattr(user, 'avatar') and user.avatar:
                embed.set_footer(text=f"Generated by {user_name}", icon_url=user.avatar.url)

            # Create the appropriate control view based on content type
            if is_video:
                # For videos, use the VideoControlView (no options button)
                from src.presentation.discord.views import VideoControlView
                view = VideoControlView(
                    bot=request.app['bot'],
                    original_prompt=request_item.prompt,
                    video_filename=filename,
                    original_seed=request_item.seed
                )
            else:
                # For images, use the appropriate view based on request type
                # Check if this is a redux or pulid request
                is_redux = False
                is_pulid = False

                # Check if this is a redux request by examining the request_item type
                if hasattr(request_item, 'is_redux'):
                    is_redux = request_item.is_redux
                    logger.info(f"Request {request_id} has is_redux attribute: {is_redux}")

                # Check if this is a pulid request by examining the request_item type
                if hasattr(request_item, 'is_pulid'):
                    is_pulid = request_item.is_pulid
                    logger.info(f"Request {request_id} has is_pulid attribute: {is_pulid}")

                # Also check if this is a ReduxRequestItem type
                from src.domain.models.queue_item import ReduxRequestItem
                if isinstance(request_item, ReduxRequestItem):
                    is_redux = True
                    logger.info(f"Request {request_id} is a ReduxRequestItem instance")

                # Check if the command name contains 'redux' or 'pulid'
                if hasattr(request_item, 'command_name'):
                    if 'redux' in request_item.command_name.lower():
                        is_redux = True
                        logger.info(f"Request {request_id} has redux in command name: {request_item.command_name}")
                    elif 'pulid' in request_item.command_name.lower():
                        is_pulid = True
                        logger.info(f"Request {request_id} has pulid in command name: {request_item.command_name}")

                # Check if the workflow filename contains 'pulid'
                if hasattr(request_item, 'workflow_filename') and request_item.workflow_filename:
                    if 'pulid' in request_item.workflow_filename.lower():
                        is_pulid = True
                        logger.info(f"Request {request_id} has pulid in workflow filename: {request_item.workflow_filename}")

                logger.info(f"Request {request_id} final determinations: is_redux={is_redux}, is_pulid={is_pulid}")

                if is_redux:
                    # For redux images, use the ReduxView (only delete button)
                    from src.presentation.discord.views.redux_view import ReduxView
                    view = ReduxView(user_id=int(request_item.user_id))
                    logger.info(f"Using ReduxView for request {request_id} with user_id={request_item.user_id}")
                elif is_pulid:
                    # For pulid images, use the PulidView (only delete button)
                    from src.presentation.discord.views.pulid_view import PulidView
                    view = PulidView(user_id=int(request_item.user_id))
                    logger.info(f"Using PulidView for request {request_id} with user_id={request_item.user_id}")
                else:
                    # For standard images, use the full ImageControlView
                    from src.presentation.discord.views import ImageControlView
                    view = ImageControlView(
                        bot=request.app['bot'],
                        original_prompt=request_item.prompt,
                        image_filename=filename,
                        original_resolution=request_item.resolution,
                        original_loras=request_item.loras,
                        original_upscale_factor=request_item.upscale_factor,
                        original_seed=request_item.seed
                    )

            # CRITICAL PRIORITY: Update the original message with the media, embed, and view
            # This is the most important part for user experience - do this FIRST and IMMEDIATELY
            # Use a very short timeout to ensure the message is sent as fast as possible
            try:
                # OPTIMIZATION: Use asyncio.wait_for with a short timeout to ensure we don't block
                # First, try to edit the message with the file
                try:
                    await asyncio.wait_for(
                        message.edit(content=f"✅ Generation complete!", embed=embed, attachments=[discord_file], view=view),
                        timeout=10.0  # Increased timeout for larger files
                    )
                except Exception as edit_error:
                    logger.error(f"Error editing message with attachment: {edit_error}")
                    # If editing fails, try sending a new message with the file
                    try:
                        # Send a new message with the file
                        new_message = await channel.send(content=f"✅ Generation complete for request {request_id}!", file=discord_file)
                        logger.info(f"Sent image as a new message after edit error")

                        # Try to add the embed and view to the new message
                        try:
                            await new_message.edit(embed=embed, view=view)
                        except Exception as embed_error:
                            logger.warning(f"Could not add embed/view to new message: {embed_error}")

                        # Update the original message to reference the new message
                        await message.edit(content=f"✅ Generation complete! Image sent in a separate message.")
                    except Exception as send_error:
                        logger.error(f"Error sending new message with attachment: {send_error}")
                        # If sending a new message fails, try one more time with just the file
                        try:
                            simple_file = discord.File(io.BytesIO(image_data), filename=filename)
                            await channel.send(file=simple_file)
                            await message.edit(content=f"✅ Generation complete! Image sent in a separate message.")
                        except Exception as final_error:
                            logger.error(f"Final attempt to send image failed: {final_error}")
                            await message.edit(content=f"✅ Generation complete! Could not send image due to Discord limitations.")

                logger.info(f"Successfully sent image to Discord for request {request_id}")

                # Remove from pending requests immediately after sending to Discord
                if request_id in request.app['bot'].pending_requests:
                    del request.app['bot'].pending_requests[request_id]
                    logger.info(f"Removed request {request_id} from pending_requests")
            except asyncio.TimeoutError:
                logger.warning(f"Timeout sending image to Discord for request {request_id}, but the operation continues in the background")
            except Exception as e:
                logger.error(f"Error sending image to Discord: {e}")
                # Try to send a direct message to the channel as a last resort
                try:
                    # Create a simple file without the embed
                    simple_file = discord.File(io.BytesIO(image_data), filename=filename)
                    await channel.send(content=f"⚠️ Error updating the original message. Here's your generated image for request {request_id}:", file=simple_file)
                    logger.info(f"Sent image as a new message after error")

                    # Try to update the original message
                    try:
                        await message.edit(content=f"✅ Generation complete! Image sent in a separate message.")
                    except Exception:
                        pass
                except Exception as send_error:
                    logger.error(f"Failed to send image as a new message: {send_error}")
                    # One final attempt with minimal content
                    try:
                        final_file = discord.File(io.BytesIO(image_data), filename=filename)
                        await channel.send(file=final_file)
                    except Exception as final_error:
                        logger.error(f"All attempts to send image failed: {final_error}")

            # Save image to disk in the background
            if 'image_repository' in request.app and request.app['image_repository']:
                try:
                    # Save the image to disk
                    image_path = f"output/{filename}"
                    with open(image_path, 'wb') as f:
                        f.write(image_data)

                    # Calculate generation time
                    generation_time = time.time() - request_item.created_at if hasattr(request_item, 'created_at') else None

                    # Save to database
                    asyncio.create_task(request.app['image_repository'].save_image_generation(
                        request_id=request_id,
                        request_item=request_item,
                        image_path=image_path,
                        generation_time=generation_time,
                        completed=True
                    ))
                    logger.info(f"Started background task to save image generation data for request {request_id}")

                    # Clean up temporary files for Redux requests
                    if hasattr(request_item, 'is_redux') and request_item.is_redux:
                        asyncio.create_task(cleanup_redux_files(request_id))
                        logger.info(f"Started background task to clean up Redux files for request {request_id}")
                except Exception as e:
                    logger.error(f"Error preparing database save: {e}")

            return web.json_response({"status": "success", "message": "Image received and sent to Discord"})

        except discord.errors.NotFound:
            logger.warning(f"Message {request_item.original_message_id} not found")
            return web.Response(text="Message not found", status=404)

        except discord.errors.Forbidden:
            logger.warning("Bot lacks permission to edit message")
            return web.Response(text="Permission denied", status=403)

        except Exception as e:
            error_message = str(e)
            # Check for specific error messages and provide more helpful information
            if "No outputs found in history" in error_message:
                error_message = "Video generation failed. Please try again or use a different prompt."
            elif "HTTP Error 404" in error_message:
                error_message = "Video file not found. The generation may have failed."

            logger.error(f"Error sending image/video: {error_message}")

            # Update progress with the error message
            await update_progress(request_id, {
                "status": "error",
                "message": f"Error: {error_message}"
            }, request.app)

            return web.Response(text=f"Error: {error_message}", status=500)

    except Exception as e:
        logger.error(f"Error in send_image: {str(e)}")
        return web.Response(text="Internal server error", status=500)

async def cleanup_redux_files(request_id):
    """
    Clean up temporary files created for Redux requests
    """
    try:
        # Define the directory path
        redux_dir = os.path.join('output', request_id)

        # Check if the directory exists
        if os.path.exists(redux_dir):
            # Remove the directory and all its contents
            shutil.rmtree(redux_dir)
            logger.info(f"Removed Redux directory: {redux_dir}")

        # Also remove the temporary workflow file
        temp_workflow_path = os.path.join('output', f"temp_workflow_{request_id}.json")
        if os.path.exists(temp_workflow_path):
            os.remove(temp_workflow_path)
            logger.info(f"Removed temporary workflow file: {temp_workflow_path}")

    except Exception as e:
        logger.error(f"Error cleaning up Redux files: {e}")

async def start_web_server(bot, port=8090, image_repository=None):
    app = web.Application()

    # Setup routes
    app.router.add_post('/register_request', register_request)
    app.router.add_post('/update_progress', update_progress)
    app.router.add_post('/send_image', send_image)
    app.router.add_post('/image_generated', send_image)  # Alias for compatibility

    app['bot'] = bot

    # Store image repository in app if provided
    if image_repository:
        app['image_repository'] = image_repository
        logger.info("Image repository initialized for web server")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()

    logger.info(f"Web server started on 0.0.0.0:{port}")

    return app
