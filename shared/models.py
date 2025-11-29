from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Any
from datetime import datetime

class User(BaseModel):
    id: str
    name: str
    email: str
    avatar: Optional[str] = None

class Agent(BaseModel):
    id: str
    name: str
    url: str
    description: Optional[str]
    capabilities: List[str] = []
    status: str = "unknown"

class Message(BaseModel):
    type: Literal['user','agent','error']
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class RequestPayload(BaseModel):
    model_config = {"extra": "allow"}  # Allow extra fields to be passed through
    
    agentId: str
    request: str
    priority: int = 1
    modelOverride: Optional[str] = None
    autoRoute: bool = False

class ErrorInfo(BaseModel):
    code: Optional[str] = None
    message: Optional[str] = None
    details: Optional[str] = None

class RequestResponseMetadata(BaseModel):
    executionTime: float  # ms
    agentTrace: List[str] = []
    participatingAgents: List[str] = []
    cached: bool = False

class RequestResponse(BaseModel):
    response: Optional[Any] = None
    agentId: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[RequestResponseMetadata] = None
    error: Optional[ErrorInfo] = None

# Internal Protocol Models
class Task(BaseModel):
    name: str
    parameters: dict

class TaskEnvelope(BaseModel):
    message_id: str
    sender: str
    recipient: str
    type: str = "task_assignment"
    task: Task
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class CompletionReport(BaseModel):
    message_id: str
    sender: str
    recipient: str
    type: str = "completion_report"
    related_message_id: str
    status: Literal["SUCCESS", "FAILURE"]
    results: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)
