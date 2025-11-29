"""
Configuration and environment setup
Set environment variables before any other imports
"""

import os

# Disable TensorFlow warnings and configure transformers
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

