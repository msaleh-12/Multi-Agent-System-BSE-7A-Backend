FROM python:3.11-slim
WORKDIR /app

# Install requirements
COPY agents/peer_collaboration/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Download TextBlob corpora
RUN python -m textblob.download_corpora

# Copy agent code
COPY agents/peer_collaboration ./agents/peer_collaboration
COPY shared ./shared

# Set Python path to find shared modules
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5017

CMD ["uvicorn", "agents.peer_collaboration.app:app", "--host", "0.0.0.0", "--port", "5017"]
