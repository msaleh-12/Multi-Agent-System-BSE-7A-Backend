FROM python:3.11-slim
WORKDIR /app

# Copy requirements and install dependencies
COPY agents/StudySchedulerAgent/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agents/StudySchedulerAgent/backend ./agents/StudySchedulerAgent/backend

# Copy shared models for TaskEnvelope/CompletionReport
COPY shared ./shared

# Set Python path to find shared modules and local models
ENV PYTHONPATH=/app:/app/agents/StudySchedulerAgent/backend

# Expose port
EXPOSE 5023

# Run the application
CMD ["uvicorn", "agents.StudySchedulerAgent.backend.main:app", "--host", "0.0.0.0", "--port", "5023"]
