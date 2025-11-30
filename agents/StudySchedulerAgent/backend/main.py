from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import datetime
import uuid
import sys
import logging

# Add parent path for shared models when running in Docker
sys.path.insert(0, '/app')

# Import models, including the helper class SubjectPriority
from models import (
    AgentInput, AgentOutput, ScheduleSummary, RecommendedSession,
    AdaptiveAction, Reminder, ReportSummary, SubjectPriority,
    SubjectDetail, Availability, Deadline, PerformanceFeedback, Context
)

# Try to import shared models for supervisor communication
try:
    from shared.models import TaskEnvelope, CompletionReport
except ImportError:
    # Define fallback models if shared module not available
    from pydantic import BaseModel
    
    class TaskEnvelope(BaseModel):
        message_id: str = ""
        sender: str = ""
        task: Any = None
    
    class CompletionReport(BaseModel):
        message_id: str = ""
        sender: str = ""
        recipient: str = ""
        related_message_id: str = ""
        status: str = ""
        results: dict = {}

_logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Study Scheduler Agent API",
    description="Intelligent system for generating and optimizing personalized study schedules."
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Core Agent Logic (The Scheduling Algorithm) ---

def calculate_priority(subject: Dict, performance_feedback: Dict) -> float:
    """Calculates a priority score based on difficulty and performance feedback."""
    difficulty_map = {"high": 3, "medium": 2, "low": 1}
    feedback_map = {"weak": 3, "average": 2, "strong": 1}

    # Derive abbreviation key for matching performance feedback (e.g., 'Artificial Intelligence' -> 'AI')
    subject_words = subject['name'].split()
    subject_short = "".join(word[0].upper() for word in subject_words)
    
    # Find the correct feedback key (e.g., 'AI', 'OS', 'SPM')
    feedback_key = ""
    for k in performance_feedback.keys():
        if k.upper() == subject_short.upper():
            feedback_key = k
            break
            
    # Get values, defaulting to 'medium' difficulty and 'average' performance if keys are missing
    feedback_val = feedback_map.get(performance_feedback.get(feedback_key, "average"), 2)
    difficulty_val = difficulty_map.get(subject['difficulty'], 2)
    
    # Priority score: Higher score means more time is needed
    priority = difficulty_val * feedback_val
    return priority

