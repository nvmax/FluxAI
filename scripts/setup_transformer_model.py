"""
Script to download and set up the transformer model for content filtering.
This script should be run during the setup process to ensure the model is available.
"""

import os
import sys
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

def setup_transformer_model():
    """Download and set up the transformer model for content filtering"""
    try:
        logger.info("Setting up transformer model for content filtering...")
        
        # Import required packages
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError:
            logger.error("Required packages not found. Please install them using:")
            logger.error("pip install transformers torch sentencepiece accelerate")
            return False
        
        # Check if CUDA is available
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")
        
        # Model to download
        model_name = "unitary/toxic-bert"
        logger.info(f"Downloading model: {model_name}")
        
        # Create cache directory if it doesn't exist
        cache_dir = Path.home() / ".cache" / "huggingface" / "transformers"
        os.makedirs(cache_dir, exist_ok=True)
        
        # Download the model and tokenizer
        logger.info("Downloading model...")
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        logger.info("Downloading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Test the model with a simple input
        logger.info("Testing model...")
        inputs = tokenizer("This is a test", return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)
        
        logger.info("Model setup completed successfully!")
        return True
    
    except Exception as e:
        logger.error(f"Error setting up transformer model: {e}")
        return False

if __name__ == "__main__":
    success = setup_transformer_model()
    sys.exit(0 if success else 1)
