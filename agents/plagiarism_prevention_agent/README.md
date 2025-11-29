# Plagiarism Prevention Agent (PPA)

An AI-powered agent that detects plagiarism in student submissions and provides rephrased versions to improve originality while preserving meaning.

## Features

- **Similarity Detection**: Uses SentenceTransformers to detect similarity between texts
- **Rephrasing Engine**: Leverages T5 transformer model for sentence-by-sentence paraphrasing
- **Pledge Percentage**: Calculates originality score (0-100%) for submissions
- **RESTful API**: FastAPI-based endpoints for integration with Supervisor Agent
- **Database Integration**: MongoDB support for storing submissions and results

## Tech Stack

- **Backend**: FastAPI
- **NLP Models**: 
  - SentenceTransformers (`all-MiniLM-L6-v2`) for similarity detection
  - T5 (`Vamsi/T5_Paraphrase_Paws`) for rephrasing
- **Database**: MongoDB (optional)
- **Python**: 3.8+

## Installation

1. Clone the repository and navigate to the project directory

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Set up MongoDB:
   - Install MongoDB locally or use MongoDB Atlas
   - Set environment variables:
     ```bash
     export MONGODB_URL="mongodb://localhost:27017/"
     export MONGODB_DB_NAME="plagiarism_agent"
     ```
   - Or create a `.env` file with these variables (see `.env.example` for reference)

## Usage

### Start the API Server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### API Endpoints

#### 1. Health Check
```
GET /health
```

#### 2. Check Similarity
```
POST /api/v1/check-similarity
```

Request body:
```json
{
  "text1": "First text to compare",
  "text2": "Second text to compare (optional)"
}
```

#### 3. Rephrase Text
```
POST /api/v1/rephrase-text
```

Request body:
```json
{
  "text": "Text to rephrase",
  "preserve_meaning": true
}
```

#### 4. Process Text (Main Endpoint)
```
POST /api/v1/process-text
```

Request body:
```json
{
  "student_id": "STU001",
  "input": {
    "student_text": "The text submitted by the student...",
    "submission_id": "SUB001",
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "processing": {
    "comparison_sources": ["synthetic_dataset", "public_dataset"],
    "method": "sentence_by_sentence_rephrasing",
    "preserve_meaning": true,
    "improve_originality": true
  }
}
```

Response:
```json
{
  "student_id": "STU001",
  "submission_id": "SUB001",
  "output": {
    "rephrased_text": [
      {
        "original_sentence": "Original sentence",
        "rephrased_sentence": "Rephrased version",
        "similarity_score": 0.75
      }
    ],
    "pledge_percentage": 65.5,
    "feedback": "Good originality. Some sentences may benefit from rephrasing..."
  },
  "timestamp": "2024-01-15T10:30:05Z"
}
```

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
project/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── models/
│   │   └── schemas.py          # Pydantic models for request/response
│   ├── services/
│   │   ├── similarity_detector.py    # Similarity detection module
│   │   ├── rephrasing_engine.py      # Rephrasing engine module
│   │   └── plagiarism_processor.py   # Orchestration module
│   ├── routers/
│   │   ├── similarity.py       # Similarity detection endpoints
│   │   ├── rephrase.py         # Rephrasing endpoints
│   │   └── process.py          # Main processing endpoint
│   └── database/
│       ├── connection.py       # MongoDB connection
│       └── models.py           # Database models
├── requirements.txt
└── README.md
```

## How It Works

1. **Similarity Detection**: 
   - Text is split into sentences
   - Each sentence is compared against reference datasets using cosine similarity
   - Sentences with similarity > threshold (0.80) are flagged

2. **Rephrasing**:
   - Flagged sentences (or all sentences if `improve_originality=true`) are rephrased using T5 model
   - Original meaning is preserved during rephrasing

3. **Pledge Percentage**:
   - Calculated as: `(1 - average_similarity) * 100`
   - Higher percentage = more original content

## Configuration

Default settings can be modified in:
- `app/services/similarity_detector.py`: Similarity threshold, model name
- `app/services/rephrasing_engine.py`: Rephrasing model name
- `app/services/plagiarism_processor.py`: Overall processing configuration

## Notes

- First run will download NLP models (may take a few minutes)
- GPU is recommended for faster processing but not required
- MongoDB is optional; the agent works without it but won't store history

## License

MIT License

