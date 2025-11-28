import logging
import uuid
from fastapi import FastAPI, Request, HTTPException
from datetime import datetime, UTC
from typing import Optional

# Import shared models
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from shared.models import TaskEnvelope, CompletionReport

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

app = FastAPI()

# Import the concept reinforcement logic
from .Concept_reinforcement_agent import ConceptReinforcementAgent

# Initialize the agent
AGENT_ID = "concept_reinforcement_agent"
SUPERVISOR_ID = "supervisor"

try:
    agent = ConceptReinforcementAgent(
        agent_id=AGENT_ID,
        supervisor_id=SUPERVISOR_ID,
        ltm_base_path="/app/LTM"
    )
    _logger.info(f"[{AGENT_ID}] Successfully initialized ConceptReinforcementAgent")
except Exception as e:
    _logger.error(f"[{AGENT_ID}] Failed to initialize agent: {e}")
    agent = None

@app.get('/health')
async def health():
    return {
        "status": "healthy" if agent else "unhealthy",
        "agent": "ConceptReinforcementAgent",
        "version": "1.0.0",
        "timestamp": datetime.now(UTC).isoformat()
    }

@app.post('/process', response_model=CompletionReport)
async def process_task(req: Request):
    """
    Process incoming task requests for concept reinforcement.
    
    Expected input format in task.parameters:
    {
        "agent_name": "concept_reinforcement_agent",
        "intent": "generate_reinforcement_tasks",
        "payload": {
            "student_id": "user_123",
            "weak_topics": ["Python loops", "Functions"],
            "preferences": {
                "learning_style": "visual",
                "max_tasks": 3
            }
        }
    }
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized properly")
    
    try:
        body = await req.json()
        task_envelope = TaskEnvelope(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request body: {e}")

    task_params = task_envelope.task.parameters
    
    _logger.info(f"[{AGENT_ID}] Received task parameters: {task_params}")
    
    # Extract the payload or construct it from parameters
    payload = task_params.get("payload", {})
    
    # If payload is not provided, try to extract from root parameters
    if not payload:
        payload = {
            "student_id": task_params.get("student_id"),
            "weak_topics": task_params.get("weak_topics", []),
            "preferences": task_params.get("preferences", {})
        }
    
    # Validate required fields
    if not payload.get("student_id"):
        return CompletionReport(
            message_id=str(uuid.uuid4()),
            sender=AGENT_ID,
            recipient=task_envelope.sender,
            related_message_id=task_envelope.message_id,
            status="FAILURE",
            results={"error": "Missing 'student_id' in payload"}
        )
    
    if not payload.get("weak_topics"):
        return CompletionReport(
            message_id=str(uuid.uuid4()),
            sender=AGENT_ID,
            recipient=task_envelope.sender,
            related_message_id=task_envelope.message_id,
            status="FAILURE",
            results={"error": "Missing 'weak_topics' in payload"}
        )
    
    # Set default preferences if not provided
    if "preferences" not in payload:
        payload["preferences"] = {}
    if "learning_style" not in payload["preferences"]:
        payload["preferences"]["learning_style"] = "visual"
    if "max_tasks" not in payload["preferences"]:
        payload["preferences"]["max_tasks"] = 3
    
    # Process the task using the agent
    try:
        results = agent.process_task(payload)
        status = "SUCCESS"
        _logger.info(f"[{AGENT_ID}] Task completed successfully")
    except Exception as e:
        results = {"error": str(e), "details": "Task processing failed"}
        status = "FAILURE"
        _logger.error(f"[{AGENT_ID}] Task failed: {e}")
    
    return CompletionReport(
        message_id=str(uuid.uuid4()),
        sender=AGENT_ID,
        recipient=task_envelope.sender,
        related_message_id=task_envelope.message_id,
        status=status,
        results=results
    )
