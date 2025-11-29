FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install agent-specific requirements (lightweight - no PyTorch)
COPY agents/research_scout_agent/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy only agent code (context is backend root)
COPY agents/research_scout_agent ./agents/research_scout_agent
COPY shared ./shared

# Expose port and run uvicorn
EXPOSE 5014
CMD ["python", "-m", "uvicorn", "agents.research_scout_agent.app:app", "--host", "0.0.0.0", "--port", "5014"]
