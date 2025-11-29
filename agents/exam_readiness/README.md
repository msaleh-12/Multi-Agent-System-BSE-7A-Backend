# Exam Readiness Agent - Integration Guide

## Overview

The Exam Readiness Agent is a specialized AI agent that generates educational assessments (quizzes, exams, assignments) with support for multiple question types, RAG-based content retrieval, PDF export, and intelligent caching.

**Agent ID**: `exam-readiness-agent`  
**Default Port**: `8003`  
**Supervisor Port**: `8000`

## Features

- ✅ **Multiple Assessment Types**: Quiz, Exam, Assignment
- ✅ **Question Types**: MCQ, Short Text, Essay, Coding, Math
- ✅ **RAG Support**: Load PDFs and generate context-aware questions
- ✅ **PDF Export**: Export assessments as formatted PDFs
- ✅ **LTM Caching**: Cache assessments for faster repeated requests
- ✅ **Difficulty Levels**: Easy, Medium, Hard
- ✅ **LaTeX Support**: Mathematical notation in questions

---

## Quick Start

### 1. Start the Agent

```bash
./run_assessment.sh
```

The agent will be available at `http://localhost:8003`

### 2. Start the Supervisor

```bash
./run_supervisor.sh
```

The supervisor will be available at `http://localhost:8000`

---

## API Integration via Supervisor

### Authentication

All requests through the supervisor require authentication.

**Login Request:**

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

**Response:**

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "1",
    "name": "Test User",
    "email": "test@example.com"
  }
}
```

Save the `token` for subsequent requests.

---

## Assessment Generation Examples

### Example 1: Basic Quiz Generation

**Request:**

```bash
curl -X POST http://localhost:8000/api/supervisor/request \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "agentId": "exam-readiness-agent",
    "request": "Generate a Python quiz",
    "subject": "Python Programming",
    "assessment_type": "quiz",
    "difficulty": "easy",
    "question_count": 3,
    "type_counts": {
      "mcq": 2,
      "short_text": 1
    }
  }'
```

**Input Parameters:**

- `agentId` (required): `"exam-readiness-agent"`
- `request` (required): Natural language description
- `subject` (required): Subject/topic of the assessment
- `assessment_type` (required): `"quiz"`, `"exam"`, or `"assignment"`
- `difficulty` (required): `"easy"`, `"medium"`, or `"hard"`
- `question_count` (required): Total number of questions (integer)
- `type_counts` (required): Object mapping question types to counts
  - Valid types: `mcq`, `short_text`, `essay`, `coding`, `math`
  - Sum of type_counts must equal question_count

**Expected Response:**

```json
{
  "response": {
    "title": "Python Programming — Quiz (Easy)",
    "description": "Auto-generated quiz (easy) for Python Programming",
    "assessment_type": "quiz",
    "subject": "Python Programming",
    "difficulty": "easy",
    "total_questions": 3,
    "questions": [
      {
        "question_id": "7b51bf42-3195-47ac-b13b-b99da43589e4",
        "question_text": "What is the correct way to create a list in Python?",
        "question_type": "mcq",
        "options": ["list = []", "list = {}", "list = ()", "list = <>"],
        "correct_answer": "list = []",
        "explanation": "Square brackets [] are used to create lists in Python."
      },
      {
        "question_id": "8c62cg53-4206-58bd-c24c-c00eb54690f5",
        "question_text": "What keyword is used to define a function in Python?",
        "question_type": "mcq",
        "options": ["function", "def", "func", "define"],
        "correct_answer": "def",
        "explanation": "The 'def' keyword is used to define functions in Python."
      },
      {
        "question_id": "9d73dh64-5317-69ce-d35d-d11fc65701g6",
        "question_text": "Explain the difference between a list and a tuple in Python.",
        "question_type": "short_text",
        "options": [],
        "correct_answer": "Lists are mutable (can be modified) while tuples are immutable (cannot be modified after creation). Lists use square brackets [] while tuples use parentheses ().",
        "expected_keywords": [
          "mutable",
          "immutable",
          "modify",
          "brackets",
          "parentheses"
        ]
      }
    ],
    "created_at": "2025-11-16T18:30:25.123456",
    "metadata": {
      "created_by": "supervisor",
      "allow_latex": true,
      "used_rag": false,
      "type_distribution": {
        "mcq": 2,
        "short_text": 1
      }
    }
  },
  "agentId": "exam-readiness-agent",
  "timestamp": "2025-11-16T18:30:25.654321",
  "metadata": {
    "executionTime": 5234.5,
    "agentTrace": ["exam-readiness-agent"],
    "participatingAgents": ["exam-readiness-agent"],
    "cached": false
  },
  "error": null
}
```

---

### Example 2: Assessment with RAG (PDF Input)

**Prerequisites:**

1. Place PDF files in `agents/exam_readiness/rag_documents/`
2. Example: `python_tutorial.pdf`

**Request:**

```bash
curl -X POST http://localhost:8000/api/supervisor/request \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "agentId": "exam-readiness-agent",
    "request": "Generate quiz using course materials",
    "subject": "Python Programming",
    "assessment_type": "quiz",
    "difficulty": "medium",
    "question_count": 5,
    "type_counts": {
      "mcq": 3,
      "short_text": 2
    },
    "pdf_input_paths": ["python_tutorial.pdf"],
    "use_rag": true,
    "rag_top_k": 6,
    "rag_max_chars": 4000
  }'
