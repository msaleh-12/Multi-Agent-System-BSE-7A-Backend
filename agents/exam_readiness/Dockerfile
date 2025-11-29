FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first to avoid CUDA downloads
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install requirements
COPY agents/exam_readiness/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agents/exam_readiness ./agents/exam_readiness
COPY shared ./shared

# Set Python path to find shared modules
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5024

CMD ["uvicorn", "agents.exam_readiness.app:app", "--host", "0.0.0.0", "--port", "5024"]
