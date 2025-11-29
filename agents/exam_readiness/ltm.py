"""
Long-Term Memory (LTM) module for caching generated assessments.
Uses SQLite to store assessment data and avoid redundant LLM calls.
"""
import logging
import hashlib
import aiosqlite
import json
from typing import Optional, Dict, Any
from pathlib import Path

_logger = logging.getLogger(__name__)

# Database path relative to exam_readiness directory
DB_PATH = Path(__file__).parent / "ltm_assessment.db"


async def init_db():
    """Initialize the LTM database for assessments"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ltm_assessments (
                cache_key TEXT PRIMARY KEY,
                parameters TEXT NOT NULL,
                assessment_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    _logger.info(f"Initialized assessment LTM database at {DB_PATH}")


async def lookup(cache_key: str) -> Optional[Dict[str, Any]]:
    """Look up cached assessment by cache key"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT assessment_data FROM ltm_assessments WHERE cache_key = ?",
                (cache_key,)
            )
            row = await cursor.fetchone()
            if row:
                _logger.info(f"LTM cache HIT for key {cache_key[:16]}...")
                return json.loads(row[0])
    except Exception as e:
        _logger.error(f"Error looking up cache: {e}")
    return None


async def save(cache_key: str, parameters: Dict[str, Any], assessment_data: Dict[str, Any]):
    """Save assessment to LTM cache"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO ltm_assessments (cache_key, parameters, assessment_data) VALUES (?, ?, ?)",
                (cache_key, json.dumps(parameters), json.dumps(assessment_data))
            )
            await db.commit()
        _logger.info(f"Saved to assessment LTM for key {cache_key[:16]}...")
    except Exception as e:
        _logger.error(f"Error saving to cache: {e}")


async def get_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Get total cached assessments
            cursor = await db.execute("SELECT COUNT(*) FROM ltm_assessments")
            total = (await cursor.fetchone())[0]
            
            # Get database file size
            db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
            
            # Get oldest and newest entries
            cursor = await db.execute(
                "SELECT MIN(created_at), MAX(created_at) FROM ltm_assessments"
            )
            oldest, newest = await cursor.fetchone()
            
            return {
                "total_cached": total,
                "database_size_bytes": db_size,
                "oldest_entry": oldest,
                "newest_entry": newest
            }
    except Exception as e:
        _logger.error(f"Error getting stats: {e}")
        return {"error": str(e)}


async def clear_cache():
    """Clear all cached assessments"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM ltm_assessments")
            await db.commit()
        _logger.info("Cleared all cached assessments from LTM")
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        _logger.error(f"Error clearing cache: {e}")
        return {"error": str(e)}


def generate_cache_key(params: Dict[str, Any]) -> str:
    """
    Generate deterministic cache key from assessment parameters.
    
    Cache key includes:
    - Core parameters: subject, assessment_type, difficulty, question_count, type_counts
    - LaTeX setting: allow_latex
    - RAG parameters: use_rag, rag_top_k, rag_max_chars, pdf_input_paths
    
    Note: PDF content changes won't invalidate cache (only filenames are tracked).
    For content-aware caching, consider adding file modification timestamps.
    """
    cacheable = {
        "subject": params.get("subject"),
        "assessment_type": params.get("assessment_type"),
        "difficulty": params.get("difficulty"),
        "question_count": params.get("question_count"),
        "type_counts": params.get("type_counts"),
        "allow_latex": params.get("allow_latex", True),
        "use_rag": params.get("use_rag", False),
    }
    
    # Include RAG parameters if RAG is enabled
    if cacheable["use_rag"]:
        cacheable["rag_top_k"] = params.get("rag_top_k", 6)
        cacheable["rag_max_chars"] = params.get("rag_max_chars", 4000)
        # Sort PDF filenames for deterministic key
        cacheable["pdf_files"] = sorted(params.get("pdf_input_paths", []))
        
        # If direct RAG context provided, hash it
        if params.get("rag_context"):
            cacheable["rag_context_hash"] = hashlib.sha256(
                params["rag_context"].encode()
            ).hexdigest()[:16]
    
    # Create deterministic JSON string (sorted keys)
    cache_string = json.dumps(cacheable, sort_keys=True)
    
    # Generate SHA256 hash
    return hashlib.sha256(cache_string.encode()).hexdigest()
