# Quick Start Guide

## Installation & Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the server:**
   ```bash
   python run.py
   ```
   Or using uvicorn directly:
   ```bash
   uvicorn app.main:app --reload
   ```

3. **Access the API:**
   - API Base URL: `http://localhost:8000`
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

## Testing the API

### Option 1: Using the test script
```bash
python test_api.py
```

### Option 2: Using curl

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Process Text (Main Endpoint):**
```bash
curl -X POST "http://localhost:8000/api/v1/process-text" \
  -H "Content-Type: application/json" \
  -d @example_request.json
```

### Option 3: Using Python requests

```python
import requests
import json

# Load example request
with open("example_request.json", "r") as f:
    data = json.load(f)

# Send request
response = requests.post(
    "http://localhost:8000/api/v1/process-text",
    json=data
)

print(json.dumps(response.json(), indent=2))
```

## First Run Notes

- **Model Downloads**: On first run, the application will download:
  - SentenceTransformer model (`all-MiniLM-L6-v2`) - ~80MB
  - T5 Paraphrase model (`Vamsi/T5_Paraphrase_Paws`) - ~500MB
  
  This may take several minutes depending on your internet connection.

- **NLTK Data**: The application will automatically download required NLTK tokenizer data.

- **MongoDB**: The application works without MongoDB, but won't store submission history. To enable:
  - Install MongoDB locally or use MongoDB Atlas
  - Set environment variables (see README.md)

## Expected Response Format

When you call `/api/v1/process-text`, you'll receive:

```json
{
  "student_id": "STU001",
  "submission_id": "SUB001",
  "output": {
    "rephrased_text": [
      {
        "original_sentence": "Original sentence here",
        "rephrased_sentence": "Rephrased version here",
        "similarity_score": 0.75
      }
    ],
    "pledge_percentage": 65.5,
    "feedback": "Good originality. Some sentences may benefit from rephrasing..."
  },
  "timestamp": "2024-01-15T10:30:05.123456"
}
```

## Troubleshooting

- **Port already in use**: Change the port in `run.py` or use `--port` flag with uvicorn
- **Model download fails**: Check internet connection, models are downloaded from Hugging Face
- **Memory errors**: The T5 model requires ~2GB RAM. Consider using a smaller model or GPU
- **Import errors**: Make sure all dependencies are installed: `pip install -r requirements.txt`