```

**Additional Parameters:**

- `pdf_input_paths` (optional): Array of PDF filenames from `rag_documents/`
- `use_rag` (optional): Boolean, enables RAG-based question generation
- `rag_top_k` (optional): Number of relevant chunks to retrieve (default: 6)
- `rag_max_chars` (optional): Max characters from RAG context (default: 4000)

**Expected Response:**

```json
{
  "response": {
    "title": "Python Programming — Quiz (Medium)",
    "description": "Auto-generated quiz (medium) for Python Programming",
    "assessment_type": "quiz",
    "subject": "Python Programming",
    "difficulty": "medium",
    "total_questions": 5,
    "questions": [...],
    "created_at": "2025-11-16T18:35:00.000000",
    "metadata": {
      "created_by": "supervisor",
      "allow_latex": true,
      "used_rag": true,
      "type_distribution": {
        "mcq": 3,
        "short_text": 2
      }
    }
  },
  "agentId": "exam-readiness-agent",
  "timestamp": "2025-11-16T18:35:08.123456",
  "metadata": {
    "executionTime": 8123.4,
    "agentTrace": ["exam-readiness-agent"],
    "participatingAgents": ["exam-readiness-agent"],
    "cached": false
  },
  "error": null
}
```

---

### Example 3: Assessment with PDF Export

**Request:**

```bash
curl -X POST http://localhost:8000/api/supervisor/request \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "agentId": "exam-readiness-agent",
    "request": "Generate and export quiz as PDF",
    "subject": "Data Structures",
    "assessment_type": "exam",
    "difficulty": "hard",
    "question_count": 10,
    "type_counts": {
      "mcq": 5,
      "short_text": 3,
      "essay": 2
    },
    "export_pdf": true,
    "pdf_output_filename": "data_structures_exam.pdf"
  }'
```

**Additional Parameters:**

- `export_pdf` (optional): Boolean, generates PDF file
- `pdf_output_filename` (optional): Custom filename (auto-generated if omitted)

**Expected Response:**

```json
{
  "response": {
    "title": "Data Structures — Exam (Hard)",
    "description": "Auto-generated exam (hard) for Data Structures",
    "assessment_type": "exam",
    "subject": "Data Structures",
    "difficulty": "hard",
    "total_questions": 10,
    "questions": [...],
    "created_at": "2025-11-16T18:40:00.000000",
    "metadata": {
      "created_by": "supervisor",
      "allow_latex": true,
      "used_rag": false,
      "type_distribution": {
        "mcq": 5,
        "short_text": 3,
        "essay": 2
      }
    }
  },
  "agentId": "exam-readiness-agent",
  "timestamp": "2025-11-16T18:40:15.789012",
  "metadata": {
    "executionTime": 15789.0,
    "agentTrace": ["exam-readiness-agent"],
    "participatingAgents": ["exam-readiness-agent"],
    "cached": false,
    "pdf_exported": true,
    "pdf_path": "data_structures_exam.pdf"
  },
  "error": null
}
```

**PDF Location:** `agents/exam_readiness/generated_assessments/data_structures_exam.pdf`

---

### Example 4: Complete Pipeline (RAG + PDF Export)

**Request:**

```bash
curl -X POST http://localhost:8000/api/supervisor/request \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "agentId": "exam-readiness-agent",
    "request": "Generate comprehensive assessment with course materials",
    "subject": "Machine Learning",
    "assessment_type": "assignment",
    "difficulty": "medium",
    "question_count": 8,
    "type_counts": {
      "mcq": 3,
      "short_text": 3,
      "coding": 2
    },
    "pdf_input_paths": ["ml_course_notes.pdf", "ml_exercises.pdf"],
    "use_rag": true,
    "rag_top_k": 10,
    "export_pdf": true,
    "pdf_output_filename": "ml_assignment_week5.pdf"
  }'
