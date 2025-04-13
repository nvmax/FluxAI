"""
Transformer-based content filter service that uses a local model for content moderation.
"""

import os
import logging
import time
from typing import Tuple, Dict, Any, Optional, List
import torch
from src.infrastructure.config.config_manager import ConfigManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransformerContentFilter:
    """
    Content filter service using transformer models for context-aware content moderation.
    Uses a local model without requiring external API calls.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super(TransformerContentFilter, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_path: str = None):
        """
        Initialize the transformer content filter service.

        Args:
            model_path: Optional path to a pre-trained model. If None, will use a default model.
        """
        # Only initialize once (singleton pattern)
        if self._initialized:
            return

        # Load configuration
        self.config = ConfigManager()

        # Load thresholds from environment variables with defaults
        self.toxic_threshold = float(os.getenv('CONTENT_FILTER_TOXIC_THRESHOLD', '0.95'))
        self.harmful_threshold = float(os.getenv('CONTENT_FILTER_HARMFUL_THRESHOLD', '0.9'))
        self.sexual_threshold = float(os.getenv('CONTENT_FILTER_SEXUAL_THRESHOLD', '0.9'))
        self.child_content_threshold = float(os.getenv('CONTENT_FILTER_CHILD_THRESHOLD', '0.1'))

        # Log the thresholds
        logger.info(f"Content filter thresholds: toxic={self.toxic_threshold}, harmful={self.harmful_threshold}, sexual={self.sexual_threshold}, child={self.child_content_threshold}")

        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_path = model_path
        self.initialized_time = None
        self.categories = []

        # Initialize the model
        self._initialize_model()

        self._initialized = True

    def _initialize_model(self):
        """Initialize the transformer model for content filtering"""
        try:
            # First, ensure required packages are installed
            self._ensure_dependencies()

            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            start_time = time.time()
            logger.info(f"Initializing transformer content filter model on {self.device}...")

            # Default model if none specified
            if not self.model_path:
                # Use a model specifically trained for detecting harmful content
                # This model is trained to detect toxicity, obscenity, and other harmful content
                self.model_path = "unitary/toxic-bert"

            logger.info(f"Loading model: {self.model_path}")

            # Create cache directory if it doesn't exist
            import os
            from pathlib import Path
            cache_dir = Path.home() / ".cache" / "huggingface" / "transformers"
            os.makedirs(cache_dir, exist_ok=True)

            # Load the model and tokenizer with progress logging
            logger.info("Downloading and loading model...")
            try:
                self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
                logger.info("Model loaded successfully")
            except Exception as model_error:
                logger.error(f"Error loading model: {model_error}")
                logger.info("Retrying with no_init_weights=True...")
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_path,
                    _fast_init=False,
                    low_cpu_mem_usage=True
                )

            logger.info("Downloading and loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)

            # Move model to GPU if available
            self.model.to(self.device)

            # Set model to evaluation mode
            self.model.eval()

            # Get category labels from the model config
            if hasattr(self.model.config, "id2label"):
                self.categories = list(self.model.config.id2label.values())
            else:
                self.categories = ["harmful", "not_harmful"]

            self.initialized_time = time.time()
            logger.info(f"Transformer content filter initialized in {self.initialized_time - start_time:.2f} seconds")
            logger.info(f"Model categories: {self.categories}")

            return True
        except Exception as e:
            logger.error(f"Error initializing transformer content filter: {e}")
            return False

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

    def check_content(self, text: str) -> Tuple[bool, Dict[str, float], Optional[str], Optional[float], Optional[str]]:
        """
        Check if content is safe using the transformer model.

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
        if not self.model or not self.tokenizer:
            logger.warning("Transformer model not initialized, skipping check")
            return True, {}, None, None, None

        try:
            # Tokenize the input text
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Get model predictions
            with torch.no_grad():
                outputs = self.model(**inputs)

            # Convert logits to probabilities
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
            probs = probs.cpu().numpy()[0]

            # Create a dictionary of category scores
            scores = {self.categories[i]: float(probs[i]) for i in range(len(self.categories))}

            # Determine if content is safe based on scores
            # For Unitary's Toxic-BERT model
            is_safe = True
            violation_type = None
            violation_score = None
            threshold_name = None

            # Unitary's model has specific categories for different types of toxicity
            # The model outputs scores for 'toxic' and 'non-toxic' categories
            if "toxic" in scores:
                toxic_score = scores["toxic"]
                if toxic_score > self.toxic_threshold:  # Use configurable threshold from .env
                    is_safe = False
                    violation_type = "toxic"
                    violation_score = toxic_score
                    threshold_name = "CONTENT_FILTER_TOXIC_THRESHOLD"
                    logger.warning(f"Detected toxic content: {toxic_score:.2f} (threshold: {self.toxic_threshold})")

            # Check for other harmful categories if they exist in the model
            harmful_categories = [
                "obscene", "sexual", "threat", "insult", "identity_hate",
                "severe_toxic"
            ]

            # Only check these if we haven't already found a violation
            if is_safe:
                for category in harmful_categories:
                    if category in scores and scores[category] > self.harmful_threshold:
                        is_safe = False
                        violation_type = category
                        violation_score = scores[category]
                        threshold_name = "CONTENT_FILTER_HARMFUL_THRESHOLD"
                        logger.warning(f"Detected harmful content: {category} = {scores[category]:.2f} (threshold: {self.harmful_threshold})")
                        break  # Stop after finding the first violation

            return is_safe, scores, violation_type, violation_score, threshold_name

        except Exception as e:
            logger.error(f"Error checking content with transformer model: {e}")
            return True, {}, None, None, None

    def check_prompt_for_child_content(self, text: str) -> Tuple[bool, Optional[str], float, Optional[str]]:
        """
        Specifically check if a prompt might generate child-related inappropriate content.
        Microsoft's content safety model is particularly good at detecting this.

        Args:
            text: The prompt to check

        Returns:
            Tuple of (is_safe, reason, confidence_score, threshold_name)
            - is_safe: Whether the content is safe
            - reason: The reason for the violation or None if safe
            - confidence_score: The confidence score for the violation or 0.0 if safe
            - threshold_name: The name of the threshold that was exceeded or None if safe
        """
        if not self.model or not self.tokenizer:
            logger.warning("Transformer model not initialized, skipping check")
            return True, None, 0.0, None

        try:
            # Tokenize the input text
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Get model predictions
            with torch.no_grad():
                outputs = self.model(**inputs)

            # Convert logits to probabilities
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
            probs = probs.cpu().numpy()[0]

            # Create a dictionary of category scores
            scores = {self.categories[i]: float(probs[i]) for i in range(len(self.categories))}

            # For Unitary's model, we need to check for toxic content combined with child-related terms
            # since it doesn't have a specific category for minor-related content
            if "toxic" in scores:
                toxic_score = scores["toxic"]
                if toxic_score > self.child_content_threshold:  # Use configurable threshold from .env
                    logger.warning(f"Detected toxic content: {toxic_score:.2f} (threshold: {self.child_content_threshold})")
                    return False, "Potentially inappropriate content", toxic_score, "CONTENT_FILTER_CHILD_THRESHOLD"

            # Also check for sexual content which is particularly concerning
            if "sexual" in scores and scores["sexual"] > self.sexual_threshold:  # Use configurable threshold from .env
                sexual_score = scores["sexual"]
                logger.warning(f"Detected sexual content: {sexual_score:.2f} (threshold: {self.sexual_threshold})")
                return False, "Potentially inappropriate sexual content", sexual_score, "CONTENT_FILTER_SEXUAL_THRESHOLD"

            # If the model doesn't have a specific Sexual/Minors category, check for child-related terms
            # combined with sexual content
            child_related_terms = [
                "child", "kid", "young", "teen", "minor", "underage", "girl", "boy",
                "daughter", "son", "school", "student", "baby", "infant", "toddler"
            ]

            # If child-related terms are present, check for sexual content
            if any(term in text.lower() for term in child_related_terms):
                sexual_categories = [cat for cat in scores.keys() if "sexual" in cat.lower()]

                for category in sexual_categories:
                    if scores[category] > 0.4:  # Lower threshold when combined with child terms
                        logger.warning(f"Detected {category} content with child-related terms: {scores[category]:.2f}")
                        return False, f"Potential inappropriate content involving minors ({category})", scores[category]

            # Additional check for other harmful categories with child-related terms
            if any(term in text.lower() for term in child_related_terms):
                harmful_categories = ["Violence", "SelfHarm", "Hate", "Harassment"]

                for category in harmful_categories:
                    if category in scores and scores[category] > 0.6:  # Lower threshold when combined with child terms
                        logger.warning(f"Detected {category} content with child-related terms: {scores[category]:.2f}")
                        return False, f"Potential harmful content involving minors ({category})", scores[category], "CONTENT_FILTER_CHILD_THRESHOLD"

            return True, None, 0.0, None

        except Exception as e:
            logger.error(f"Error checking for child content: {e}")
            return True, None, 0.0, None

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.

        Returns:
            Dictionary with model information
        """
        return {
            "model_path": self.model_path,
            "device": self.device,
            "initialized": self.model is not None,
            "initialized_time": self.initialized_time,
            "categories": self.categories
        }
