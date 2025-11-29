FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install lightweight requirements (no PyTorch needed - uses Groq API)
COPY agents/concept_reinforcement_agent/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy only agent code (context is backend root)
COPY agents/concept_reinforcement_agent ./agents/concept_reinforcement_agent
COPY shared ./shared
COPY config ./config

# Create LTM directory
RUN mkdir -p /app/LTM

# Expose port and run uvicorn
EXPOSE 5015
CMD ["python", "-m", "uvicorn", "agents.concept_reinforcement_agent.app:app", "--host", "0.0.0.0", "--port", "5015"]
