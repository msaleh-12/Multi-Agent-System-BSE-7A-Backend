"""
Database models for storing submissions and results
"""

from datetime import datetime, timezone
from typing import List, Dict, Any
from app.models.schemas import RephrasedSentence

class SubmissionRecord:
    """Model for storing submission records in database"""
    
    @staticmethod
    def create_record(
        student_id: str,
        submission_id: str,
        student_text: str,
        rephrased_sentences: List[RephrasedSentence],
        pledge_percentage: float,
        feedback: str,
        timestamp: str
    ) -> Dict[str, Any]:
        """
        Create a submission record for database storage
        
        Returns:
            Dictionary representation of the record
        """
        return {
            "student_id": student_id,
            "submission_id": submission_id,
            "student_text": student_text,
            "rephrased_text": [
                {
                    "original_sentence": sent.original_sentence,
                    "rephrased_sentence": sent.rephrased_sentence,
                    "similarity_score": sent.similarity_score
                }
                for sent in rephrased_sentences
            ],
            "pledge_percentage": pledge_percentage,
            "feedback": feedback,
            "timestamp": timestamp,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    
    @staticmethod
    def save_to_db(record: Dict[str, Any]):
        """Save record to database"""
        from app.database.connection import get_database
        db = get_database()
        if db is not None:
            try:
                db.submissions.insert_one(record)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error saving to database: {e}")

