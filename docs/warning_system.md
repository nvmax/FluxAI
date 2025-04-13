# Content Filter Warning System

The content filter warning system implements a Multi strike policy for users who violate the content filtering rules. This document explains how the system works and the available commands for managing warnings and bans.

## How the Warning System Works

1. When a user submits a prompt that violates the content filtering rules (contains banned words, matches regex patterns, or violates context rules), they receive a warning.
2. After specified amount of warnings, the user is automatically restricted/banned from using the bot.
 - settings specified in setup tool
3. Warnings and bans are tracked in the database and persist across bot restarts.

### Warnings

- Users will recieve warnings each time depending on how many are specified when the bot is setup, it should give them a count down of how many warnings they have left until action is taken from being suspended for 24 hours or being banned altogether.

## Commands

### User Commands

- `/warnings` - Check your own warnings
  - Shows a list of your warnings, including the violation details and timestamps.

### Admin Commands

**Note:** The following commands can only be executed by users with the Administrator permission or users with the BOT_MANAGER_ROLE_ID role specified in the .env file.

- `/warnings [user]` - Check warnings for a specific user
  - Shows a list of warnings for the specified user, including the violation details and timestamps.

- `/warningremove [user]` - Remove all warnings from a user
  - Removes all warnings from the specified user, giving them a clean slate.

- `/banned` - List all banned users
  - Shows a list of all banned users, including the reason for the ban and the timestamp.

- `/ban [user] [reason]` - Ban a user from using the bot
  - Manually bans a user from using the bot with the specified reason.

- `/unban [user]` - Unban a user from using the bot
  - Unbans a user, allowing them to use the bot again.

## Content Filter Commands

- `/add_banned_word [word]` - Add a word to the banned words list
  - Adds a word to the list of banned words that trigger warnings.

- `/remove_banned_word [word]` - Remove a word from the banned words list
  - Removes a word from the list of banned words.

- `/list_banned_words` - List all banned words
  - Shows a list of all banned words.

- `/add_regex_pattern [name] [pattern] [description] [severity]` - Add a regex pattern to the content filter
  - Adds a regex pattern to the content filter with the specified name, pattern, description, and severity.

 - Example:

  Block inappropriate celebrity requests:
  ```
   /add_regex_pattern "celebrity_nsfw" "(?i)(naked|nude|explicit|nsfw)\\s+(celebrity|actor|actress|famous)" "Blocks inappropriate celebrity requests" "medium"`
   ```



## Database Tables

The warning system uses the following database tables:

### user_warnings

Stores warnings issued to users.

- `id` - Unique identifier for the warning
- `user_id` - Discord user ID
- `prompt` - The prompt that triggered the warning
- `word` - The violation details (banned word, regex pattern, or context rule)
- `warned_at` - Timestamp when the warning was issued

### banned_users

Stores banned users.

- `user_id` - Discord user ID (primary key)
- `reason` - Reason for the ban
- `banned_at` - Timestamp when the user was banned

### filter_violations

Stores all content filter violations, regardless of whether they resulted in a warning.

- `id` - Unique identifier for the violation
- `user_id` - Discord user ID
- `prompt` - The prompt that triggered the violation
- `violation_type` - Type of violation (banned_word, regex_pattern, or context_rule)
- `violation_details` - Details of the violation
- `timestamp` - Timestamp when the violation occurred
