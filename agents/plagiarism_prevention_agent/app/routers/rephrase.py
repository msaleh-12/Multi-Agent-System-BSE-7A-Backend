"""
Text rephrasing API endpoints
"""

from fastapi import APIRouter, HTTPException
from app.models.schemas import RephraseRequest, RephraseResponse, RephrasedSentence
from app.services.rephrasing_engine import RephrasingEngine
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize rephrasing engine (singleton pattern)
_rephrasing_engine = None

def get_rephrasing_engine() -> RephrasingEngine:
    """Get or create rephrasing engine instance"""
    global _rephrasing_engine
    if _rephrasing_engine is None:
        _rephrasing_engine = RephrasingEngine()
    return _rephrasing_engine

@router.post("/rephrase-text", response_model=RephraseResponse)
async def rephrase_text(request: RephraseRequest):
    """
    Rephrase text sentence by sentence
    
    Args:
        request: RephraseRequest with text and preserve_meaning flag
        
    Returns:
        RephraseResponse with original, rephrased text, and sentence pairs
    """
    try:
        engine = get_rephrasing_engine()
        
        # Rephrase text sentence by sentence
        rephrased_pairs = engine.rephrase_text_sentence_by_sentence(
            request.text,
            preserve_meaning=request.preserve_meaning
        )
        
        # Create RephrasedSentence objects
        sentences = [
            RephrasedSentence(
                original_sentence=orig,
                rephrased_sentence=rephr,
                similarity_score=0.0  # Not computed in this endpoint
            )
            for orig, rephr in rephrased_pairs
        ]
        
        # Combine rephrased sentences
        rephrased_text = " ".join([sent.rephrased_sentence for sent in sentences])
        
        return RephraseResponse(
            original_text=request.text,
            rephrased_text=rephrased_text,
            sentences=sentences
        )
    
    except Exception as e:
        logger.error(f"Error in rephrasing: {e}")
        raise HTTPException(status_code=500, detail=f"Error rephrasing text: {str(e)}")

