# Flux AI Discord Bot Architecture

This document describes the architecture of the Flux AI Discord Bot application.

## Overview

Flux AI Discord Bot is a Discord bot for image generation using ComfyUI. It allows users to generate images from prompts, use reference images for image mixing (Redux), create personalized images with user-provided reference images (PuLID), generate videos, and more.

The application follows a layered architecture with the following components:

1. **Presentation Layer**: Discord bot interface, commands, and views
2. **Application Layer**: Core business logic and services
3. **Domain Layer**: Core domain models and business rules
4. **Infrastructure Layer**: External services, database, and web server

## Directory Structure

```
Flux AI Discord Bot/
├── src/                           # All source code
│   ├── presentation/              # User interface layer
│   │   ├── discord/               # Discord-specific code
│   │   │   ├── bot.py             # Main bot class
│   │   │   ├── commands/          # Command handlers
│   │   │   │   ├── image_commands.py    # Image generation commands
│   │   │   │   ├── queue_commands.py    # Queue management commands
│   │   │   │   ├── analytics_commands.py # Analytics commands
│   │   │   │   ├── filter_commands.py   # Content filter commands
│   │   │   │   └── lora_commands.py     # LoRA management commands
│   │   │   ├── views/             # UI components
│   │   │   │   ├── image_view.py        # Image display view
│   │   │   │   ├── prompt_modal.py      # Prompt input modal
│   │   │   │   ├── redux_modal.py       # Redux settings modal
│   │   │   │   ├── redux_view.py        # Redux workflow view
│   │   │   │   ├── pulid_modal.py       # PuLID settings modal
│   │   │   │   ├── pulid_view.py        # PuLID workflow view
│   │   │   │   ├── image_control_view.py # Image control buttons
│   │   │   │   ├── video_control_view.py # Video control buttons
│   │   │   │   ├── enhancement_modal.py  # AI enhancement modal
│   │   │   │   └── lora_selection_view.py # LoRA selection view
│   │   │   └── events/            # Event handlers
│   │   └── web/                   # Web interface
│   │       ├── server.py          # Web server
│   │       ├── web_server.py      # Web server implementation
│   │       └── image_handler.py   # Image request handler
│   ├── application/               # Application services
│   │   ├── image_generation/      # Image generation service
│   │   │   └── image_generation_service.py # Image generation logic
│   │   ├── queue/                 # Queue management
│   │   │   └── queue_service.py   # Queue processing logic
│   │   ├── analytics/             # Analytics service
│   │   │   └── analytics_service.py # Usage tracking and statistics
│   │   ├── content_filter/        # Content filtering
│   │   │   ├── content_filter_service.py # Content filtering logic
│   │   │   └── transformer_content_filter.py # ML-based content filter
│   │   ├── ai/                    # AI services
│   │   │   └── ai_service.py      # AI prompt enhancement
│   │   └── lora_management/       # LoRA management
│   ├── domain/                    # Domain models and logic
│   │   ├── models/                # Core domain models
│   │   │   └── queue_item.py      # Queue item models
│   │   ├── exceptions/            # Domain-specific exceptions
│   │   ├── value_objects/         # Value objects
│   │   ├── interfaces/            # Interfaces for dependencies
│   │   │   ├── ai_provider.py     # AI provider interface
│   │   │   ├── analytics_repository.py # Analytics repository interface
│   │   │   └── queue_repository.py # Queue repository interface
│   │   ├── lora_management/       # LoRA domain logic
│   │   │   └── lora_manager.py    # LoRA management logic
│   │   └── events/                # Domain events
│   │       ├── event_bus.py       # Event publishing system
│   │       └── common_events.py   # Common event definitions
│   ├── infrastructure/            # External services and persistence
│   │   ├── database/              # Database access
│   │   │   ├── database_service.py # Database connection
│   │   │   ├── analytics_repository.py # Analytics data storage
│   │   │   ├── queue_repository.py # Queue data storage
│   │   │   └── image_repository.py # Image metadata storage
│   │   ├── ai_providers/          # AI provider implementations
│   │   │   ├── provider_factory.py # AI provider factory
│   │   │   ├── anthropic_provider.py # Anthropic Claude integration
│   │   │   ├── openai_provider.py # OpenAI integration
│   │   │   ├── xai_provider.py    # XAI integration
│   │   │   └── lmstudio_provider.py # Local LM Studio integration
│   │   ├── comfyui/               # ComfyUI integration
│   │   │   └── comfyui_service.py # ComfyUI API client
│   │   ├── storage/               # File storage
│   │   ├── config/                # Configuration management
│   │   │   ├── config_manager.py  # Configuration access
│   │   │   └── config_loader.py   # Configuration loading
│   │   └── di/                    # Dependency injection
│   │       └── container.py       # DI container implementation
├── config/                        # Configuration files
│   ├── ratios.json                # Image resolution ratios
│   ├── lora.json                  # LoRA definitions
│   ├── fluxfusion*.json           # ComfyUI workflows for image generation
│   ├── Pulid*.json                # ComfyUI workflows for PuLID
│   ├── Redux.json                 # ComfyUI workflow for Redux
│   └── Video.json                 # ComfyUI workflow for video generation
├── lora_editor/                   # LoRA management tool
│   ├── main.py                    # LoRA editor entry point
│   ├── app.py                     # Main application
│   ├── lora_editor.py             # Legacy editor implementation
│   ├── lora_database.py           # LoRA database operations
│   ├── controllers/               # MVC controllers
│   ├── models/                    # MVC models
│   ├── views/                     # MVC views
│   ├── dialogs/                   # UI dialogs
│   ├── ui/                        # UI components
│   ├── utils/                     # Utility functions
│   └── downloaders/               # LoRA download implementations
├── setup/                         # Setup utilities
│   ├── comfyui_validator.py       # ComfyUI installation validator
│   ├── setup_support.py           # Setup helper functions
│   ├── setup_ui.py                # Setup UI implementation
│   └── required_files/            # Files needed for setup
├── scripts/                       # Utility scripts
├── logs/                          # Log files
├── docs/                          # Documentation
├── run.py                         # Main entry point
├── setup.py                       # Setup tool entry point
└── comfyui_monitor.py             # ComfyUI monitoring utility
```

