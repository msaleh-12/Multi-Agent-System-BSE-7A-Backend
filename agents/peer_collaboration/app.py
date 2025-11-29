# agents/peer_collaboration/app.py

from fastapi import FastAPI, Request, HTTPException
from datetime import datetime, timezone
import uuid
import sys
import re

# Add path for shared modules
sys.path.insert(0, '/app')

from .routing import router
from .analysis import analyze_discussion

app = FastAPI(title="Peer Collaboration Agent API")
app.include_router(router)


def normalize_discussion_logs(logs):
    """
    Normalize discussion logs to the expected format:
    [{"user_id": "name", "timestamp": "...", "message": "..."}]
    
    Handles various input formats:
    - Already normalized list of dicts
    - List of strings like "Alice (2025-11-29 10:00): message"
    - Raw text with multiple messages
    """
    if not logs:
        return []
    
    normalized = []
    
    for log in logs:
        if isinstance(log, dict):
            # Already a dict, ensure it has required keys
            normalized.append({
                "user_id": log.get("user_id", log.get("name", log.get("sender", "Unknown"))),
                "timestamp": log.get("timestamp", log.get("time", "")),
                "message": log.get("message", log.get("content", log.get("text", "")))
            })
        elif isinstance(log, str):
            # Try to parse string format like "Alice (2025-11-29 10:00): message"
            # Or "- Alice (timestamp): message"
            pattern = r'^-?\s*(\w+)\s*\(([^)]+)\):\s*["\']?(.+?)["\']?$'
            match = re.match(pattern, log.strip())
            if match:
                normalized.append({
                    "user_id": match.group(1),
                    "timestamp": match.group(2),
                    "message": match.group(3)
                })
            else:
                # Fallback: treat entire string as message from unknown user
                normalized.append({
                    "user_id": "Unknown",
                    "timestamp": "",
                    "message": log
                })
    
    return normalized


def normalize_team_members(members):
    """
    Normalize team members to a list of strings.
    """
    if not members:
        return []
    
    if isinstance(members, str):
        # Split by comma, semicolon, or "and"
        parts = re.split(r'[,;]|\band\b', members)
        return [m.strip() for m in parts if m.strip()]
    
    if isinstance(members, list):
        result = []
        for m in members:
            if isinstance(m, str):
                result.append(m.strip())
            elif isinstance(m, dict):
                result.append(m.get("name", m.get("user_id", str(m))))
        return result
    
    return []


@app.get("/")
async def root():
    return {"message": "Peer Collaboration Agent is running"}


@app.get("/health")
async def health():
    """Health check endpoint - REQUIRED for supervisor integration."""
    return {
        "status": "healthy",
        "agent": "peer_collaboration_agent",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/process")
async def process_task(request: Request):
    """
    Main processing endpoint for supervisor integration.
    Accepts TaskEnvelope format and processes collaboration analysis requests.
    """
    try:
        body = await request.json()
        
        # Extract task parameters from TaskEnvelope format
        task_params = body.get("task", {}).get("parameters", {})
        
        # Support both structured and simple formats
        if "agent_name" in task_params and "intent" in task_params and "payload" in task_params:
            # Structured format
            payload = task_params["payload"]
            project_id = payload.get("project_id", "default_project")
            team_members = payload.get("team_members", [])
            discussion_logs = payload.get("discussion_logs", [])
            action = payload.get("action", "analyze")
        else:
            # Simple format - extract from params
            project_id = task_params.get("project_id", "default_project")
            team_members = task_params.get("team_members", [])
            discussion_logs = task_params.get("discussion_logs", [])
            action = task_params.get("action", "analyze")
        
        # Normalize inputs to expected format
        team_members = normalize_team_members(team_members)
        discussion_logs = normalize_discussion_logs(discussion_logs)
        
        # Build the request for analysis
        analysis_request = {
            "project_id": project_id,
            "team_members": team_members,
            "action": action,
            "content": {
                "discussion_logs": discussion_logs
            }
        }
        
        # Perform the analysis
        result = analyze_discussion(analysis_request)
        
        # Return in CompletionReport format
        return {
            "message_id": str(uuid.uuid4()),
            "sender": "peer_collaboration_agent",
            "recipient": body.get("sender", "supervisor"),
            "related_message_id": body.get("message_id", ""),
            "status": "SUCCESS",
            "results": result
        }
        
    except Exception as e:
        import traceback
        return {
            "message_id": str(uuid.uuid4()),
            "sender": "peer_collaboration_agent",
            "recipient": body.get("sender", "supervisor") if 'body' in dir() else "supervisor",
            "related_message_id": body.get("message_id", "") if 'body' in dir() else "",
            "status": "FAILURE",
            "results": {"error": str(e), "traceback": traceback.format_exc()}
        }
