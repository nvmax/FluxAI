"""
Service for filtering inappropriate content.
"""

import re
import logging
import json
import os
import time
from typing import Dict, Any, List, Optional, Tuple, Set

from src.domain.events.event_bus import EventBus
from src.domain.events.common_events import ContentFilterViolationEvent
from src.infrastructure.database.database_service import DatabaseService
from src.application.content_filter.transformer_content_filter import TransformerContentFilter

logger = logging.getLogger(__name__)

class ContentFilterService:
    """
    Service for filtering inappropriate content.
    Handles checking prompts against banned words and patterns.
    Implements a warning system with a three-strike policy.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one content filter service exists"""
        if cls._instance is None:
            cls._instance = super(ContentFilterService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, database_service: DatabaseService):
        """
        Initialize the content filter service.

        Args:
            database_service: Service for database access
        """
        # Only initialize once (singleton pattern)
        if self._initialized:
            return

        self.database_service = database_service
        self.event_bus = EventBus()
        self.banned_words: Set[str] = set()
        self.regex_patterns: List[Dict[str, Any]] = []
        self.context_rules: List[Dict[str, Any]] = []

        # Load warning and ban settings from environment variables
        self.max_warnings = int(os.getenv('MAX_WARNINGS', '3'))
        self.enable_permanent_ban = os.getenv('ENABLE_PERMANENT_BAN', 'true').lower() == 'true'

        # Initialize database tables
        self._init_database_tables()

        # Define the paths to the backup JSON files
        self.banned_words_backup_path = os.path.join('src', 'application', 'content_filter', 'banned_words.json')
        self.context_rules_backup_path = os.path.join('src', 'application', 'content_filter', 'context_rules.json')

        # Ensure the content_filter directory exists
        os.makedirs(os.path.dirname(self.banned_words_backup_path), exist_ok=True)

        # Initialize the transformer-based content filter
        logger.info("Initializing transformer-based content filter (will download model if needed)...")
        self.transformer_filter = TransformerContentFilter()
        logger.info("Transformer-based content filter initialized successfully")

        self._initialized = True

        # Load banned words and patterns
        self._load_banned_words()
        self._load_regex_patterns()
        self._load_context_rules()

    def _init_database_tables(self):
        """Initialize the database tables for content filtering"""
        try:
            logger.info("Initializing content filter database tables...")

            # Create banned words table
            self.database_service.create_table(
                "banned_words",
                {
                    "word": "TEXT PRIMARY KEY",
                    "added_at": "REAL NOT NULL"
                }
            )
            logger.info("Created banned_words table")

            # Create regex patterns table
            self.database_service.create_table(
                "regex_patterns",
                {
                    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                    "name": "TEXT NOT NULL",
                    "pattern": "TEXT NOT NULL",
                    "description": "TEXT",
                    "severity": "TEXT NOT NULL",
                    "added_at": "REAL NOT NULL"
                }
            )
            logger.info("Created regex_patterns table")

            # Create context rules table
            self.database_service.create_table(
                "context_rules",
                {
                    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                    "trigger_word": "TEXT NOT NULL",
                    "allowed_contexts": "TEXT",
                    "disallowed_contexts": "TEXT",
                    "description": "TEXT",
                    "added_at": "REAL NOT NULL"
                }
            )
            logger.info("Created context_rules table")

            # Create filter violations table
            self.database_service.create_table(
                "filter_violations",
                {
                    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                    "user_id": "TEXT NOT NULL",
                    "prompt": "TEXT NOT NULL",
                    "violation_type": "TEXT NOT NULL",
                    "violation_details": "TEXT",
                    "timestamp": "REAL NOT NULL"
                }
            )
            logger.info("Created filter_violations table")

            # Create user warnings table
            self.database_service.create_table(
                "user_warnings",
                {
                    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                    "user_id": "TEXT NOT NULL",
                    "prompt": "TEXT NOT NULL",
                    "word": "TEXT NOT NULL",
                    "warned_at": "REAL NOT NULL"
                }
            )
            logger.info("Created user_warnings table")

            # Create banned users table
            self.database_service.create_table(
                "banned_users",
                {
                    "user_id": "TEXT PRIMARY KEY",
                    "reason": "TEXT NOT NULL",
                    "banned_at": "REAL NOT NULL",
                    "is_permanent": "INTEGER DEFAULT 1",  # 1 = true, 0 = false
                    "expires_at": "REAL DEFAULT NULL"  # NULL for permanent bans
                }
            )
            logger.info("Created banned_users table")

            logger.info("Content filter database tables initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing content filter database tables: {e}")

    def _load_banned_words(self):
        """Load banned words from the database and backup file"""
        try:
            # First try to load from database
            try:
                rows = self.database_service.fetch_all("SELECT word FROM banned_words")
                self.banned_words = {row[0].lower() for row in rows}
                logger.info(f"Loaded {len(self.banned_words)} banned words from database")
            except Exception as e:
                logger.error(f"Error loading banned words from database: {e}")
                self.banned_words = set()

            # Then try to load from backup file
            if os.path.exists(self.banned_words_backup_path):
                try:
                    with open(self.banned_words_backup_path, 'r') as f:
                        backup_words = json.load(f)
                        backup_set = {word.lower() for word in backup_words}
                        logger.info(f"Loaded {len(backup_set)} banned words from backup file")

                        # If database was empty but backup has words, restore from backup
                        if not self.banned_words and backup_set:
                            logger.info("Database empty but backup exists - restoring from backup")
                            for word in backup_set:
                                try:
                                    self.database_service.insert(
                                        "banned_words",
                                        {
                                            "word": word,
                                            "added_at": time.time()
                                        }
                                    )
                                except Exception as e:
                                    logger.warning(f"Could not restore word '{word}' to database: {e}")

                            # Reload from database
                            rows = self.database_service.fetch_all("SELECT word FROM banned_words")
                            self.banned_words = {row[0].lower() for row in rows}
                            logger.info(f"Restored {len(self.banned_words)} banned words from backup to database")

                        # If database has words but they differ from backup, update backup
                        elif self.banned_words != backup_set:
                            logger.info("Database and backup differ - updating backup file")
                            self._save_banned_words_to_json()
                except Exception as e:
                    logger.error(f"Error loading banned words from backup file: {e}")
            else:
                # If backup file doesn't exist but we have words in the database, create backup
                if self.banned_words:
                    logger.info("Backup file doesn't exist - creating from database")
                    self._save_banned_words_to_json()

            logger.info(f"Final banned words count: {len(self.banned_words)}")
        except Exception as e:
            logger.error(f"Error in _load_banned_words: {e}")
            self.banned_words = set()

    def _load_regex_patterns(self):
        """Load regex patterns from the database"""
        try:
            rows = self.database_service.fetch_all(
                "SELECT id, name, pattern, description, severity FROM regex_patterns"
            )
            self.regex_patterns = [
                {
                    "id": row[0],
                    "name": row[1],
                    "pattern": row[2],
                    "description": row[3],
                    "severity": row[4],
                    "compiled": re.compile(row[2], re.IGNORECASE)
                }
                for row in rows
            ]
            logger.info(f"Loaded {len(self.regex_patterns)} regex patterns")
        except Exception as e:
            logger.error(f"Error loading regex patterns: {e}")
            self.regex_patterns = []

    def _load_context_rules(self):
        """Load context rules from the database or backup JSON file"""
        try:
            # First try to load from database
            rows = self.database_service.fetch_all(
                "SELECT id, trigger_word, allowed_contexts, disallowed_contexts, description FROM context_rules"
            )
            self.context_rules = [
                {
                    "id": row[0],
                    "trigger_word": row[1],
                    "allowed_contexts": json.loads(row[2]) if row[2] else [],
                    "disallowed_contexts": json.loads(row[3]) if row[3] else [],
                    "description": row[4]
                }
                for row in rows
            ]

            if self.context_rules:
                logger.info(f"Loaded {len(self.context_rules)} context rules from database")
                # Save to JSON as backup
                self._save_context_rules_to_json()
                return
            else:
                logger.warning("No context rules found in database, trying backup file")
        except Exception as e:
            logger.error(f"Error loading context rules from database: {e}")

        # If we get here, either there was an error or no rules in the database
        # Try to load from backup JSON file
        try:
            if os.path.exists(self.context_rules_backup_path):
                with open(self.context_rules_backup_path, 'r') as f:
                    json_rules = json.load(f)

                # Convert JSON rules to our format
                self.context_rules = []
                for rule in json_rules:
                    # Add to in-memory list
                    self.context_rules.append({
                        "id": None,  # No ID since it's from JSON
                        "trigger_word": rule["trigger_word"],
                        "allowed_contexts": rule["allowed_contexts"],
                        "disallowed_contexts": rule["disallowed_contexts"],
                        "description": rule.get("description", "")
                    })

                logger.info(f"Loaded {len(self.context_rules)} context rules from backup file")

                # Save to database
                self._sync_context_rules_to_database()
            else:
                logger.warning(f"Backup file not found: {self.context_rules_backup_path}")
                self.context_rules = []
        except Exception as e:
            logger.error(f"Error loading context rules from backup file: {e}")
            self.context_rules = []

    def _save_banned_words_to_json(self):
        """Save banned words to a backup JSON file"""
        try:
            # Sort the words for consistency
            sorted_words = sorted(list(self.banned_words))

            # Save to JSON file
            with open(self.banned_words_backup_path, 'w') as f:
                json.dump(sorted_words, f, indent=4)

            logger.info(f"Saved {len(sorted_words)} banned words to backup file: {self.banned_words_backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving banned words to backup file: {e}")
            return False

    def _save_context_rules_to_json(self):
        """Save context rules to a backup JSON file"""
        try:
            # Convert context rules to a format suitable for JSON
            json_rules = [
                {
                    "trigger_word": rule["trigger_word"],
                    "allowed_contexts": rule["allowed_contexts"],
                    "disallowed_contexts": rule["disallowed_contexts"],
                    "description": rule["description"]
                }
                for rule in self.context_rules
            ]

            # Save to JSON file
            with open(self.context_rules_backup_path, 'w') as f:
                json.dump(json_rules, f, indent=4)

            logger.info(f"Saved {len(json_rules)} context rules to backup file: {self.context_rules_backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving context rules to backup file: {e}")
            return False

    def _sync_context_rules_to_database(self):
        """Sync context rules from memory to the database"""
        try:
            # First, clear existing rules
            self.database_service.execute("DELETE FROM context_rules")
            logger.info("Cleared existing context rules from database")

            # Then insert all rules from memory
            for rule in self.context_rules:
                # Skip rules that already have an ID (they're already in the database)
                if rule.get("id") is not None:
                    continue

                # Insert into database
                rule_id = self.database_service.insert(
                    "context_rules",
                    {
                        "trigger_word": rule["trigger_word"],
                        "allowed_contexts": json.dumps(rule["allowed_contexts"]),
                        "disallowed_contexts": json.dumps(rule["disallowed_contexts"]),
                        "description": rule["description"],
                        "added_at": time.time()
                    }
                )

                # Update the rule with the new ID
                rule["id"] = rule_id

            logger.info(f"Synced {len(self.context_rules)} context rules to database")
            return True
        except Exception as e:
            logger.error(f"Error syncing context rules to database: {e}")
            return False

    def reload_filters(self):
        """Reload all filters from the database"""
        self._load_banned_words()
        self._load_regex_patterns()
        self._load_context_rules()

    def check_prompt(self, user_id: str, prompt: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check a prompt against the content filters.
        Implements a three-strike warning system.

        Args:
            user_id: ID of the user who submitted the prompt
            prompt: Prompt to check

        Returns:
            Tuple of (is_allowed, violation_type, violation_details)
        """
        # First check if the user is already banned
        if self.is_user_banned(user_id):
            return False, "banned_user", "You are banned from using this service. Please contact an administrator."

        # Check with transformer-based content filter first
        try:
            # First check for child-related inappropriate content
            is_safe, reason, confidence, threshold_name = self.transformer_filter.check_prompt_for_child_content(prompt)

            if not is_safe:
                # Record violation with threshold information
                self._record_violation(
                    user_id,
                    prompt,
                    "ai_content_filter",
                    f"AI detected inappropriate content: {reason} (confidence: {confidence:.2f}, threshold: {threshold_name})"
                )

                # Get current warning count
                warning_count = self.get_warning_count(user_id)

                # Add a warning
                self.add_user_warning(user_id, prompt, f"ai_filter:{reason}")

                # Check if max warnings reached
                if warning_count >= self.max_warnings - 1:  # Max warnings reached (0-indexed)
                    if self.enable_permanent_ban:
                        # Permanently ban the user
                        self.ban_user(user_id, f"AI detected inappropriate content after {self.max_warnings-1} warnings: {reason}")
                        return False, "ai_content_filter", f"🚫 You have been permanently banned for submitting potentially inappropriate content.\nThis was your {warning_count+1}th violation out of {self.max_warnings} allowed. Please contact an administrator if you believe this is an error.\nThreshold that was exceeded: {threshold_name}={confidence:.2f}"
                    else:
                        # Temporarily restrict the user
                        self.temp_restrict_user(user_id, f"AI detected inappropriate content after {self.max_warnings-1} warnings: {reason}")
                        return False, "ai_content_filter", f"🚫 You have been temporarily restricted for 24 hours for submitting potentially inappropriate content.\nThis was your {warning_count+1}th violation out of {self.max_warnings} allowed. Your warnings will be reset after 24 hours.\nThreshold that was exceeded: {threshold_name}={confidence:.2f}"
                elif warning_count == self.max_warnings - 2:  # One warning away from max
                    return False, "ai_content_filter", f"⚠️ FINAL WARNING: Your prompt may generate inappropriate content.\nThis is warning {warning_count+1} of {self.max_warnings}. One more violation will result in {'a permanent ban' if self.enable_permanent_ban else 'a 24-hour restriction'}.\nThreshold that was exceeded: {threshold_name}={confidence:.2f}"
                else:  # Earlier warnings
                    warnings_remaining = self.max_warnings - warning_count - 1
                    return False, "ai_content_filter", f"⚠️ WARNING: Your prompt may generate inappropriate content.\nThis is warning {warning_count+1} of {self.max_warnings}. You have {warnings_remaining} {'warning' if warnings_remaining == 1 else 'warnings'} remaining before {'a permanent ban' if self.enable_permanent_ban else 'a 24-hour restriction'}.\nThreshold that was exceeded: {threshold_name}={confidence:.2f}"

            # Then do a general content safety check
            is_safe, scores, violation_type, violation_score, threshold_name = self.transformer_filter.check_content(prompt)

            if not is_safe:
                # Record violation with detailed information
                self._record_violation(
                    user_id,
                    prompt,
                    "ai_content_filter",
                    f"AI detected {violation_type} content (score: {violation_score:.2f}, threshold: {threshold_name})"
                )

                # Get current warning count
                warning_count = self.get_warning_count(user_id)

                # Add a warning
                self.add_user_warning(user_id, prompt, f"ai_filter:{violation_type}")

                # Check if max warnings reached
                if warning_count >= self.max_warnings - 1:  # Max warnings reached (0-indexed)
                    if self.enable_permanent_ban:
                        # Permanently ban the user
                        self.ban_user(user_id, f"AI detected {violation_type} content after {self.max_warnings-1} warnings")
                        return False, "ai_content_filter", f"🚫 You have been permanently banned for submitting potentially {violation_type} content.\nThis was your {warning_count+1}th violation out of {self.max_warnings} allowed. Please contact an administrator if you believe this is an error.\nThreshold that was exceeded: {threshold_name}={violation_score:.2f}"
                    else:
                        # Temporarily restrict the user
                        self.temp_restrict_user(user_id, f"AI detected {violation_type} content after {self.max_warnings-1} warnings")
                        return False, "ai_content_filter", f"🚫 You have been temporarily restricted for 24 hours for submitting potentially {violation_type} content.\nThis was your {warning_count+1}th violation out of {self.max_warnings} allowed. Your warnings will be reset after 24 hours.\nThreshold that was exceeded: {threshold_name}={violation_score:.2f}"
                elif warning_count == self.max_warnings - 2:  # One warning away from max
                    return False, "ai_content_filter", f"⚠️ FINAL WARNING: Your prompt may generate {violation_type} content.\nThis is warning {warning_count+1} of {self.max_warnings}. One more violation will result in {'a permanent ban' if self.enable_permanent_ban else 'a 24-hour restriction'}.\nThreshold that was exceeded: {threshold_name}={violation_score:.2f}"
                else:  # Earlier warnings
                    warnings_remaining = self.max_warnings - warning_count - 1
                    return False, "ai_content_filter", f"⚠️ WARNING: Your prompt may generate {violation_type} content.\nThis is warning {warning_count+1} of {self.max_warnings}. You have {warnings_remaining} {'warning' if warnings_remaining == 1 else 'warnings'} remaining before {'a permanent ban' if self.enable_permanent_ban else 'a 24-hour restriction'}.\nThreshold that was exceeded: {threshold_name}={violation_score:.2f}"
        except Exception as e:
            logger.error(f"Error using transformer content filter: {e}")
            # Continue with rule-based checks if transformer filter fails

        prompt_lower = prompt.lower()

        # First check context rules to allow for exceptions
        # For example, "young adult" should be allowed even though "young" is a banned word
        for rule in self.context_rules:
            trigger_word = rule["trigger_word"].lower()

            # Skip if the trigger word is not in the prompt
            if trigger_word not in prompt_lower:
                continue

            # Check if any allowed context is present
            allowed_found = False
            for context in rule["allowed_contexts"]:
                if context.lower() in prompt_lower:
                    allowed_found = True
                    break

            # If an allowed context is found, we can skip checking disallowed contexts
            # for this trigger word
            if allowed_found:
                continue

            # Check if any disallowed context is present
            for context in rule["disallowed_contexts"]:
                if context.lower() in prompt_lower:
                    # Record violation
                    self._record_violation(
                        user_id,
                        prompt,
                        "context_rule",
                        f"{rule['trigger_word']} with disallowed context: {context}"
                    )

                    # Get current warning count
                    warning_count = self.get_warning_count(user_id)

                    # Add a warning
                    self.add_user_warning(user_id, prompt, f"context:{rule['trigger_word']}")

                    # Check if this is the third strike
                    if warning_count >= 2:  # This is the third warning (0-indexed)
                        # Ban the user
                        self.ban_user(user_id, f"Context violation after two warnings: {rule['trigger_word']} with {context}")
                        return False, "context_rule", f"🚫 You have been banned for using '{rule['trigger_word']}' with disallowed context '{context}'.\nThis was your third violation. Please contact an administrator if you believe this is an error."
                    elif warning_count == 1:  # Second warning
                        return False, "context_rule", f"⚠️ FINAL WARNING: Your prompt contains '{rule['trigger_word']}' with disallowed context '{context}'.\nThis is your second warning. One more violation will result in a permanent ban."
                    else:  # First warning
                        return False, "context_rule", f"⚠️ WARNING: Your prompt contains '{rule['trigger_word']}' with disallowed context '{context}'.\nThis is your first warning. You have one more warning remaining before a permanent ban."

            # If allowed contexts are specified and none were found, it's a violation
            if rule["allowed_contexts"] and not allowed_found:
                # Record violation
                self._record_violation(
                    user_id,
                    prompt,
                    "context_rule",
                    f"{rule['trigger_word']} without allowed context"
                )

                # Get current warning count
                warning_count = self.get_warning_count(user_id)

                # Add a warning
                self.add_user_warning(user_id, prompt, f"context:{rule['trigger_word']}")

                # Check if this is the third strike
                if warning_count >= 2:  # This is the third warning (0-indexed)
                    # Ban the user
                    self.ban_user(user_id, f"Context violation after two warnings: {rule['trigger_word']} without allowed context")
                    return False, "context_rule", f"🚫 You have been banned for using '{rule['trigger_word']}' without proper context.\nThis was your third violation. Please contact an administrator if you believe this is an error."
                elif warning_count == 1:  # Second warning
                    return False, "context_rule", f"⚠️ FINAL WARNING: Your prompt contains '{rule['trigger_word']}' without proper context.\nThis is your second warning. One more violation will result in a permanent ban."
                else:  # First warning
                    return False, "context_rule", f"⚠️ WARNING: Your prompt contains '{rule['trigger_word']}' without proper context.\nThis is your first warning. You have one more warning remaining before a permanent ban."

        # Now check banned words
        # Skip banned words that are part of allowed contexts in context rules
        for word in self.banned_words:
            if word in prompt_lower:
                # Check if this word is part of an allowed context
                skip_word = False
                for rule in self.context_rules:
                    if rule["trigger_word"].lower() == word:
                        for allowed_context in rule["allowed_contexts"]:
                            if allowed_context.lower() in prompt_lower:
                                skip_word = True
                                break
                    if skip_word:
                        break

                if skip_word:
                    continue

                # Record violation
                self._record_violation(user_id, prompt, "banned_word", word)

                # Get current warning count
                warning_count = self.get_warning_count(user_id)

                # Add a warning
                self.add_user_warning(user_id, prompt, f"banned_word:{word}")

                # Check if this is the third strike
                if warning_count >= 2:  # This is the third warning (0-indexed)
                    # Ban the user
                    self.ban_user(user_id, f"Used banned word after two warnings: {word}")
                    return False, "banned_word", f"🚫 You have been banned for using the banned word '{word}'.\nThis was your third violation. Please contact an administrator if you believe this is an error."
                elif warning_count == 1:  # Second warning
                    return False, "banned_word", f"⚠️ FINAL WARNING: Your prompt contains the banned word '{word}'.\nThis is your second warning. One more violation will result in a permanent ban."
                else:  # First warning
                    return False, "banned_word", f"⚠️ WARNING: Your prompt contains the banned word '{word}'.\nThis is your first warning. You have one more warning remaining before a permanent ban."

        # Check regex patterns
        for pattern in self.regex_patterns:
            match = pattern["compiled"].search(prompt)
            if match:
                # Record violation
                self._record_violation(
                    user_id,
                    prompt,
                    "regex_pattern",
                    f"{pattern['name']}: {match.group(0)}"
                )

                # Get current warning count
                warning_count = self.get_warning_count(user_id)

                # Add a warning
                self.add_user_warning(user_id, prompt, f"regex:{pattern['name']}")

                # Check if this is the third strike
                if warning_count >= 2:  # This is the third warning (0-indexed)
                    # Ban the user
                    self.ban_user(user_id, f"Violated regex pattern after two warnings: {pattern['name']}")
                    return False, "regex_pattern", f"🚫 You have been banned for violating content policy with '{match.group(0)}'.\nThis was your third violation. Please contact an administrator if you believe this is an error."
                elif warning_count == 1:  # Second warning
                    return False, "regex_pattern", f"⚠️ FINAL WARNING: Your prompt contains prohibited content: '{match.group(0)}'.\nThis is your second warning. One more violation will result in a permanent ban."
                else:  # First warning
                    return False, "regex_pattern", f"⚠️ WARNING: Your prompt contains prohibited content: '{match.group(0)}'.\nThis is your first warning. You have one more warning remaining before a permanent ban."

        # Context rules are now checked at the beginning of the method

        # All checks passed
        return True, None, None

    def _record_violation(self, user_id: str, prompt: str, violation_type: str, violation_details: str):
        """
        Record a content filter violation.

        Args:
            user_id: ID of the user who submitted the prompt
            prompt: Prompt that violated the filter
            violation_type: Type of violation
            violation_details: Details of the violation
        """
        try:
            # Insert into database
            self.database_service.insert(
                "filter_violations",
                {
                    "user_id": user_id,
                    "prompt": prompt,
                    "violation_type": violation_type,
                    "violation_details": violation_details,
                    "timestamp": time.time()
                }
            )

            # Publish event
            self.event_bus.publish(ContentFilterViolationEvent(
                user_id=user_id,
                prompt=prompt,
                violation_type=violation_type,
                violation_details=violation_details
            ))

            logger.info(f"Recorded content filter violation: {violation_type} - {violation_details}")
        except Exception as e:
            logger.error(f"Error recording content filter violation: {e}")

    def add_banned_word(self, word: str) -> bool:
        """
        Add a banned word to the filter.

        Args:
            word: Word to ban

        Returns:
            True if successful, False otherwise
        """
        try:
            word = word.lower().strip()

            # Check if word is already banned
            if word in self.banned_words:
                return True

            # Add to database
            self.database_service.insert(
                "banned_words",
                {
                    "word": word,
                    "added_at": time.time()
                }
            )

            # Add to in-memory set
            self.banned_words.add(word)

            # Update the backup JSON file
            self._save_banned_words_to_json()

            logger.info(f"Added banned word: {word}")
            return True
        except Exception as e:
            logger.error(f"Error adding banned word: {e}")
            return False

    def remove_banned_word(self, word: str) -> bool:
        """
        Remove a banned word from the filter.

        Args:
            word: Word to unban

        Returns:
            True if successful, False otherwise
        """
        try:
            word = word.lower().strip()

            # Remove from database
            self.database_service.delete(
                "banned_words",
                "word = ?",
                (word,)
            )

            # Remove from in-memory set
            if word in self.banned_words:
                self.banned_words.remove(word)

            # Update the backup JSON file
            self._save_banned_words_to_json()

            logger.info(f"Removed banned word: {word}")
            return True
        except Exception as e:
            logger.error(f"Error removing banned word: {e}")
            return False

    def add_regex_pattern(self, name: str, pattern: str, description: str, severity: str) -> bool:
        """
        Add a regex pattern to the filter.

        Args:
            name: Name of the pattern
            pattern: Regex pattern
            description: Description of the pattern
            severity: Severity level (high, medium, low)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate pattern
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
            except Exception as e:
                logger.error(f"Invalid regex pattern: {e}")
                return False

            # Add to database
            pattern_id = self.database_service.insert(
                "regex_patterns",
                {
                    "name": name,
                    "pattern": pattern,
                    "description": description,
                    "severity": severity,
                    "added_at": time.time()
                }
            )

            # Add to in-memory list
            self.regex_patterns.append({
                "id": pattern_id,
                "name": name,
                "pattern": pattern,
                "description": description,
                "severity": severity,
                "compiled": compiled
            })

            logger.info(f"Added regex pattern: {name}")
            return True
        except Exception as e:
            logger.error(f"Error adding regex pattern: {e}")
            return False

    def remove_regex_pattern(self, pattern_id: int) -> bool:
        """
        Remove a regex pattern from the filter.

        Args:
            pattern_id: ID of the pattern to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove from database
            self.database_service.delete(
                "regex_patterns",
                "id = ?",
                (pattern_id,)
            )

            # Remove from in-memory list
            self.regex_patterns = [p for p in self.regex_patterns if p["id"] != pattern_id]

            logger.info(f"Removed regex pattern: {pattern_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing regex pattern: {e}")
            return False

    def get_banned_words(self) -> List[str]:
        """
        Get all banned words.

        Returns:
            List of banned words
        """
        return sorted(list(self.banned_words))

    def get_regex_patterns(self) -> List[Dict[str, Any]]:
        """
        Get all regex patterns.

        Returns:
            List of regex patterns
        """
        return [
            {
                "id": p["id"],
                "name": p["name"],
                "pattern": p["pattern"],
                "description": p["description"],
                "severity": p["severity"]
            }
            for p in self.regex_patterns
        ]

    def get_context_rules(self) -> List[Dict[str, Any]]:
        """
        Get all context rules.

        Returns:
            List of context rules
        """
        return self.context_rules

    def add_context_rule(self, trigger_word: str, allowed_contexts: List[str] = None,
                        disallowed_contexts: List[str] = None, description: str = "") -> bool:
        """
        Add a context rule to the filter.

        Args:
            trigger_word: The word that triggers the rule
            allowed_contexts: List of allowed contexts for the trigger word
            disallowed_contexts: List of disallowed contexts for the trigger word
            description: Description of the rule

        Returns:
            True if successful, False otherwise
        """
        try:
            if not trigger_word:
                return False

            if not allowed_contexts and not disallowed_contexts:
                return False

            # Check if rule already exists
            for rule in self.context_rules:
                if rule["trigger_word"].lower() == trigger_word.lower():
                    # Update existing rule
                    rule["allowed_contexts"] = allowed_contexts or []
                    rule["disallowed_contexts"] = disallowed_contexts or []
                    rule["description"] = description

                    # Update database
                    if rule.get("id") is not None:
                        self.database_service.update(
                            "context_rules",
                            {
                                "allowed_contexts": json.dumps(allowed_contexts or []),
                                "disallowed_contexts": json.dumps(disallowed_contexts or []),
                                "description": description
                            },
                            "id = ?",
                            (rule["id"],)
                        )
                    else:
                        # Insert new rule
                        rule_id = self.database_service.insert(
                            "context_rules",
                            {
                                "trigger_word": trigger_word,
                                "allowed_contexts": json.dumps(allowed_contexts or []),
                                "disallowed_contexts": json.dumps(disallowed_contexts or []),
                                "description": description,
                                "added_at": time.time()
                            }
                        )
                        rule["id"] = rule_id

                    # Save to JSON backup
                    self._save_context_rules_to_json()

                    logger.info(f"Updated context rule for '{trigger_word}'")
                    return True

            # Add new rule
            rule_id = self.database_service.insert(
                "context_rules",
                {
                    "trigger_word": trigger_word,
                    "allowed_contexts": json.dumps(allowed_contexts or []),
                    "disallowed_contexts": json.dumps(disallowed_contexts or []),
                    "description": description,
                    "added_at": time.time()
                }
            )

            # Add to in-memory list
            self.context_rules.append({
                "id": rule_id,
                "trigger_word": trigger_word,
                "allowed_contexts": allowed_contexts or [],
                "disallowed_contexts": disallowed_contexts or [],
                "description": description
            })

            # Save to JSON backup
            self._save_context_rules_to_json()

            logger.info(f"Added context rule for '{trigger_word}'")
            return True

        except Exception as e:
            logger.error(f"Error adding context rule: {e}")
            return False

    def remove_context_rule(self, trigger_word: str) -> bool:
        """
        Remove a context rule from the filter.

        Args:
            trigger_word: The trigger word of the rule to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            # Find the rule
            for i, rule in enumerate(self.context_rules):
                if rule["trigger_word"].lower() == trigger_word.lower():
                    # Remove from database if it has an ID
                    if rule.get("id") is not None:
                        self.database_service.delete(
                            "context_rules",
                            "id = ?",
                            (rule["id"],)
                        )

                    # Remove from in-memory list
                    del self.context_rules[i]

                    # Save to JSON backup
                    self._save_context_rules_to_json()

                    logger.info(f"Removed context rule for '{trigger_word}'")
                    return True

            logger.warning(f"Context rule for '{trigger_word}' not found")
            return False

        except Exception as e:
            logger.error(f"Error removing context rule: {e}")
            return False

    def add_user_warning(self, user_id: str, prompt: str, violation_details: str) -> bool:
        """
        Add a warning for a user.

        Args:
            user_id: ID of the user to warn
            prompt: Prompt that triggered the warning
            violation_details: Details of the violation

        Returns:
            True if successful, False otherwise
        """
        try:
            # Insert into database
            self.database_service.insert(
                "user_warnings",
                {
                    "user_id": user_id,
                    "prompt": prompt,
                    "word": violation_details,
                    "warned_at": time.time()
                }
            )

            logger.info(f"Added warning for user {user_id}: {violation_details}")
            return True
        except Exception as e:
            logger.error(f"Error adding user warning: {e}")
            return False

    def get_user_warnings(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all warnings for a user.

        Args:
            user_id: ID of the user

        Returns:
            List of warnings
        """
        try:
            rows = self.database_service.fetch_all(
                "SELECT id, prompt, word, warned_at FROM user_warnings WHERE user_id = ? ORDER BY warned_at DESC",
                (user_id,)
            )

            warnings = [
                {
                    "id": row[0],
                    "prompt": row[1],
                    "violation": row[2],
                    "warned_at": row[3]
                }
                for row in rows
            ]

            return warnings
        except Exception as e:
            logger.error(f"Error getting user warnings: {e}")
            return []

    def get_warning_count(self, user_id: str) -> int:
        """
        Get the number of warnings for a user.

        Args:
            user_id: ID of the user

        Returns:
            Number of warnings
        """
        try:
            result = self.database_service.fetch_one(
                "SELECT COUNT(*) FROM user_warnings WHERE user_id = ?",
                (user_id,)
            )

            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting warning count: {e}")
            return 0

    def remove_user_warning(self, warning_id: int) -> bool:
        """
        Remove a warning.

        Args:
            warning_id: ID of the warning to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            self.database_service.delete(
                "user_warnings",
                "id = ?",
                (warning_id,)
            )

            logger.info(f"Removed warning {warning_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing warning: {e}")
            return False

    def remove_all_user_warnings(self, user_id: str) -> bool:
        """
        Remove all warnings for a user.

        Args:
            user_id: ID of the user

        Returns:
            True if successful, False otherwise
        """
        try:
            self.database_service.delete(
                "user_warnings",
                "user_id = ?",
                (user_id,)
            )

            logger.info(f"Removed all warnings for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing user warnings: {e}")
            return False

    def ban_user(self, user_id: str, reason: str) -> bool:
        """
        Permanently ban a user.

        Args:
            user_id: ID of the user to ban
            reason: Reason for the ban

        Returns:
            True if successful, False otherwise
        """
        try:
            # Insert into database with permanent flag
            self.database_service.insert(
                "banned_users",
                {
                    "user_id": user_id,
                    "reason": reason,
                    "banned_at": time.time(),
                    "is_permanent": True,
                    "expires_at": None
                }
            )

            logger.info(f"Permanently banned user {user_id}: {reason}")
            return True
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            return False

    def temp_restrict_user(self, user_id: str, reason: str) -> bool:
        """
        Temporarily restrict a user for 24 hours and reset their warnings after the period.

        Args:
            user_id: ID of the user to restrict
            reason: Reason for the restriction

        Returns:
            True if successful, False otherwise
        """
        try:
            # Calculate expiration time (24 hours from now)
            expires_at = time.time() + (24 * 60 * 60)  # 24 hours in seconds

            # Insert into database with temporary flag and expiration
            self.database_service.insert(
                "banned_users",
                {
                    "user_id": user_id,
                    "reason": reason,
                    "banned_at": time.time(),
                    "is_permanent": False,
                    "expires_at": expires_at
                }
            )

            logger.info(f"Temporarily restricted user {user_id} for 24 hours: {reason}")
            return True
        except Exception as e:
            logger.error(f"Error restricting user: {e}")
            return False

    def unban_user(self, user_id: str) -> bool:
        """
        Unban a user.

        Args:
            user_id: ID of the user to unban

        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove from database
            self.database_service.delete(
                "banned_users",
                "user_id = ?",
                (user_id,)
            )

            logger.info(f"Unbanned user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error unbanning user: {e}")
            return False

    def is_user_banned(self, user_id: str) -> bool:
        """
        Check if a user is banned or temporarily restricted.
        Automatically removes expired temporary restrictions and resets warnings.

        Args:
            user_id: ID of the user

        Returns:
            True if the user is banned or restricted, False otherwise
        """
        try:
            # Get ban info including expiration details
            result = self.database_service.fetch_one(
                "SELECT is_permanent, expires_at FROM banned_users WHERE user_id = ?",
                (user_id,)
            )

            if result is None:
                return False

            is_permanent, expires_at = result

            # If it's a permanent ban, user is banned
            if is_permanent:
                return True

            # If it's a temporary restriction, check if it's expired
            current_time = time.time()
            if expires_at and current_time > expires_at:
                # Restriction has expired, remove it and reset warnings
                self.unban_user(user_id)
                self.remove_all_warnings(user_id)
                logger.info(f"Temporary restriction for user {user_id} has expired. Warnings reset.")
                return False
            else:
                # Restriction is still active
                return True
        except Exception as e:
            logger.error(f"Error checking if user is banned: {e}")
            return False

    def get_ban_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get ban information for a user.

        Args:
            user_id: ID of the user

        Returns:
            Ban information or None if the user is not banned
        """
        try:
            result = self.database_service.fetch_one(
                "SELECT reason, banned_at, is_permanent, expires_at FROM banned_users WHERE user_id = ?",
                (user_id,)
            )

            if result:
                reason, banned_at, is_permanent, expires_at = result
                return {
                    "reason": reason,
                    "banned_at": banned_at,
                    "is_permanent": bool(is_permanent),
                    "expires_at": expires_at,
                    "time_remaining": expires_at - time.time() if expires_at and not is_permanent else None
                }
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting ban info: {e}")
            return None

    def get_all_banned_users(self) -> List[Dict[str, Any]]:
        """
        Get all banned users.

        Returns:
            List of banned users
        """
        try:
            rows = self.database_service.fetch_all(
                "SELECT user_id, reason, banned_at, is_permanent, expires_at FROM banned_users ORDER BY banned_at DESC"
            )

            current_time = time.time()
            banned_users = [
                {
                    "user_id": row[0],
                    "reason": row[1],
                    "banned_at": row[2],
                    "is_permanent": bool(row[3]),
                    "expires_at": row[4],
                    "time_remaining": row[4] - current_time if row[4] and not row[3] else None,
                    "status": "Permanent Ban" if row[3] else ("Active Restriction" if row[4] > current_time else "Expired Restriction")
                }
                for row in rows
            ]

            return banned_users
        except Exception as e:
            logger.error(f"Error getting banned users: {e}")
            return []

    def get_all_warnings(self) -> List[Dict[str, Any]]:
        """
        Get all warnings.

        Returns:
            List of warnings
        """
        try:
            rows = self.database_service.fetch_all(
                "SELECT id, user_id, prompt, word, warned_at FROM user_warnings ORDER BY warned_at DESC"
            )

            warnings = [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "prompt": row[2],
                    "violation": row[3],
                    "warned_at": row[4]
                }
                for row in rows
            ]

            return warnings
        except Exception as e:
            logger.error(f"Error getting all warnings: {e}")
            return []

    def remove_all_warnings(self, user_id: str) -> bool:
        """
        Remove all warnings for a user.

        Args:
            user_id: ID of the user

        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete all warnings for the user
            self.database_service.execute(
                "DELETE FROM user_warnings WHERE user_id = ?",
                (user_id,)
            )

            logger.info(f"Removed all warnings for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing warnings: {e}")
            return False