## Key Components

### Presentation Layer

The presentation layer handles user interactions through Discord and the web server.

#### Discord Bot

The Discord bot is implemented in `src/presentation/discord/bot.py`. It handles Discord interactions and commands, including command registration, event handling, and message processing.

Commands are organized into cogs in the `src/presentation/discord/commands/` directory:

- `image_commands.py`: Commands for generating images (/comfy, /redux, /pulid, /video)
- `queue_commands.py`: Commands for managing the queue (/queue, /clear_queue, /set_queue_priority)
- `analytics_commands.py`: Commands for viewing analytics (/stats, /reset_stats)
- `filter_commands.py`: Commands for managing content filters and user warnings/bans
- `lora_commands.py`: Commands for managing and viewing LoRAs (/lorainfo)

Views are implemented in the `src/presentation/discord/views/` directory:

- `image_view.py`: View for displaying generated images
- `image_control_view.py`: Buttons for controlling generated images
- `video_control_view.py`: Buttons for controlling generated videos
- `prompt_modal.py`: Modal for entering prompts
- `enhancement_modal.py`: Modal for AI prompt enhancement
- `redux_modal.py`: Modal for Redux image generation settings
- `redux_view.py`: View for Redux workflow
- `redux_image_view.py`: View for displaying Redux-generated images
- `pulid_modal.py`: Modal for PuLID image generation settings
- `pulid_view.py`: View for PuLID workflow
- `lora_selection_view.py`: View for selecting LoRAs to apply

#### Web Server

The web server is implemented in `src/presentation/web/web_server.py` and `src/presentation/web/server.py`. It handles callbacks from ComfyUI, processes generation progress updates, and serves generated images. The `image_handler.py` file handles image-specific requests and responses.

### Application Layer

The application layer contains the core business logic of the application.

#### Queue Service

The queue service is implemented in `src/application/queue/queue_service.py`. It manages the image generation queue, handling priorities, rate limiting, and user request limits (50 requests per hour per user).

#### Analytics Service

The analytics service is implemented in `src/application/analytics/analytics_service.py`. It tracks and analyzes application usage, including command usage statistics, generation times for different types of content (images vs videos), and user activity.

#### Content Filter Service

The content filter service is implemented in `src/application/content_filter/content_filter_service.py`. It filters inappropriate content from prompts using multiple methods:

1. Banned words list (stored in database and backed up in JSON)
2. Regular expression patterns for context-aware filtering
3. Transformer-based content filtering using Microsoft's content safety model

The service also manages a warning system for users who attempt to generate inappropriate content, with configurable thresholds and ban options.

#### Image Generation Service

The image generation service is implemented in `src/application/image_generation/image_generation_service.py`. It handles the image generation process by:

1. Preparing workflows for ComfyUI based on command type (comfy, redux, pulid, video)
2. Setting appropriate parameters (prompts, resolution, LoRAs, seeds)
3. Sending requests to ComfyUI
4. Processing and returning the generated content
5. Cleaning up temporary files

#### AI Service

The AI service is implemented in `src/application/ai/ai_service.py`. It provides AI-powered prompt enhancement using various AI providers (OpenAI, Anthropic, XAI, LM Studio) configured in the .env file.

### Domain Layer

The domain layer contains the core domain models and rules.

#### Models

Domain models are implemented in the `src/domain/models/` directory:

- `queue_item.py`: Models for queue items and different request types (standard, redux, pulid, video)

#### Events

Domain events are implemented in the `src/domain/events/` directory:

- `event_bus.py`: Event bus for publishing and subscribing to events
- `common_events.py`: Common domain events like CommandExecutedEvent

#### Interfaces

Interfaces for dependencies are implemented in the `src/domain/interfaces/` directory:

- `queue_repository.py`: Interface for queue data access
- `analytics_repository.py`: Interface for analytics data access
- `ai_provider.py`: Interface for AI providers

