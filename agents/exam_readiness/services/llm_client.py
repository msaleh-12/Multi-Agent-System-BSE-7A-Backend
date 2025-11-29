import os
import logging
import google.generativeai as genai
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

_logger = logging.getLogger(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")

def _get_mode():
    """Determine if we should use cloud or mock mode"""
    if API_KEY:
        genai.configure(api_key=API_KEY)
        return "cloud"
    _logger.warning("GEMINI_API_KEY not set, falling back to 'mock' mode.")
    return "mock"

def query_llm(prompt: str, model: str = "gemini-2.5-flash", max_tokens: int = 8000) -> str:
    """
    Query the LLM using Google's Gemini API.
    Uses environment variable GEMINI_API_KEY for authentication.
    Falls back to mock mode if API key is not set.
    """
    mode = _get_mode()
    
    if mode == "mock":
        _logger.info("Using mock mode for LLM query")
        return f"[MOCK] Generated response for prompt: {prompt[:100]}..."
    
    try:
        model_instance = genai.GenerativeModel(
            model,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": 0.7,
            }
        )
        
        response = model_instance.generate_content(prompt)
        return response.text
    
    except Exception as e:
        _logger.error(f"Error calling Google GenAI: {e}")
        raise RuntimeError(f"Gemini API request failed: {str(e)}")