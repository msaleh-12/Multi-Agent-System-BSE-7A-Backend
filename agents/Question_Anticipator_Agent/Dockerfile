FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY agents/Question_Anticipator_Agent/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install CPU-only PyTorch first (prevents GPU dependencies ~2GB savings)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install additional dependencies for Gemini (sentence-transformers will use CPU torch)
RUN pip install --no-cache-dir google-generativeai langchain-anthropic sentence-transformers

# Copy agent code
COPY agents/Question_Anticipator_Agent ./agents/Question_Anticipator_Agent

# Copy shared models
COPY shared ./shared

# Set Python path
ENV PYTHONPATH=/app:/app/agents/Question_Anticipator_Agent

# Expose port
EXPOSE 5022

# Run the application
CMD ["uvicorn", "agents.Question_Anticipator_Agent.question_anticipator:app", "--host", "0.0.0.0", "--port", "5022"]
