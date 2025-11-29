"""
Similarity Detection Module
Uses SentenceTransformers to detect similarity between texts
"""

# Import config first to set environment variables
import app.config  # noqa: F401

import numpy as np
from sentence_transformers import SentenceTransformer, util
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class SimilarityDetector:
    """Detects similarity between texts using sentence embeddings"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", threshold: float = 0.80):
        """
        Initialize the similarity detector
        
        Args:
            model_name: Name of the SentenceTransformer model
            threshold: Similarity threshold for plagiarism detection
        """
        logger.info(f"Loading similarity model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold
        logger.info("Similarity model loaded successfully")
    
    def encode_text(self, text: str) -> np.ndarray:
        """
        Encode text into embedding vector
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector
        """
        return self.model.encode(text, convert_to_tensor=False)
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0.0 - 1.0)
        """
        emb1 = self.model.encode(text1, convert_to_tensor=True)
        emb2 = self.model.encode(text2, convert_to_tensor=True)
        similarity = util.cos_sim(emb1, emb2).item()
        return float(similarity)
    
    def is_plagiarized(self, similarity_score: float) -> bool:
        """
        Determine if text is plagiarized based on similarity score
        
        Args:
            similarity_score: Similarity score (0.0 - 1.0)
            
        Returns:
            True if plagiarized, False otherwise
        """
        return similarity_score >= self.threshold
    
    def compare_with_datasets(self, text: str, datasets: List[str]) -> Tuple[float, str]:
        """
        Compare text against multiple datasets and return highest similarity
        
        Args:
            text: Text to check
            datasets: List of reference texts/datasets
            
        Returns:
            Tuple of (max_similarity_score, source_name)
        """
        max_similarity = 0.0
        max_source = None
        
        for dataset_text in datasets:
            similarity = self.compute_similarity(text, dataset_text)
            if similarity > max_similarity:
                max_similarity = similarity
                max_source = dataset_text[:50] + "..." if len(dataset_text) > 50 else dataset_text
        
        return max_similarity, max_source or "unknown"
    
    def sentence_similarity(self, sentence: str, reference_texts: List[str]) -> float:
        """
        Compute maximum similarity of a sentence against reference texts
        
        Args:
            sentence: Sentence to check
            reference_texts: List of reference texts
            
        Returns:
            Maximum similarity score
        """
        if not reference_texts:
            return 0.0
        
        max_sim = 0.0
        for ref_text in reference_texts:
            sim = self.compute_similarity(sentence, ref_text)
            max_sim = max(max_sim, sim)
        
        return max_sim

