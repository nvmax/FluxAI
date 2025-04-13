# Analytics Commands

This document describes the analytics commands available in the FluxComfyDiscordbot application.

## Overview

The analytics system tracks usage statistics for the bot, including command usage, image generation, and user activity. This data can be viewed using the analytics commands.

## Commands

### /stats

The `/stats` command shows usage statistics for the bot.

**Usage:**
```
/stats [days]
```

**Parameters:**
- `days` (optional): Number of days to show statistics for (default: 7)

**Example:**
```
/stats 30
```

This will show usage statistics for the last 30 days.

**Output:**
The command will display an embed with the following information:
- Image Generation
  - Total Images
  - Average Generation Time
  - Total Videos
  - Average Video Time
- Command Usage
  - Total Commands
  - Popular Commands
- User Activity
  - Total Users
  - Active Users
- Popular Resolutions

### /reset_stats

The `/reset_stats` command resets all usage statistics. This command can only be used by administrators or users with the Bot Manager role.

**Usage:**
```
/reset_stats
```

**Example:**
```
/reset_stats
```

This will reset all usage statistics.

**Output:**
The command will display a message confirming that the statistics have been reset.

## Tracked Statistics

The analytics system tracks the following statistics:

### Command Usage

- Command name
- User ID
- Guild ID
- Channel ID
- Timestamp
- Execution time
- Success/failure

### Image Generation

- User ID
- Prompt
- Resolution
- LoRAs used
- Upscale factor
- Generation time
- Is video
- Generation type (standard, redux, pulid, etc.)
- Timestamp

### User Activity

- User ID
- Guild ID
- Action type
- Timestamp
- Details

## Resetting Analytics

To reset all analytics data, use the `/reset_stats` command. This will delete all tracked statistics and start fresh.

## Implementation Details

The analytics system is implemented in the following files:

- `src/application/analytics/analytics_service.py`: Service for tracking and analyzing application usage
- `src/domain/interfaces/analytics_repository.py`: Interface for analytics data access
- `src/presentation/discord/commands/analytics_commands.py`: Discord commands for analytics

The analytics data is stored in a SQLite database in the following tables:

- `command_usage`: Tracks command usage
- `image_stats`: Tracks image generation
- `user_activity`: Tracks user activity
- `daily_stats`: Summarizes daily statistics

 
 [🏠  Return to main](../readme.md)