def generate_schedule(data: AgentInput) -> AgentOutput:
    """
    Generates an adaptive study schedule based on user input, deadlines, and performance.
    """
    
    # 1. Subject Prioritization
    # Extract the list of SubjectDetail models from the 'subjects' key in the profile dict
    subjects = data.profile.get("subjects", []) 
    priority_list: List[SubjectPriority] = []
    
    for subj in subjects:
        priority = calculate_priority(subj.model_dump(), data.performance_feedback.model_dump())
        priority_list.append(SubjectPriority(name=subj.name, priority_score=priority))

    # FIX: Correctly sorting the list. The error was here.
    priority_list.sort(key=lambda x: x.priority_score, reverse=True)
    
    # 2. Allocate Time and Distribution
    total_hours_per_subject: Dict[str, int] = {}
    total_study_hours = 0
    daily_limit = data.availability.daily_study_limit_hours
    
    # Heuristic: Determine the optimal hours per subject per session
    # High priority subjects (score >= 6) get 2 hours, others get 1 hour.
    allocation_map = {p.name: (2 if p.priority_score >= 6 else 1) for p in priority_list}
    
    # 3. Generate Schedule Entries
    recommended_schedule: List[RecommendedSession] = []
    available_days = data.availability.preferred_days
    time_slots = data.availability.preferred_times
    
    num_days_to_schedule = 7 # Plan for one week
    subject_index = 0
    
    for day_counter in range(num_days_to_schedule):
        # Cycle through preferred days
        if not available_days:
             break # No preferred days, stop scheduling
             
        current_day = available_days[day_counter % len(available_days)] 
        
        hours_scheduled_today = 0
        
        # Try to fill the daily limit (up to 3 hours) using subjects by priority
        for slot_attempt in range(daily_limit):
            if hours_scheduled_today >= daily_limit or not priority_list:
                break
                
            # Cycle through the prioritized list of subjects
            subj_priority = priority_list[subject_index % len(priority_list)]
            subject_name = subj_priority.name
            allocated_time = allocation_map.get(subject_name, 1)

            if hours_scheduled_today + allocated_time <= daily_limit:
                
                # Determine time slot (using the first preferred time as a start point for simplicity)
                start_time_str = time_slots[0] if time_slots else "6:00 PM"
                
                try:
                    start_dt = datetime.datetime.strptime(start_time_str, "%I:%M %p")
                    end_dt = start_dt + datetime.timedelta(hours=allocated_time)
                    end_time_str = end_dt.strftime("%I:%M %p")
                except ValueError:
                    end_time_str = f"{6 + allocated_time}:00 PM"

                time_range = f"{start_time_str} - {end_time_str}"
                
                recommended_schedule.append(RecommendedSession(
                    day=current_day,
                    subject=subject_name,
                    time=time_range
                ))
                hours_scheduled_today += allocated_time
                total_study_hours += allocated_time

            subject_index += 1 # Move to the next subject for the next available slot attempt

        day_counter += 1

    # 4. Compile Output Summary (Using example data when complex calculation is omitted)
    total_sessions = len(recommended_schedule)
    coverage_percentage = "90%" 
    next_revision_day = recommended_schedule[0].day if recommended_schedule else "N/A"

    schedule_summary = ScheduleSummary(
        total_sessions=total_sessions,
        total_study_hours=total_study_hours,
        coverage_percentage=coverage_percentage,
        next_revision_day=next_revision_day
    )
    
    # Static output components required by the contract
    adaptive_actions = [
        AdaptiveAction(trigger="missed_session", adjustment="reschedule to next available slot"),
        AdaptiveAction(trigger="performance_drop", adjustment="increase study frequency for weak subjects"),
    ]
    
    reminders = [
        Reminder(type="daily", message="Study session starts at 6:00 PM!"),
        Reminder(type="weekly_summary", message="You completed 80% of your planned study hours this week!"),
    ]
    
    report_summary = ReportSummary(
        consistency_score=88,
        time_efficiency="High",
        performance_trend="Improving"
    )

    return AgentOutput(
        student_id=data.student_id,
        schedule_summary=schedule_summary,
        recommended_schedule=recommended_schedule,
        adaptive_actions=adaptive_actions,
        reminders=reminders,
        report_summary=report_summary
    )


# --- FastAPI Endpoint ---

@app.post("/generate_schedule/", response_model=AgentOutput)
async def handle_schedule_request(data: AgentInput):
    """
    Receives the AgentInput payload from the Supervisor Agent,
    generates an optimal study schedule, and returns the AgentOutput.
    """
    if data.context.request_type != "generate_study_schedule":
        raise HTTPException(
            status_code=400,
            detail="Invalid request_type. Must be 'generate_study_schedule'."
        )
    
    try:
        output = generate_schedule(data)
        return output
    except Exception as e:
        print(f"Error during schedule generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An internal error occurred during scheduling: {e}"
        )


@app.get("/health/")
def health_check():
    """Simple health check endpoint for the Supervisor Agent."""
    return {"status": "ok", "agent_name": "Study Scheduler Agent"}


@app.get("/health")
def health_check_no_slash():
    """Health check endpoint without trailing slash."""
    return {
        "status": "healthy",
        "agent_name": "study_scheduler_agent",
        "version": "1.0.0",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }


