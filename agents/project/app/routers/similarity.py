"""
Similarity detection API endpoints
"""

from fastapi import APIRouter, HTTPException
from app.models.schemas import SimilarityRequest, SimilarityResponse
from app.services.similarity_detector import SimilarityDetector
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize similarity detector (singleton pattern)
_similarity_detector = None

def get_similarity_detector() -> SimilarityDetector:
    """Get or create similarity detector instance"""
    global _similarity_detector
    if _similarity_detector is None:
        _similarity_detector = SimilarityDetector()
    return _similarity_detector

@router.post("/check-similarity", response_model=SimilarityResponse)
async def check_similarity(request: SimilarityRequest):
    """
    Check similarity between two texts
    
    Args:
        request: SimilarityRequest with text1 and optional text2
        
    Returns:
        SimilarityResponse with similarity score and plagiarism status
    """
    try:
        detector = get_similarity_detector()
        
        if request.text2:
            # Compare two texts
            similarity_score = detector.compute_similarity(request.text1, request.text2)
        else:
            # If only one text provided, return a default score
            # In production, this would compare against datasets
            similarity_score = 0.3  # Default assumption
        
        is_plagiarized = detector.is_plagiarized(similarity_score)
        
        return SimilarityResponse(
            similarity_score=similarity_score,
            is_plagiarized=is_plagiarized,
            threshold=detector.threshold
        )
    
    except Exception as e:
        logger.error(f"Error in similarity check: {e}")
        raise HTTPException(status_code=500, detail=f"Error checking similarity: {str(e)}")

