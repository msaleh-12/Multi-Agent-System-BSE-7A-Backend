from pydantic import BaseModel
from typing import List, Dict

# --- Input Models ---

class SubjectDetail(BaseModel):
    """Details for a single subject."""
    name: str
    difficulty: str  # e.g., "high", "medium", "low"

class Availability(BaseModel):
    """User's weekly availability and study limits."""
    preferred_days: List[str]
    preferred_times: List[str]  # e.g., ["6:00 PM", "9:00 PM"]
    daily_study_limit_hours: int

class Deadline(BaseModel):
    """Exam or major deadline for a subject."""
    subject: str
    exam_date: str  # ISO date format: "YYYY-MM-DD"

class PerformanceFeedback(BaseModel):
    """Current performance status for subjects. Uses abbreviations (AI, OS, SPM)."""
    AI: str  # e.g., "weak", "average", "strong"
    OS: str
    SPM: str

class Context(BaseModel):
    """Contextual information about the request."""
    request_type: str  # Should be "generate_study_schedule"
    priority: str

class AgentInput(BaseModel):
    """The full input contract for the Study Scheduler Agent."""
    student_id: str
    profile: Dict[str, List[SubjectDetail]]
    availability: Availability
    deadlines: List[Deadline]
    performance_feedback: PerformanceFeedback
    context: Context

# --- Output Models ---

class ScheduleSummary(BaseModel):
    """High-level statistics of the generated schedule."""
    total_sessions: int
    total_study_hours: int
    coverage_percentage: str
    next_revision_day: str

class RecommendedSession(BaseModel):
    """A single scheduled study block."""
    day: str
    subject: str
    time: str  # e.g., "6:00 PM - 8:00 PM"

class AdaptiveAction(BaseModel):
    """Pre-defined adaptive rules for the agent."""
    trigger: str
    adjustment: str

class Reminder(BaseModel):
    """Scheduled reminders."""
    type: str
    message: str

class ReportSummary(BaseModel):
    """Overall performance metrics."""
    consistency_score: int
    time_efficiency: str
    performance_trend: str

class AgentOutput(BaseModel):
    """The full output contract from the Study Scheduler Agent."""
    student_id: str
    schedule_summary: ScheduleSummary
    recommended_schedule: List[RecommendedSession]
    adaptive_actions: List[AdaptiveAction]
    reminders: List[Reminder]
    report_summary: ReportSummary

# --- Helper Class for Logic (Non-Pydantic) ---

class SubjectPriority:
    """Helper class for internal sorting logic, not exposed via API."""
    def __init__(self, name: str, priority_score: float):
        self.name = name
        self.priority_score = priority_score