"""
Main application entry point.
"""

import asyncio
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/bot.log', encoding='utf-8')
    ]
)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Set log level for all loggers
logging.getLogger().setLevel(logging.INFO)
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# Import after logging is configured
from src.infrastructure.config.config_manager import ConfigManager
from src.infrastructure.di.container import DIContainer
from src.infrastructure.database.database_service import DatabaseService
from src.infrastructure.database.image_repository import ImageRepository
from src.infrastructure.comfyui.comfyui_service import ComfyUIService
from src.application.queue.queue_service import QueueService
from src.application.analytics.analytics_service import AnalyticsService
from src.application.content_filter.content_filter_service import ContentFilterService
from src.application.image_generation.image_generation_service import ImageGenerationService
from src.presentation.discord.bot import DiscordBot

async def start_queue_processor(queue_service, image_generation_service):
    """Start the queue processor"""
    logger.info("Starting queue processor...")

    async def process_queue_item(item):
        """Process a queue item"""
        logger.info(f"Processing queue item: {item.request_id}")
        success, _, _ = await image_generation_service.generate_image(item)
        logger.info(f"Queue item processed: {item.request_id}, success: {success}")
        return success

    # Start the queue processor
    await queue_service.start_processing(process_queue_item)
    logger.info("Queue processor started")

async def setup_database():
    """Set up the database"""
    logger.info("Setting up database...")

    # Create database service
    db_service = DatabaseService()

    # Create repositories
    from src.infrastructure.database.queue_repository import SQLiteQueueRepository
    from src.infrastructure.database.analytics_repository import SQLiteAnalyticsRepository
    from src.infrastructure.database.image_repository import ImageRepository

    # Initialize repositories
    queue_repository = SQLiteQueueRepository(db_service)
    analytics_repository = SQLiteAnalyticsRepository(db_service)
    image_repository = ImageRepository(db_service)

    return db_service, queue_repository, analytics_repository, image_repository

async def setup_services(db_service, queue_repository, analytics_repository, image_repository):
    """Set up application services"""
    logger.info("Setting up services...")

    # Get configuration
    config = ConfigManager()

    # Create ComfyUI service
    comfyui_service = ComfyUIService(config.server_address)

    # Create analytics service
    analytics_service = AnalyticsService(analytics_repository)

    # Create content filter service
    content_filter_service = ContentFilterService(db_service)

    # Create queue service
    queue_service = QueueService(queue_repository)

    # Create image generation service without bot reference
    image_generation_service = ImageGenerationService(
        comfyui_service=comfyui_service,
        analytics_service=analytics_service,
        config_manager=config,
        image_repository=image_repository,
        bot=None  # We'll set this later
    )

    # Register services with DI container
    container = DIContainer()
    container.register(DatabaseService, db_service)
    container.register(ComfyUIService, comfyui_service)
    container.register(AnalyticsService, analytics_service)
    container.register(ContentFilterService, content_filter_service)
    container.register(ImageGenerationService, image_generation_service)
    container.register(QueueService, queue_service)
    container.register(ImageRepository, image_repository)

    # Note: We don't register the bot in the container to avoid circular dependencies

    # Initialize services
    await queue_service.initialize()

    return container

async def main():
    """Main application entry point"""
    logger.info("=== Starting Application ===")

    try:
        # Set up database and repositories
        db_service, queue_repository, analytics_repository, image_repository = await setup_database()

        # Set up services
        container = await setup_services(db_service, queue_repository, analytics_repository, image_repository)

        # Get services from container
        queue_service = container.resolve(QueueService)
        image_generation_service = container.resolve(ImageGenerationService)
        content_filter_service = container.resolve(ContentFilterService)
        analytics_service = container.resolve(AnalyticsService)

        # Create bot with services injected
        bot = DiscordBot(
            queue_service=queue_service,
            analytics_service=analytics_service,
            content_filter_service=content_filter_service,
            image_generation_service=image_generation_service
        )

        # Set image repository on bot for commands to access
        bot.image_repository = image_repository

        # Set bot reference in image generation service
        image_generation_service.bot = bot

        # Start web server
        from src.presentation.web.web_server import start_web_server
        await start_web_server(bot, port=8090, image_repository=image_repository)

        # Services are already resolved above

        # Start queue processor
        asyncio.create_task(start_queue_processor(queue_service, image_generation_service))

        # Start bot
        config = ConfigManager()
        if not config.discord_token:
            logger.error("No Discord token found. Please check your .env file")
            return

        # Create temp directory if it doesn't exist
        os.makedirs('temp', exist_ok=True)
        os.makedirs('output', exist_ok=True)

        async with bot:
            logger.info("Starting bot...")
            await bot.start(config.discord_token)

    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
