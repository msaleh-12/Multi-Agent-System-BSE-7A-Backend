from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class AssessmentType(str, Enum):
    QUIZ = "quiz"
    EXAM = "exam"
    ASSIGNMENT = "assignment"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionType(str, Enum):
    MCQ = "mcq"
    SHORT_TEXT = "short_text"
    ESSAY = "essay"
    CODING = "coding"
    MATH = "math"


class AssessmentGenerationRequest(BaseModel):
    subject: str = Field(..., description="Subject or topic for the assessment")
    assessment_type: AssessmentType = Field(..., description="Type of assessment")
    difficulty: Difficulty = Field(..., description="Overall difficulty level")
    question_count: int = Field(..., ge=1, description="Total number of questions")
    type_counts: Dict[str, int] = Field(
        ..., 
        description="Distribution of question types, e.g., {'mcq': 5, 'essay': 2}"
    )
    created_by: str = Field(default="api", description="Creator identifier")
    allow_latex: bool = Field(default=True, description="Allow LaTeX notation for math")
    rag_context: Optional[str] = Field(None, description="Additional RAG context")
    pdf_paths: Optional[List[str]] = Field(None, description="Paths to PDFs for RAG")
    rag_top_k: int = Field(default=6, description="Number of RAG results to retrieve")
    rag_max_chars: int = Field(default=4000, description="Maximum characters from RAG context")


class QuestionResponse(BaseModel):
    question_id: str
    question_text: str
    question_type: str
    options: List[str]
    correct_answer: str
    expected_keywords: List[str] = []
    marks: int
    difficulty: Optional[str]
    metadata: Dict[str, Any] = {}


class AssessmentResponse(BaseModel):
    title: str
    description: str
    assessment_type: str
    subject: str
    difficulty: str
    total_questions: int
    questions: List[QuestionResponse]
    created_at: datetime
    metadata: Dict[str, Any] = {}


class RAGSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=3, ge=1, le=20, description="Number of results to return")


class RAGSearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total_documents: int