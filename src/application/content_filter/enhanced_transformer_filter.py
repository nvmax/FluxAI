"""
Enhanced transformer-based content filter service that uses multiple specialized models for content moderation.
"""

import os
import logging
import time
from typing import Tuple, Dict, Any, Optional, List, Union
import torch
import re
from src.infrastructure.config.config_manager import ConfigManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedTransformerFilter:
    """
    Enhanced content filter service using multiple transformer models for context-aware content moderation.
    Uses specialized models for different types of content detection.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super(EnhancedTransformerFilter, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, primary_model_path: str = None, child_content_model_path: str = None, use_specialized_child_model: bool = None):
        """
        Initialize the enhanced transformer content filter service.

        Args:
            primary_model_path: Optional path to a pre-trained model for general toxicity detection.
                                If None, will use s-nlp/roberta_toxicity_classifier.
            child_content_model_path: Optional path to a pre-trained model for child-related content detection.
                                     If None, will use microsoft/mdeberta-v3-base or a fine-tuned model if available.
            use_specialized_child_model: Whether to use the specialized child content model.
                                        If None, will use the value from the environment variable CONTENT_FILTER_USE_CHILD_MODEL.
        """
        # Only initialize once (singleton pattern)
        if self._initialized:
            return

        # Load configuration
        self.config = ConfigManager()

        # Load thresholds from environment variables with defaults
        self.toxic_threshold = float(os.getenv('CONTENT_FILTER_TOXIC_THRESHOLD', '0.95'))
        self.harmful_threshold = float(os.getenv('CONTENT_FILTER_HARMFUL_THRESHOLD', '0.9'))
        # Set a very high threshold for sexual content to effectively allow it when adult content is allowed
        if os.getenv('CONTENT_FILTER_ALLOW_ADULT', 'true').lower() == 'true':
            self.sexual_threshold = float(os.getenv('CONTENT_FILTER_SEXUAL_THRESHOLD', '1.0'))
        else:
            self.sexual_threshold = float(os.getenv('CONTENT_FILTER_SEXUAL_THRESHOLD', '0.7'))
        # Keep a low threshold for child-related content
        self.child_content_threshold = float(os.getenv('CONTENT_FILTER_CHILD_THRESHOLD', '0.1'))
        self.hate_threshold = float(os.getenv('CONTENT_FILTER_HATE_THRESHOLD', '0.7'))
        self.violence_threshold = float(os.getenv('CONTENT_FILTER_VIOLENCE_THRESHOLD', '0.8'))

        # Flag to control whether adult content is allowed
        self.allow_adult_content = os.getenv('CONTENT_FILTER_ALLOW_ADULT', 'true').lower() == 'true'

        # Log the thresholds and settings
        logger.info(f"Content filter thresholds: toxic={self.toxic_threshold}, harmful={self.harmful_threshold}, "
                   f"sexual={self.sexual_threshold}, child={self.child_content_threshold}, "
                   f"hate={self.hate_threshold}, violence={self.violence_threshold}")
        logger.info(f"Allow adult content: {self.allow_adult_content}")

        # Initialize model variables
        self.primary_model = None
        self.primary_tokenizer = None
        self.primary_model_path = primary_model_path or "s-nlp/roberta_toxicity_classifier"
        self.primary_categories = []

        # Child content model - specialized for child-related content detection
        self.child_model = None
        self.child_tokenizer = None

        # Check for a fine-tuned model first, then fall back to a specialized pre-trained model
        fine_tuned_model_path = os.path.join('models', 'child_content_detector')
        if os.path.exists(fine_tuned_model_path):
            self.child_model_path = child_content_model_path or fine_tuned_model_path
            logger.info(f"Found fine-tuned child content model at {fine_tuned_model_path}")
        else:
            # Use a specialized model for child content detection
            # This model is better at detecting child-related inappropriate content
            self.child_model_path = child_content_model_path or "s-nlp/roberta_toxicity_classifier"
            logger.info(f"Using specialized model for child content detection: {self.child_model_path}")

        self.child_categories = []

        # Determine whether to use the specialized child model
        # This can be controlled via environment variable or constructor parameter
        if use_specialized_child_model is not None:
            self.use_specialized_child_model = use_specialized_child_model
        else:
            self.use_specialized_child_model = os.getenv('CONTENT_FILTER_USE_CHILD_MODEL', 'true').lower() == 'true'

        logger.info(f"Specialized child content model enabled: {self.use_specialized_child_model}")

        # Device configuration
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.initialized_time = None

        # Context-aware filtering
        self.context_patterns = self._initialize_context_patterns()

        # Initialize the models
        self._initialize_primary_model()
        self._initialize_child_model()

        self._initialized = True

    def _initialize_context_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize patterns for context-aware filtering"""
        return {
            "child_related": {
                "terms": [
                    # Basic child-related terms
                    "child", "kid", "young", "teen", "minor", "underage", "girl", "boy",
                    "daughter", "son", "school", "student", "baby", "infant", "toddler",
                    # Additional age-related terms
                    "adolescent", "youth", "juvenile", "preteen", "tween", "teenager",
                    "kindergarten", "elementary", "preschool", "daycare", "nursery",
                    # Family-related terms
                    "children", "kids", "minors", "youngster", "little one", "little girl", "little boy"
                ],
                "threshold_modifier": 0.3,  # Significantly lower the threshold when these terms are present
                "exclusion_terms": ["adult", "adults", "woman", "man", "women", "men"]  # Terms that should not trigger child-related detection
            },
            "educational": {
                "terms": [
                    "education", "school", "learning", "teaching", "academic", "study",
                    "research", "science", "history", "literature", "art", "biology"
                ],
                "threshold_modifier": 1.5  # Increase the threshold for educational content
            },
            "medical": {
                "terms": [
                    "medical", "health", "doctor", "hospital", "treatment", "patient",
                    "disease", "condition", "symptom", "diagnosis", "therapy", "medicine"
                ],
                "threshold_modifier": 1.5  # Increase the threshold for medical content
            },
            "animal": {
                "terms": [
                    "cat", "dog", "pet", "animal", "bird", "fish", "wildlife",
                    "nature", "zoo", "farm", "veterinary", "species"
                ],
                "threshold_modifier": 2.0  # Significantly increase threshold for animal content
            }
        }

    def _ensure_dependencies(self):
        """Ensure all required dependencies are installed"""
        try:
            # Try importing required packages
            import importlib.util

            required_packages = [
                ("transformers", "4.30.0"),
                ("torch", "2.0.0"),
                ("sentencepiece", "0.1.99"),
                ("accelerate", "0.20.0")
            ]

            missing_packages = []
            for package, min_version in required_packages:
                spec = importlib.util.find_spec(package)
                if spec is None:
                    missing_packages.append(package)
                    continue

                # Check version if package is installed
                try:
                    module = importlib.import_module(package)
                    if hasattr(module, "__version__"):
                        version = module.__version__
                        logger.info(f"Found {package} version {version}")
                    else:
                        logger.warning(f"Could not determine version for {package}")
                except ImportError:
                    missing_packages.append(package)

            if missing_packages:
                logger.warning(f"Missing required packages: {missing_packages}")
                logger.info("Attempting to install missing packages...")

                import subprocess
                import sys

                # Install missing packages
                for package in missing_packages:
                    logger.info(f"Installing {package}...")
                    try:
                        subprocess.check_call([
                            sys.executable, "-m", "pip", "install", package
                        ])
                        logger.info(f"Successfully installed {package}")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"Failed to install {package}: {e}")
                        raise

            return True
        except Exception as e:
            logger.error(f"Error ensuring dependencies: {e}")
            return False

    def _initialize_primary_model(self):
        """Initialize the primary transformer model for general content filtering"""
        try:
            # First, ensure required packages are installed
            self._ensure_dependencies()

            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            start_time = time.time()
            logger.info(f"Initializing primary content filter model ({self.primary_model_path}) on {self.device}...")

            # Create cache directory if it doesn't exist
            import os
            from pathlib import Path
            cache_dir = Path.home() / ".cache" / "huggingface" / "transformers"
            os.makedirs(cache_dir, exist_ok=True)

            # Load the model and tokenizer with progress logging
            logger.info("Downloading and loading primary model...")
            try:
                self.primary_model = AutoModelForSequenceClassification.from_pretrained(self.primary_model_path)
                logger.info("Primary model loaded successfully")
            except Exception as model_error:
                logger.error(f"Error loading primary model: {model_error}")
                logger.info("Retrying with no_init_weights=True...")
                self.primary_model = AutoModelForSequenceClassification.from_pretrained(
                    self.primary_model_path,
                    _fast_init=False,
                    low_cpu_mem_usage=True
                )

            logger.info("Downloading and loading primary tokenizer...")
            self.primary_tokenizer = AutoTokenizer.from_pretrained(self.primary_model_path)

            # Move model to GPU if available
            self.primary_model.to(self.device)

            # Set model to evaluation mode
            self.primary_model.eval()

            # Get category labels from the model config
            if hasattr(self.primary_model.config, "id2label"):
                self.primary_categories = list(self.primary_model.config.id2label.values())
            else:
                self.primary_categories = ["toxic", "non_toxic"]

            self.initialized_time = time.time()
            logger.info(f"Primary content filter model initialized in {self.initialized_time - start_time:.2f} seconds")
            logger.info(f"Primary model categories: {self.primary_categories}")

            return True
        except Exception as e:
            logger.error(f"Error initializing primary transformer model: {e}")
            return False

    def _initialize_child_model(self):
        """Initialize the specialized model for child-related content detection"""
        try:
            # First, ensure required packages are installed
            self._ensure_dependencies()

            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            start_time = time.time()
            logger.info(f"Initializing child content filter model ({self.child_model_path}) on {self.device}...")

            # Create cache directory if it doesn't exist
            import os
            from pathlib import Path
            cache_dir = Path.home() / ".cache" / "huggingface" / "transformers"
            os.makedirs(cache_dir, exist_ok=True)

            # Load the model and tokenizer with progress logging
            logger.info("Downloading and loading child content model...")
            try:
                self.child_model = AutoModelForSequenceClassification.from_pretrained(self.child_model_path)
                logger.info("Child content model loaded successfully")
            except Exception as model_error:
                logger.error(f"Error loading child content model: {model_error}")
                logger.info("Retrying with no_init_weights=True...")
                self.child_model = AutoModelForSequenceClassification.from_pretrained(
                    self.child_model_path,
                    _fast_init=False,
                    low_cpu_mem_usage=True
                )

            logger.info("Downloading and loading child content tokenizer...")
            self.child_tokenizer = AutoTokenizer.from_pretrained(self.child_model_path)

            # Move model to GPU if available
            self.child_model.to(self.device)

            # Set model to evaluation mode
            self.child_model.eval()

            # Get category labels from the model config
            if hasattr(self.child_model.config, "id2label"):
                self.child_categories = list(self.child_model.config.id2label.values())
            else:
                self.child_categories = ["inappropriate", "appropriate"]

            logger.info(f"Child content filter model initialized in {time.time() - start_time:.2f} seconds")
            logger.info(f"Child model categories: {self.child_categories}")

            return True
        except Exception as e:
            logger.error(f"Error initializing child content transformer model: {e}")
            return False

    def _get_context_adjusted_threshold(self, text: str, base_threshold: float, category: str) -> float:
        """
        Adjust the threshold based on the context of the text.

        Args:
            text: The text to analyze
            base_threshold: The base threshold value
            category: The category being checked (toxic, sexual, etc.)

        Returns:
            Adjusted threshold value
        """
        # Convert text to lowercase for matching
        text_lower = text.lower()

        # Start with the base threshold
        adjusted_threshold = base_threshold

        # Track which context patterns were matched
        matched_contexts = []

        # Apply context-based adjustments
        for context_name, context_data in self.context_patterns.items():
            # Check if any terms from this context are in the text
            if any(term in text_lower for term in context_data["terms"]):
                # Apply the modifier to the threshold
                adjusted_threshold *= context_data["threshold_modifier"]
                matched_contexts.append(context_name)

        # Cap the threshold at 0.99 to prevent it from becoming too permissive
        adjusted_threshold = min(adjusted_threshold, 0.99)

        # Log the adjustment if any was made
        if matched_contexts:
            logger.info(f"Adjusted {category} threshold from {base_threshold} to {adjusted_threshold} due to contexts: {matched_contexts}")

        return adjusted_threshold

    def check_content(self, text: str) -> Tuple[bool, Dict[str, float], Optional[str], Optional[float], Optional[str]]:
        """
        Check if content is safe using the primary transformer model.

        Args:
            text: The text to check

        Returns:
            Tuple of (is_safe, scores, violation_type, violation_score, threshold_name)
            - is_safe: Whether the content is safe
            - scores: Dictionary of category scores
            - violation_type: The type of violation (toxic, sexual, etc.) or None if safe
            - violation_score: The score for the violation or None if safe
            - threshold_name: The name of the threshold that was exceeded or None if safe
        """
        # First, do a quick check for harmful terms related to children
        # This is a direct pattern matching approach that doesn't rely on the model
        child_related_terms = self.context_patterns["child_related"]["terms"]

        # Define harmful terms based on whether adult content is allowed
        if self.allow_adult_content:
            # If adult content is allowed, exclude sexual terms from the harmful list
            harmful_terms = [
                "violent", "violence", "harm", "hurt", "abuse", "cry", "crying",
                "exploit", "hit", "slap", "beat", "kill", "torture", "punish", "punishment"
            ]

            # These terms are always harmful when combined with child-related terms
            child_harmful_terms = [
                "sexual", "naked", "nude", "inappropriate", "explicit"
            ]
        else:
            # If adult content is not allowed, include all harmful terms
            harmful_terms = [
                "violent", "violence", "harm", "hurt", "abuse", "cry", "crying",
                "inappropriate", "explicit", "sexual", "naked", "nude", "exploit",
                "hit", "slap", "beat", "kill", "torture", "punish", "punishment"
            ]
            child_harmful_terms = []

        # Check if the text contains both child-related terms and harmful terms
        text_lower = text.lower()

        # No need to check exclusion terms here since we handle adult+child combinations separately

        # Check if the text explicitly contains 'adult' or 'adults'
        has_adult_term = 'adult' in text_lower or 'adults' in text_lower

        # Check if the text contains child-related terms
        has_child_term = any(term in text_lower for term in child_related_terms)

        # Special case: If the text contains BOTH adult terms AND child terms, it might be concerning
        # This catches cases like "Adult naked man with child"
        if has_adult_term and has_child_term:
            # Check for potentially concerning combinations
            concerning_adult_child_terms = [
                "naked", "nude", "bed", "touching", "inappropriate",
                "explicit", "pornographic", "obscene"
            ]

            # Special case for "sexual content between adults" which should be allowed
            if "sexual" in text_lower and "between adults" in text_lower and not any(child_term in text_lower for child_term in ["child", "children", "kid", "kids", "minor", "minors", "young"]):
                logger.info(f"Allowing explicit adult content: {text}")
                # Skip further checks and allow this content
                return True, {}, None, None, None
            # If any concerning terms are present with both adult and child terms, block it
            elif any(term in text_lower for term in concerning_adult_child_terms):
                logger.warning(f"General check: Detected concerning combination of adult and child terms with '{text_lower}'")
                return False, {}, "adult_child_inappropriate", 0.95, "CONTENT_FILTER_CHILD_THRESHOLD"

        if has_child_term:
            # Check for general harmful terms
            for harmful_term in harmful_terms:
                if harmful_term in text_lower:
                    logger.warning(f"Direct pattern match: Detected harmful term '{harmful_term}' with child-related content: {text}")
                    return False, {}, "harmful_child_content", 0.9, "CONTENT_FILTER_CHILD_THRESHOLD"

            # If adult content is allowed, also check for child-specific harmful terms
            if self.allow_adult_content:
                for harmful_term in child_harmful_terms:
                    if harmful_term in text_lower:
                        logger.warning(f"Direct pattern match: Detected child-inappropriate term '{harmful_term}' with child-related content: {text}")
                        return False, {}, "inappropriate_child_content", 0.95, "CONTENT_FILTER_CHILD_THRESHOLD"
        if not self.primary_model or not self.primary_tokenizer:
            logger.warning("Primary transformer model not initialized, skipping check")
            return True, {}, None, None, None

        try:
            # Tokenize the input text
            inputs = self.primary_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Get model predictions
            with torch.no_grad():
                outputs = self.primary_model(**inputs)

            # Convert logits to probabilities
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
            probs = probs.cpu().numpy()[0]

            # Create a dictionary of category scores
            scores = {self.primary_categories[i]: float(probs[i]) for i in range(len(self.primary_categories))}

            # Determine if content is safe based on scores
            is_safe = True
            violation_type = None
            violation_score = None
            threshold_name = None

            # Check for toxic content with context-adjusted threshold
            if "toxic" in scores:
                toxic_score = scores["toxic"]
                adjusted_threshold = self._get_context_adjusted_threshold(text, self.toxic_threshold, "toxic")

                # If adult content is allowed, check if the content contains adult-related terms
                if self.allow_adult_content:
                    # Get adult-related terms from the exclusion list
                    adult_terms = self.context_patterns["child_related"].get("exclusion_terms", [])
                    text_lower = text.lower()

                    # If the content contains adult terms, be more permissive with toxic content
                    if any(term in text_lower for term in adult_terms):
                        # Increase the threshold for adult content
                        adjusted_threshold = max(adjusted_threshold, 0.99)
                        logger.info(f"Increased toxic threshold to {adjusted_threshold} for adult content")

                if toxic_score > adjusted_threshold:
                    is_safe = False
                    violation_type = "toxic"
                    violation_score = toxic_score
                    threshold_name = "CONTENT_FILTER_TOXIC_THRESHOLD"
                    logger.warning(f"Detected toxic content: {toxic_score:.2f} (threshold: {adjusted_threshold})")

            # Check for other harmful categories with context-adjusted thresholds
            harmful_categories = {
                "obscene": self.harmful_threshold,
                "threat": self.harmful_threshold,
                "insult": self.harmful_threshold,
                "identity_hate": self.hate_threshold,
                "severe_toxic": self.harmful_threshold,
                "hate": self.hate_threshold,
                "violence": self.violence_threshold
            }

            # Only include sexual categories if adult content is not allowed
            if not self.allow_adult_content:
                harmful_categories["sexual"] = self.sexual_threshold

            # Only check these if we haven't already found a violation
            if is_safe:
                for category, base_threshold in harmful_categories.items():
                    if category in scores:
                        adjusted_threshold = self._get_context_adjusted_threshold(text, base_threshold, category)

                        if scores[category] > adjusted_threshold:
                            is_safe = False
                            violation_type = category
                            violation_score = scores[category]
                            threshold_name = f"CONTENT_FILTER_{category.upper()}_THRESHOLD"
                            logger.warning(f"Detected harmful content: {category} = {scores[category]:.2f} (threshold: {adjusted_threshold})")
                            break  # Stop after finding the first violation

            return is_safe, scores, violation_type, violation_score, threshold_name

        except Exception as e:
            logger.error(f"Error checking content with primary transformer model: {e}")
            return True, {}, None, None, None

    def check_prompt_for_child_content(self, text: str) -> Tuple[bool, Optional[str], float, Optional[str]]:
        """
        Specifically check if a prompt might generate child-related inappropriate content.
        Uses a specialized model for child content detection.

        Args:
            text: The prompt to check

        Returns:
            Tuple of (is_safe, reason, confidence_score, threshold_name)
            - is_safe: Whether the content is safe
            - reason: The reason for the violation or None if safe
            - confidence_score: The confidence score for the violation or 0.0 if safe
            - threshold_name: The name of the threshold that was exceeded or None if safe
        """
        # First check if we have a specialized child content model and it's enabled
        if self.child_model and self.child_tokenizer and self.use_specialized_child_model:
            try:
                # Tokenize the input text
                inputs = self.child_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

                # Get model predictions
                with torch.no_grad():
                    outputs = self.child_model(**inputs)

                # Convert logits to probabilities
                probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
                probs = probs.cpu().numpy()[0]

                # Create a dictionary of category scores
                scores = {self.child_categories[i]: float(probs[i]) for i in range(len(self.child_categories))}

                # For the roberta_toxicity_classifier model, we only care about the 'toxic' category
                # The 'neutral' category should not trigger a block by itself
                if 'toxic' in scores:
                    toxic_score = scores['toxic']
                    # Use a very low threshold for child-related content
                    adjusted_threshold = self._get_context_adjusted_threshold(text, self.child_content_threshold * 0.5, 'toxic')

                    if toxic_score > adjusted_threshold:
                        logger.warning(f"Specialized model detected toxic content: {toxic_score:.2f} (threshold: {adjusted_threshold})")
                        return False, f"Potentially inappropriate content involving minors", toxic_score, "CONTENT_FILTER_CHILD_THRESHOLD"

                # Check for child-related terms combined with the content
                child_related_terms = self.context_patterns["child_related"]["terms"]

                # Get exclusion terms that should not trigger child-related detection
                exclusion_terms = self.context_patterns["child_related"].get("exclusion_terms", [])

                # Check if any exclusion terms are present
                text_lower = text.lower()
                has_exclusion_term = any(term in text_lower for term in exclusion_terms)

                # Check if the text explicitly contains 'adult' or 'adults'
                text_lower = text.lower()
                has_adult_term = 'adult' in text_lower or 'adults' in text_lower

                # Check if the text contains child-related terms
                has_child_term = any(term in text_lower for term in child_related_terms)

                # Special case: If the text contains BOTH adult terms AND child terms, it might be concerning
                # This catches cases like "Adult naked man with child"
                if has_adult_term and has_child_term:
                    # Check for potentially concerning combinations
                    concerning_adult_child_terms = [
                        "naked", "nude", "bed", "touching", "inappropriate",
                        "explicit", "pornographic", "obscene"
                    ]

                    # Special case for "sexual content between adults" which should be allowed
                    if "sexual" in text_lower and "between adults" in text_lower and not any(child_term in text_lower for child_term in ["child", "children", "kid", "kids", "minor", "minors", "young"]):
                        logger.info(f"Child check: Allowing explicit adult content: {text}")
                        return True, None, 0.0, None
                    # If any concerning terms are present with both adult and child terms, block it
                    elif any(term in text_lower for term in concerning_adult_child_terms):
                        logger.warning(f"Child check: Detected concerning combination of adult and child terms with '{text_lower}'")
                        return False, "Potentially inappropriate content involving adults and minors", 0.95, "CONTENT_FILTER_CHILD_THRESHOLD"
                    else:
                        # If it contains both adult and child terms but no concerning terms, allow it
                        # This handles cases like "Adult supervision required for children"
                        logger.info(f"Content contains both adult and child terms but appears safe: {text}")
                        return True, None, 0.0, None

                # Only consider child-related if it contains child terms and doesn't contain exclusion terms
                if has_child_term and not has_exclusion_term and not has_adult_term:
                    # For child-related content, we need to be more careful

                    # Define harmful terms based on whether adult content is allowed
                    if self.allow_adult_content:
                        # If adult content is allowed, exclude sexual terms from the harmful list
                        harmful_terms = [
                            "violent", "violence", "harm", "hurt", "abuse", "cry", "crying",
                            "exploit", "hit", "slap", "beat", "kill", "torture", "punish", "punishment"
                        ]

                        # These terms are always harmful when combined with child-related terms
                        child_harmful_terms = [
                            "sexual", "naked", "nude", "inappropriate", "explicit"
                        ]
                    else:
                        # If adult content is not allowed, include all harmful terms
                        harmful_terms = [
                            "violent", "violence", "harm", "hurt", "abuse", "cry", "crying",
                            "inappropriate", "explicit", "sexual", "naked", "nude", "exploit",
                            "hit", "slap", "beat", "kill", "torture", "punish", "punishment"
                        ]
                        child_harmful_terms = []

                    # Check for harmful terms combined with child-related terms
                    text_lower = text.lower()

                    # Check for general harmful terms
                    for harmful_term in harmful_terms:
                        if harmful_term in text_lower:
                            logger.warning(f"Detected harmful term '{harmful_term}' combined with child-related content: {text}")
                            return False, "Potentially harmful content involving minors", 0.9, "CONTENT_FILTER_CHILD_THRESHOLD"

                    # If adult content is allowed, also check for child-specific harmful terms
                    if self.allow_adult_content:
                        for harmful_term in child_harmful_terms:
                            if harmful_term in text_lower:
                                logger.warning(f"Detected child-inappropriate term '{harmful_term}' with child-related content: {text}")
                                return False, "Potentially inappropriate content involving minors", 0.95, "CONTENT_FILTER_CHILD_THRESHOLD"

                    # Then check for educational or innocent content that should be allowed
                    educational_terms = self.context_patterns["educational"]["terms"]
                    animal_terms = self.context_patterns["animal"]["terms"]

                    # If it contains educational or animal terms, it's likely safe
                    if any(term in text.lower() for term in educational_terms) or any(term in text.lower() for term in animal_terms):
                        logger.info("Child-related content appears to be educational or about animals, allowing it")
                        return True, None, 0.0, None

                logger.info("Specialized child content check passed")

            except Exception as e:
                logger.error(f"Error checking with specialized child content model: {e}")
                # Fall back to primary model if specialized model fails

        # Fall back to primary model if specialized model is not available or failed
        if not self.primary_model or not self.primary_tokenizer:
            logger.warning("Primary transformer model not initialized, skipping check")
            return True, None, 0.0, None

        try:
            # Tokenize the input text
            inputs = self.primary_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Get model predictions
            with torch.no_grad():
                outputs = self.primary_model(**inputs)

            # Convert logits to probabilities
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
            probs = probs.cpu().numpy()[0]

            # Create a dictionary of category scores
            scores = {self.primary_categories[i]: float(probs[i]) for i in range(len(self.primary_categories))}

            # Check for toxic content with a much lower threshold for child-related content
            if "toxic" in scores:
                toxic_score = scores["toxic"]
                # Use a significantly lower threshold for child content detection
                # This makes the filter more sensitive to potentially inappropriate content
                adjusted_threshold = self._get_context_adjusted_threshold(text, self.child_content_threshold * 0.5, "toxic")

                if toxic_score > adjusted_threshold:
                    logger.warning(f"Detected toxic content in child check: {toxic_score:.2f} (threshold: {adjusted_threshold})")
                    return False, "Potentially inappropriate content involving minors", toxic_score, "CONTENT_FILTER_CHILD_THRESHOLD"

            # Check for sexual content
            if "sexual" in scores:
                sexual_score = scores["sexual"]
                adjusted_threshold = self._get_context_adjusted_threshold(text, self.sexual_threshold, "sexual")

                # Only block sexual content if adult content is not allowed
                if not self.allow_adult_content and sexual_score > adjusted_threshold:
                    logger.warning(f"Detected sexual content: {sexual_score:.2f} (threshold: {adjusted_threshold})")
                    return False, "Potentially inappropriate sexual content", sexual_score, "CONTENT_FILTER_SEXUAL_THRESHOLD"
                elif self.allow_adult_content and sexual_score > adjusted_threshold:
                    logger.info(f"Detected adult content but allowing it: {sexual_score:.2f} (threshold: {adjusted_threshold})")

            # Check for child-related terms combined with concerning content
            child_related_terms = self.context_patterns["child_related"]["terms"]

            # Enhanced detection for child-related terms
            # If child-related terms are present, apply much stricter thresholds
            if any(term in text.lower() for term in child_related_terms):
                # First check for harmful terms that should always be blocked when combined with child-related terms
                harmful_terms = [
                    "violent", "violence", "harm", "hurt", "abuse", "cry", "crying",
                    "inappropriate", "explicit", "sexual", "naked", "nude", "exploit",
                    "hit", "slap", "beat", "kill", "torture", "punish", "punishment"
                ]

                # Check for harmful terms combined with child-related terms
                text_lower = text.lower()

                # Check if the text explicitly contains 'adult' or 'adults' to avoid false positives
                has_adult_term = 'adult' in text_lower or 'adults' in text_lower

                # If the content is specifically about adults, don't block it
                if has_adult_term:
                    logger.info(f"Content contains adult terms, allowing it: {text}")
                    return True, None, 0.0, None

                # Otherwise, check for harmful terms
                for harmful_term in harmful_terms:
                    if harmful_term in text_lower:
                        logger.warning(f"Detected harmful term '{harmful_term}' combined with child-related content in general check: {text}")
                        return False, "Potentially harmful content involving minors", 0.9, "CONTENT_FILTER_CHILD_THRESHOLD"

                # Check for toxic content with child-related terms - use very low threshold
                if "toxic" in scores and scores["toxic"] > self.child_content_threshold * 0.3:
                    logger.warning(f"Detected toxic content with child-related terms: {scores['toxic']:.2f}")
                    return False, f"Potential inappropriate content involving minors (toxic)", scores["toxic"], "CONTENT_FILTER_CHILD_THRESHOLD"

                # For neutral/non-toxic content with child-related terms, we need more nuanced detection
                # Check for concerning categories with lower thresholds
                concerning_categories = {
                    "sexual": self.child_content_threshold * 0.3,  # Very low threshold for sexual content
                    "obscene": self.child_content_threshold * 0.4,
                    "threat": self.child_content_threshold * 0.5,
                    "identity_hate": self.child_content_threshold * 0.5,
                    "severe_toxic": self.child_content_threshold * 0.3,
                    "hate": self.child_content_threshold * 0.5,
                    "violence": self.child_content_threshold * 0.4
                }

                for category, threshold in concerning_categories.items():
                    if category in scores and scores[category] > threshold:
                        logger.warning(f"Detected {category} content with child-related terms: {scores[category]:.2f} (threshold: {threshold})")
                        return False, f"Potential inappropriate content involving minors ({category})", scores[category], "CONTENT_FILTER_CHILD_THRESHOLD"

                # Check for combinations of categories that together might indicate inappropriate content
                # For example, if both "neutral" and "sexual" scores are moderately high
                if "neutral" in scores and "sexual" in scores:
                    combined_score = scores["neutral"] * 0.3 + scores["sexual"] * 0.7
                    if combined_score > 0.6:
                        logger.warning(f"Detected concerning combination of categories with child-related terms: {combined_score:.2f}")
                        return False, "Potential inappropriate content involving minors (combined categories)", combined_score, "CONTENT_FILTER_CHILD_THRESHOLD"

                # Check if the content is educational or about animals - these are likely safe
                educational_terms = self.context_patterns["educational"]["terms"]
                animal_terms = self.context_patterns["animal"]["terms"]
                if any(term in text.lower() for term in educational_terms) or any(term in text.lower() for term in animal_terms):
                    logger.info("Child-related content appears to be educational or about animals, allowing it")
                    # Continue with the check, but with higher thresholds

            return True, None, 0.0, None

        except Exception as e:
            logger.error(f"Error checking for child content: {e}")
            return True, None, 0.0, None

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded models.

        Returns:
            Dictionary with model information
        """
        return {
            "primary_model_path": self.primary_model_path,
            "primary_model_initialized": self.primary_model is not None,
            "primary_categories": self.primary_categories,
            "child_model_path": self.child_model_path,
            "child_model_initialized": self.child_model is not None,
            "child_categories": self.child_categories,
            "device": self.device,
            "initialized_time": self.initialized_time
        }
