"""
Rephrasing Engine Module
Uses T5 transformer model for paraphrasing text
"""

# Import config first to set environment variables
import app.config  # noqa: F401

import logging
from typing import List, Tuple
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
import nltk
from nltk.tokenize import sent_tokenize

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    try:
        nltk.download('punkt_tab', quiet=True)
    except:
        # Fallback to punkt if punkt_tab not available
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)

logger = logging.getLogger(__name__)

class RephrasingEngine:
    """Rephrases text using T5 transformer model"""
    
    def __init__(self, model_name: str = "Vamsi/T5_Paraphrase_Paws"):
        """
        Initialize the rephrasing engine
        
        Args:
            model_name: Name of the T5 model for paraphrasing
        """
        logger.info(f"Loading rephrasing model: {model_name}")
        try:
            # Try to load with fast tokenizer first, fallback to slow if needed
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
            except (ValueError, OSError) as e:
                logger.warning(f"Fast tokenizer failed, using slow tokenizer: {e}")
                self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
            
            self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            self.model.eval()
            logger.info(f"Rephrasing model loaded successfully on {self.device}")
        except Exception as e:
            logger.error(f"Error loading rephrasing model: {e}")
            raise
    
    def rephrase_sentence(self, sentence: str, max_length: int = 128, num_beams: int = 4) -> str:
        """
        Rephrase a single sentence
        
        Args:
            sentence: Sentence to rephrase
            max_length: Maximum length of generated text
            num_beams: Number of beams for beam search
            
        Returns:
            Rephrased sentence
        """
        try:
            # Format input for T5 paraphrase model
            input_text = f"paraphrase: {sentence} </s>"
            
            # Tokenize input
            inputs = self.tokenizer.encode(
                input_text,
                return_tensors="pt",
                max_length=512,
                truncation=True,
                padding=True
            ).to(self.device)
            
            # Generate rephrased text
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=max_length,
                    num_beams=num_beams,
                    early_stopping=True,
                    do_sample=False
                )
            
            # Decode output
            rephrased = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return rephrased.strip()
        
        except Exception as e:
            logger.error(f"Error rephrasing sentence: {e}")
            return sentence  # Return original if rephrasing fails
    
    def rephrase_text_sentence_by_sentence(
        self,
        text: str,
        preserve_meaning: bool = True
    ) -> List[Tuple[str, str]]:
        """
        Rephrase text sentence by sentence
        
        Args:
            text: Text to rephrase
            preserve_meaning: Whether to preserve original meaning
            
        Returns:
            List of tuples (original_sentence, rephrased_sentence)
        """
        # Split text into sentences
        sentences = sent_tokenize(text)
        rephrased_pairs = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            rephrased = self.rephrase_sentence(sentence)
            rephrased_pairs.append((sentence, rephrased))
        
        return rephrased_pairs
    
    def rephrase_with_fallback(self, sentence: str, max_attempts: int = 3) -> str:
        """
        Rephrase sentence with multiple attempts if needed
        
        Args:
            sentence: Sentence to rephrase
            max_attempts: Maximum number of rephrasing attempts
            
        Returns:
            Best rephrased sentence
        """
        best_rephrased = sentence
        
        for attempt in range(max_attempts):
            rephrased = self.rephrase_sentence(sentence)
            # If rephrased is different from original, use it
            if rephrased.lower() != sentence.lower():
                best_rephrased = rephrased
                break
        
        return best_rephrased

