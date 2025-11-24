FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install requirements first to cache dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy only agent code (context is backend root)
COPY agents/adaptive_quiz_master ./agents/adaptive_quiz_master
COPY shared ./shared
COPY config ./config

# Expose port and run uvicorn
EXPOSE 5011
CMD ["python", "-m", "uvicorn", "agents.adaptive_quiz_master.app:app", "--host", "0.0.0.0", "--port", "5011"]
