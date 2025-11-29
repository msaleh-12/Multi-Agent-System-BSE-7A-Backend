# agents/peer_collaboration/models.py

from pydantic import BaseModel
from typing import List, Dict, Any

class DiscussionLog(BaseModel):
    user_id: str
    timestamp: str
    message: str

class CollaborationRequest(BaseModel):
    project_id: str
    team_members: List[str]
    action: str
    content: Dict[str, Any]