#### LoRA Management

LoRA management domain logic is implemented in `src/domain/lora_management/lora_manager.py`. It provides domain-level operations for managing LoRAs.

### Infrastructure Layer

The infrastructure layer handles external services and persistence.

#### Database Service

The database service is implemented in `src/infrastructure/database/database_service.py`. It provides a centralized way to access the SQLite database, which stores:

- Queue items and request history
- Analytics data
- Content filter rules (banned words, regex patterns, context rules)
- User warnings and bans
- Image metadata

#### ComfyUI Service

The ComfyUI service is implemented in `src/infrastructure/comfyui/comfyui_service.py`. It handles interactions with ComfyUI's API, including:

- Sending workflow requests
- Monitoring generation progress
- Retrieving generated images and videos
- Managing workflow files and parameters

#### AI Provider Factory

The AI provider factory is implemented in `src/infrastructure/ai_providers/provider_factory.py`. It manages the creation of AI provider instances based on configuration. Supported providers include:

- OpenAI (GPT models)
- Anthropic (Claude models)
- XAI (custom provider)
- LM Studio (local models)

#### Configuration Manager

The configuration manager is implemented in `src/infrastructure/config/config_manager.py`. It centralizes all configuration loading and access, including:

- Environment variables from .env file
- JSON configuration files from the config directory
- ComfyUI workflow files
- Content filter settings

#### Dependency Injection Container

The dependency injection container is implemented in `src/infrastructure/di/container.py`. It provides a simple way to register and resolve dependencies, reducing tight coupling between components.

## Flow of Control

### Standard Image Generation (/comfy)

1. User sends a /comfy command to the Discord bot with prompt and resolution
2. Command handler processes the command, optionally showing a LoRA selection modal
3. Content filter service checks the prompt for inappropriate content
4. Request is added to the queue with appropriate priority
5. Queue service processes the request when it reaches the front of the queue
6. Image generation service prepares the workflow and sends it to ComfyUI
7. ComfyUI generates the image and sends progress updates
8. Web server receives the completed image
9. Discord bot displays the image to the user with an image control view

### Redux Image Generation (/redux)

1. User sends a /redux command with resolution parameter
2. Bot shows a modal to collect strength parameters
3. User uploads two reference images sequentially
4. Request is added to the queue
5. Image generation service prepares the Redux workflow with both images
6. ComfyUI generates a mixed image based on the reference images
7. Discord bot displays the result with appropriate controls

### PuLID Image Generation (/pulid)

1. User sends a /pulid command with prompt and resolution
2. Bot shows a modal for LoRA selection
3. User uploads a reference image
4. Request is added to the queue
5. Image generation service prepares the PuLID workflow
6. ComfyUI generates a personalized image based on the reference and prompt
7. Discord bot displays the result with appropriate controls

### Video Generation (/video)

1. User sends a /video command with a prompt
2. Request is added to the queue
3. Image generation service prepares the video workflow
4. ComfyUI generates a video based on the prompt
5. Discord bot displays the video with video control options

## Event-Driven Architecture

The application uses an event-driven architecture for cross-cutting concerns:

1. Events are published to the event bus (e.g., CommandExecutedEvent)
2. Event handlers subscribe to events
3. Event handlers process events asynchronously

This allows for loose coupling between components and makes it easier to add new features. For example, the analytics service subscribes to command execution events to track usage statistics without the command handlers needing to know about analytics.

## Dependency Injection

The application uses a simple dependency injection system to reduce tight coupling:

1. Services are registered with the DI container in the main application entry point
2. Services are resolved from the container when needed
3. Services depend on interfaces, not concrete implementations

This makes it easier to test and replace components. For example, the image generation service depends on the ComfyUI service interface, not its concrete implementation, making it possible to swap out the ComfyUI integration without changing the image generation logic.

## Configuration

Configuration is centralized in the `src/infrastructure/config/config_manager.py` file. It loads configuration from:

1. Environment variables in the .env file
2. JSON files in the `config/` directory (ratios.json, lora.json, workflow files)

This makes it easier to manage configuration and avoid duplication. The setup tool (setup.py) provides a user-friendly interface for configuring the application, including:

1. Discord bot settings
2. ComfyUI connection settings
3. AI provider configuration
4. Content filter thresholds
5. Rate limiting and warning thresholds

## LoRA Editor

The LoRA editor is a separate application within the project, implemented using an MVC architecture. It allows users to:

1. View and edit LoRA metadata
2. Download LoRAs from Civitai and HuggingFace
3. Check for LoRA updates
4. Organize LoRAs with weights, triggerwords, and active/inactive status

The editor is launched using `lora_editor/main.py` and stores its configuration in `lora_editor/lora_settings.json`.

## Setup and Configuration Tool

The setup tool (`setup.py`) provides a graphical interface for configuring the application. It includes:

1. Discord bot configuration
2. ComfyUI connection settings
3. AI provider selection and configuration
4. Content filter settings
5. System paths and directories

The setup process validates the ComfyUI installation and ensures all required components are properly configured.



 [🏠  Return to main](../readme.md)
