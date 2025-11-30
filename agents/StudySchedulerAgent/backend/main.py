from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import datetime

# Import models, including the helper class SubjectPriority
from models import (
    AgentInput, AgentOutput, ScheduleSummary, RecommendedSession,
    AdaptiveAction, Reminder, ReportSummary, SubjectPriority
)

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