@app.post("/process", response_model=CompletionReport)
async def process_task(request: Request):
    """
    Main processing endpoint for supervisor TaskEnvelope format.
    Handles structured format from supervisor/orchestrator.
    """
    try:
        body = await request.json()
        _logger.info(f"Received process request: {body}")
        
        # Try to parse as TaskEnvelope
        try:
            task_envelope = TaskEnvelope(**body)
            task_params = task_envelope.task.parameters if hasattr(task_envelope.task, 'parameters') else {}
        except Exception:
            # If not TaskEnvelope format, use body directly as parameters
            task_params = body
            task_envelope = None
        
        # Extract parameters from structured or simple format
        if "agent_name" in task_params and "intent" in task_params and "payload" in task_params:
            # Structured format from orchestrator
            payload = task_params["payload"]
        else:
            # Simple format - use task_params directly
            payload = task_params
        
        # Build AgentInput from payload
        agent_input = _build_agent_input_from_payload(payload)
        
        # Generate schedule
        output = generate_schedule(agent_input)
        
        # Convert output to response format
        result_data = {
            "student_id": output.student_id,
            "schedule_summary": output.schedule_summary.model_dump(),
            "recommended_schedule": [s.model_dump() for s in output.recommended_schedule],
            "adaptive_actions": [a.model_dump() for a in output.adaptive_actions],
            "reminders": [r.model_dump() for r in output.reminders],
            "report_summary": output.report_summary.model_dump()
        }
        
        # Build response message
        response_message = _build_response_message(output)
        
        return CompletionReport(
            message_id=str(uuid.uuid4()),
            sender="study_scheduler_agent",
            recipient=task_envelope.sender if task_envelope else "supervisor",
            related_message_id=task_envelope.message_id if task_envelope else "",
            status="SUCCESS",
            results={
                "response": response_message,
                "schedule_data": result_data
            }
        )
        
    except Exception as e:
        _logger.error(f"Error processing request: {e}", exc_info=True)
        return CompletionReport(
            message_id=str(uuid.uuid4()),
            sender="study_scheduler_agent",
            recipient="supervisor",
            related_message_id="",
            status="ERROR",
            results={"error": str(e)}
        )


def _build_agent_input_from_payload(payload: Dict[str, Any]) -> AgentInput:
    """Convert supervisor payload to AgentInput format."""
    
    # Extract subjects from payload
    subjects_data = payload.get("subjects", [])
    if isinstance(subjects_data, list):
        subjects = [
            SubjectDetail(
                name=s.get("name", s) if isinstance(s, dict) else str(s),
                difficulty=s.get("difficulty", "medium") if isinstance(s, dict) else "medium"
            ) for s in subjects_data
        ]
    else:
        subjects = []
    
    # Extract availability
    availability_data = payload.get("availability", {})
    availability = Availability(
        preferred_days=availability_data.get("preferred_days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]),
        preferred_times=availability_data.get("preferred_times", ["6:00 PM"]),
        daily_study_limit_hours=availability_data.get("daily_study_limit_hours", 3)
    )
    
    # Extract deadlines
    deadlines_data = payload.get("deadlines", [])
    deadlines = [
        Deadline(
            subject=d.get("subject", "General"),
            exam_date=d.get("exam_date", d.get("date", "2025-12-31"))
        ) for d in deadlines_data
    ] if deadlines_data else []
    
    # Extract performance feedback with defaults
    perf_data = payload.get("performance_feedback", {})
    performance_feedback = PerformanceFeedback(
        AI=perf_data.get("AI", "average"),
        OS=perf_data.get("OS", "average"),
        SPM=perf_data.get("SPM", "average")
    )
    
    # Context
    context = Context(
        request_type="generate_study_schedule",
        priority=payload.get("priority", "normal")
    )
    
    return AgentInput(
        student_id=payload.get("student_id", "default_student"),
        profile={"subjects": subjects},
        availability=availability,
        deadlines=deadlines,
        performance_feedback=performance_feedback,
        context=context
    )


def _build_response_message(output: AgentOutput) -> str:
    """Build a human-readable response message from the schedule output."""
    message = f"📅 **Study Schedule Created for Student {output.student_id}**\n\n"
    
    summary = output.schedule_summary
    message += f"**Summary:**\n"
    message += f"- Total Sessions: {summary.total_sessions}\n"
    message += f"- Total Study Hours: {summary.total_study_hours}\n"
    message += f"- Coverage: {summary.coverage_percentage}\n"
    message += f"- Next Revision: {summary.next_revision_day}\n\n"
    
    message += f"**Recommended Schedule:**\n"
    for session in output.recommended_schedule:
        message += f"- {session.day}: {session.subject} ({session.time})\n"
    
    message += f"\n**Reminders:**\n"
    for reminder in output.reminders:
        message += f"- [{reminder.type}] {reminder.message}\n"
    
    report = output.report_summary
    message += f"\n**Performance Report:**\n"
    message += f"- Consistency Score: {report.consistency_score}%\n"
    message += f"- Time Efficiency: {report.time_efficiency}\n"
    message += f"- Performance Trend: {report.performance_trend}\n"
    
    return message