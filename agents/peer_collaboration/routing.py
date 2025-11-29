# agents/peer_collaboration/routing.py

from fastapi import APIRouter, HTTPException
from .analysis import analyze_discussion
from .suggestions import generate_suggestions

router = APIRouter()

@router.post("/analyze")
async def analyze_collaboration(request: dict):
    try:
        result = analyze_discussion(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
