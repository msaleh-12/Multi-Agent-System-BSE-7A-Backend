"""
Main processing endpoint that orchestrates similarity detection and rephrasing
"""

from fastapi import APIRouter, HTTPException
from app.models.schemas import PPARequest, PPAResponse, PPAOutput
from app.services.plagiarism_processor import PlagiarismProcessor
from app.database.models import SubmissionRecord
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize processor (singleton pattern)
_processor = None

def get_processor() -> PlagiarismProcessor:
    """Get or create plagiarism processor instance"""
    global _processor
    if _processor is None:
        _processor = PlagiarismProcessor()
    return _processor

@router.post("/process-text", response_model=PPAResponse)
async def process_text(request: PPARequest):
    """
    Main endpoint for processing text: detects similarity and rephrases
    
    This is the unified endpoint that the Supervisor Agent should call.
    It combines similarity detection and rephrasing in one call.
    
    Args:
        request: PPARequest with student_id, input, and processing config
        
    Returns:
        PPAResponse with rephrased text, pledge percentage, and feedback
    """
    try:
        processor = get_processor()
        
        # Process the text (check online for plagiarism)
        rephrased_sentences, pledge_percentage, is_plagiarized, feedback = processor.process_text(
            student_text=request.input.student_text,
            comparison_sources=request.processing.comparison_sources,
            preserve_meaning=request.processing.preserve_meaning,
            improve_originality=request.processing.improve_originality,
            check_online=True  # Enable online plagiarism checking
        )
        
        # Determine if plagiarism was detected
        plagiarism_detected = any(sent.is_plagiarized for sent in rephrased_sentences)
        
        # Create output
        output = PPAOutput(
            rephrased_text=rephrased_sentences,
            pledge_percentage=pledge_percentage,
            is_plagiarized=is_plagiarized,
            plagiarism_detected=plagiarism_detected,
            feedback=feedback
        )
        
        # Save to database
        record = SubmissionRecord.create_record(
            student_id=request.student_id,
            submission_id=request.input.submission_id,
            student_text=request.input.student_text,
            rephrased_sentences=rephrased_sentences,
            pledge_percentage=pledge_percentage,
            feedback=feedback,
            timestamp=request.input.timestamp
        )
        SubmissionRecord.save_to_db(record)
        
        # Create response
        response = PPAResponse(
            student_id=request.student_id,
            submission_id=request.input.submission_id,
            output=output,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        logger.info(f"Processed submission {request.input.submission_id} for student {request.student_id}")
        
        return response
    
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing text: {str(e)}")

