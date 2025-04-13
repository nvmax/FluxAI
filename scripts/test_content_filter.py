"""
Script to test the content filter with the expanded context rules.
"""

import sys
import os
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.application.content_filter.content_filter_service import ContentFilterService
    from src.infrastructure.database.database_service import DatabaseService

    def test_content_filter():
        """Test the content filter with various prompts"""
        logger.info("Testing content filter with expanded context rules")

        # Initialize services
        db_service = DatabaseService()
        content_filter = ContentFilterService(db_service)

        # Get all context rules
        context_rules = content_filter.get_context_rules()
        logger.info(f"Loaded {len(context_rules)} context rules")

        # Print the first 5 rules as a sample
        logger.info("Sample of context rules:")
        for i, rule in enumerate(context_rules[:5]):
            logger.info(f"Rule {i+1}: {rule['trigger_word']} - {len(rule['allowed_contexts'])} allowed contexts, {len(rule['disallowed_contexts'])} disallowed contexts")

        # Test prompts that should be allowed
        allowed_prompts = [
            "A beautiful landscape with mountains and a lake",
            "A portrait of a young adult woman with long hair",
            "A professional photo of a young man in a business suit",
            "A small house in the countryside",
            "A cute animal in a garden",
            "An anime style landscape with cherry blossoms",
            "A cartoon character in a fantasy world"
        ]

        # Test prompts that should be blocked
        blocked_prompts = [
            "A young girl playing in a park",
            "A small child with a toy",
            "A school classroom with students",
            "A family with children at the beach",
            "A cute little boy playing with toys",
            "An anime girl in a school uniform",
            "A cartoon boy character"
        ]

        # First, unban any test users
        content_filter.unban_user("test_user_allowed")
        content_filter.unban_user("test_user_blocked")

        # Remove any warnings
        content_filter.remove_all_user_warnings("test_user_allowed")
        content_filter.remove_all_user_warnings("test_user_blocked")

        # Test allowed prompts
        logger.info("\nTesting prompts that should be allowed:")
        for prompt in allowed_prompts:
            is_allowed, violation_type, violation_details = content_filter.check_prompt("test_user_allowed", prompt)
            result = "ALLOWED" if is_allowed else f"BLOCKED: {violation_type} - {violation_details}"
            logger.info(f"Prompt: '{prompt}' -> {result}")

        # Test blocked prompts
        logger.info("\nTesting prompts that should be blocked:")
        for prompt in blocked_prompts:
            is_allowed, violation_type, violation_details = content_filter.check_prompt("test_user_blocked", prompt)
            result = "ALLOWED" if is_allowed else f"BLOCKED: {violation_type} - {violation_details}"
            logger.info(f"Prompt: '{prompt}' -> {result}")

        return 0

    if __name__ == "__main__":
        sys.exit(test_content_filter())

except Exception as e:
    logger.error(f"Error in test_content_filter: {e}")
    sys.exit(1)