```

**Expected Response:**

```json
{
  "response": {
    "title": "Machine Learning — Assignment (Medium)",
    "description": "Auto-generated assignment (medium) for Machine Learning",
    "assessment_type": "assignment",
    "subject": "Machine Learning",
    "difficulty": "medium",
    "total_questions": 8,
    "questions": [...],
    "created_at": "2025-11-16T18:45:00.000000",
    "metadata": {
      "created_by": "supervisor",
      "allow_latex": true,
      "used_rag": true,
      "type_distribution": {
        "mcq": 3,
        "short_text": 3,
        "coding": 2
      }
    }
  },
  "agentId": "exam-readiness-agent",
  "timestamp": "2025-11-16T18:45:20.456789",
  "metadata": {
    "executionTime": 20456.8,
    "agentTrace": ["exam-readiness-agent"],
    "participatingAgents": ["exam-readiness-agent"],
    "cached": false,
    "pdf_exported": true,
    "pdf_path": "ml_assignment_week5.pdf",
    "rag_pdfs_loaded": ["ml_course_notes.pdf", "ml_exercises.pdf"]
  },
  "error": null
}
```

---

## PowerShell Example (Complete Workflow)

```powershell
# Step 1: Login
$response = curl -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{\"email\":\"test@example.com\",\"password\":\"password123\"}' | ConvertFrom-Json

$token = $response.token

# Step 2: Generate assessment
curl -X POST http://localhost:8000/api/supervisor/request `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $token" `
  -d '{\"agentId\":\"exam-readiness-agent\",\"request\":\"Generate Python quiz\",\"subject\":\"Python Programming\",\"assessment_type\":\"quiz\",\"difficulty\":\"easy\",\"question_count\":5,\"type_counts\":{\"mcq\":3,\"short_text\":2}}'
```

---

## Request Parameters Reference

### Required Parameters

| Parameter         | Type    | Description                        | Example                       |
| ----------------- | ------- | ---------------------------------- | ----------------------------- |
| `agentId`         | string  | Must be `"exam-readiness-agent"`   | `"exam-readiness-agent"`      |
| `request`         | string  | Natural language description       | `"Generate a Python quiz"`    |
| `subject`         | string  | Assessment topic/subject           | `"Python Programming"`        |
| `assessment_type` | string  | Type: `quiz`, `exam`, `assignment` | `"quiz"`                      |
| `difficulty`      | string  | Level: `easy`, `medium`, `hard`    | `"medium"`                    |
| `question_count`  | integer | Total number of questions          | `5`                           |
| `type_counts`     | object  | Question type distribution         | `{"mcq": 3, "short_text": 2}` |

### Optional Parameters

| Parameter             | Type    | Default        | Description                         |
| --------------------- | ------- | -------------- | ----------------------------------- |
| `allow_latex`         | boolean | `true`         | Enable LaTeX for math notation      |
| `pdf_input_paths`     | array   | `[]`           | PDF filenames from `rag_documents/` |
| `use_rag`             | boolean | `false`        | Enable RAG-based generation         |
| `rag_top_k`           | integer | `6`            | Number of RAG chunks to retrieve    |
| `rag_max_chars`       | integer | `4000`         | Max characters from RAG context     |
| `export_pdf`          | boolean | `false`        | Generate PDF output                 |
| `pdf_output_filename` | string  | auto           | Custom PDF filename                 |
| `created_by`          | string  | `"supervisor"` | Creator identifier                  |

### Question Types

| Type            | Code         | Description                      |
| --------------- | ------------ | -------------------------------- |
| Multiple Choice | `mcq`        | 4 options, single correct answer |
| Short Text      | `short_text` | Brief written response           |
| Essay           | `essay`      | Long-form written response       |
| Coding          | `coding`     | Programming problem              |
| Math            | `math`       | Mathematical problem (LaTeX)     |

---

## Response Structure

### Success Response

```json
{
  "response": {
    "title": "string",
    "description": "string",
    "assessment_type": "string",
    "subject": "string",
    "difficulty": "string",
    "total_questions": 0,
    "questions": [...],
    "created_at": "ISO 8601 timestamp",
    "metadata": {
      "created_by": "string",
      "allow_latex": true,
      "used_rag": false,
      "type_distribution": {}
    }
  },
  "agentId": "exam-readiness-agent",
  "timestamp": "ISO 8601 timestamp",
  "metadata": {
    "executionTime": 0.0,
    "agentTrace": ["exam-readiness-agent"],
    "participatingAgents": ["exam-readiness-agent"],
    "cached": false,
    "pdf_exported": false,
    "pdf_path": null,
    "rag_pdfs_loaded": []
  },
  "error": null
}
```

### Error Response

```json
{
  "response": null,
  "agentId": "exam-readiness-agent",
  "timestamp": "2025-11-16T18:50:00.000000",
  "metadata": null,
  "error": {
    "code": "AGENT_EXECUTION_ERROR",
    "message": "Missing required parameters: subject, question_count",
    "details": null
  }
}
```

### Common Error Codes

| Code                    | Description              |
| ----------------------- | ------------------------ |
| `AGENT_NOT_FOUND`       | Agent ID not in registry |
| `AGENT_UNAVAILABLE`     | Agent is offline         |
| `AGENT_EXECUTION_ERROR` | Agent processing failed  |
| `COMMUNICATION_ERROR`   | Network/timeout error    |

---

## LTM Caching

The agent automatically caches generated assessments for improved performance.

### Cache Behavior

- **Cache Key**: Based on subject, assessment_type, difficulty, question_count, type_counts, RAG parameters
- **Cache Hit**: Returns cached assessment in ~100-500ms (90-98% faster)
- **Cache Miss**: Generates new assessment and saves to cache
- **Cached Flag**: `metadata.cached: true` indicates cache hit

### Cache Management

**Get Cache Statistics:**

```bash
curl http://localhost:8003/cache/stats
```

**Response:**

```json
{
  "total_cached": 15,
  "database_size_bytes": 234567,
  "oldest_entry": "2025-11-15T10:00:00",
  "newest_entry": "2025-11-16T18:50:00"
}
```

**Clear Cache:**

```bash
curl -X DELETE http://localhost:8003/cache/clear
```

---

## Direct Agent Access (Bypass Supervisor)

For testing or direct integration, you can call the agent directly.

**Endpoint:** `POST http://localhost:8003/process`

**Request Body (TaskEnvelope format):**

```json
{
  "message_id": "test-123",
  "sender": "test-client",
  "recipient": "exam-readiness-agent",
  "type": "task_assignment",
  "task": {
    "name": "process_request",
    "parameters": {
      "agentId": "exam-readiness-agent",
      "request": "Generate quiz",
      "subject": "Python Programming",
      "assessment_type": "quiz",
      "difficulty": "easy",
      "question_count": 3,
      "type_counts": { "mcq": 3 }
    }
  },
  "timestamp": "2025-11-16T18:00:00.000000"
}
```

**Response (CompletionReport format):**

```json
{
  "message_id": "response-456",
  "sender": "AssessmentGenerationAgent",
  "recipient": "test-client",
  "type": "completion_report",
  "related_message_id": "test-123",
  "status": "SUCCESS",
  "results": {
    "output": {...},
    "cached": false,
    "pdf_exported": false
  },
  "timestamp": "2025-11-16T18:00:05.000000"
}
```

---

## Health Check

**Request:**

```bash
curl http://localhost:8003/health
```

**Response:**

```json
{
  "status": "healthy",
  "agent_type": "exam readiness",
  "capabilities": [
    "quiz",
    "assignment",
    "examination",
    "rag",
    "pdf_export",
    "ltm_cache"
  ],
  "rag_documents_loaded": 0,
  "cache_stats": {
    "total_cached": 15,
    "database_size_bytes": 234567
  }
}
```

---

## Troubleshooting

### Common Issues

**1. "Missing required parameters" Error**

- Ensure all required fields are present: subject, assessment_type, difficulty, question_count, type_counts
- Verify `type_counts` sum equals `question_count`

**2. "PDF file not found" Error**

- Check that PDF files exist in `agents/exam_readiness/rag_documents/`
- Use only the filename in `pdf_input_paths`, not the full path

**3. "Agent unavailable" Error**

- Verify agent is running: `curl http://localhost:8003/health`
- Check supervisor can reach agent (port 8003)

**4. Timeout Error**

- Large assessments take longer (5-30 seconds)
- RAG processing adds overhead
- Consider increasing supervisor timeout in `supervisor/worker_client.py`

**5. Cache Not Working**

- Check database was created: `agents/exam_readiness/ltm_assessment.db`
- Verify cache stats: `curl http://localhost:8003/cache/stats`
- Check logs for LTM initialization errors

### Debug Logging

Enable debug logging by setting environment variable:

```bash
export LOG_LEVEL=DEBUG
./run_assessment.sh
```

---

## Testing

### Run Integration Tests

```bash
cd agents/exam_readiness/tests
python test_exam_readiness.py
```

### Run Cache Tests

```bash
cd agents/exam_readiness/tests
python test_ltm_caching.py
```

---

## File Locations

| Type           | Location                                       |
| -------------- | ---------------------------------------------- |
| RAG Input PDFs | `agents/exam_readiness/rag_documents/`         |
| Generated PDFs | `agents/exam_readiness/generated_assessments/` |
| Cache Database | `agents/exam_readiness/ltm_assessment.db`      |
| Logs           | Console output                                 |

---

## Support

For issues or questions:

1. Check agent health: `curl http://localhost:8003/health`
2. Review logs in terminal
3. Run integration tests to verify setup
4. Check supervisor connectivity

---

## Version

**Agent Version**: 1.0.0  
**API Protocol**: TaskEnvelope/CompletionReport  
**Last Updated**: November 16, 2025
