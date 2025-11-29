"""
Database connection and configuration
"""

import os
from pymongo import MongoClient
from pymongo.database import Database
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# MongoDB connection
_client: Optional[MongoClient] = None
_db: Optional[Database] = None

def get_database() -> Optional[Database]:
    """Get MongoDB database instance"""
    return _db

def init_db():
    """Initialize database connection"""
    global _client, _db
    
    try:
        # Get MongoDB connection string from environment or use default
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
        db_name = os.getenv("MONGODB_DB_NAME", "plagiarism_agent")
        
        _client = MongoClient(mongodb_url)
        _db = _client[db_name]
        
        # Create indexes
        _db.submissions.create_index("submission_id", unique=True)
        _db.submissions.create_index("student_id")
        _db.submissions.create_index("timestamp")
        
        logger.info(f"Database initialized: {db_name}")
    except Exception as e:
        logger.warning(f"Could not connect to MongoDB: {e}. Continuing without database.")
        _db = None

def close_db():
    """Close database connection"""
    global _client
    if _client:
        _client.close()
        logger.info("Database connection closed")

