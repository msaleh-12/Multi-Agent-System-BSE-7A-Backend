from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from enum import Enum
from contextlib import asynccontextmanager
import uvicorn
import os
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
import uuid
import json
import logging
from fastapi import Request

from .services.assessment_service import (
    generate_questions_by_type
)
from .services.rag_service import RAGService
from .services.pdf_service import generate_assessment_pdf
from .models import (
    AssessmentGenerationRequest,
    AssessmentResponse,
    QuestionResponse,
    RAGSearchRequest,
    RAGSearchResponse,
)
from shared.models import TaskEnvelope, CompletionReport
from . import ltm

_logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize LTM database on startup"""
    _logger.info("Initializing Assessment LTM...")
    await ltm.init_db()
    yield
    _logger.info("Shutting down Assessment Agent")

app = FastAPI(
    title="Assessment Generation Agent",
    description="A multi-agent system designed to assist university teachers by automating the generation of assessments (quizzes, assignments, exams). The system uses specialized AI agents to generate MCQs, short questions, and long questions based on the specified structure, difficulty levels",
    version="1.0.0",
    lifespan=lifespan
)

# Global RAG service instance
rag_service = RAGService()

# Get the base directory for exam_readiness agent
BASE_DIR = Path(__file__).parent

# Directory for RAG input PDFs (relative to exam_readiness/)
RAG_DOCUMENTS_DIR = BASE_DIR / "rag_documents"
RAG_DOCUMENTS_DIR.mkdir(exist_ok=True)

# Directory for generated assessment PDFs (relative to exam_readiness/)
GENERATED_ASSESSMENTS_DIR = BASE_DIR / "generated_assessments"
GENERATED_ASSESSMENTS_DIR.mkdir(exist_ok=True)

# Legacy directories for backward compatibility with /upload-pdfs endpoint
UPLOAD_DIR = Path(tempfile.gettempdir()) / "assessment_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

OUTPUT_DIR = Path(tempfile.gettempdir()) / "assessment_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    cache_stats = await ltm.get_stats()
    return {
        "status": "healthy",
        "agent_type": "exam readiness",
        "capabilities": ["quiz", "assignment", "examination", "rag", "pdf_export", "ltm_cache"],
        "rag_documents_loaded": rag_service.get_document_count(),
        "cache_stats": {
            "total_cached": cache_stats.get("total_cached", 0),
            "database_size_bytes": cache_stats.get("database_size_bytes", 0)
        }
    }


@app.post('/process', response_model=CompletionReport)
async def process_task(req: Request):
    """
    Process task from supervisor.
    Accepts TaskEnvelope and returns CompletionReport.
    
    Expected in task.parameters (RequestPayload format):
    {
        "agentId": "assessment-agent",
        "request": "user's natural language request",
        "priority": 1,
        "modelOverride": null,
        "autoRoute": false,
        "subject": "Python Programming",
        "assessment_type": "quiz",
        "difficulty": "easy",
        "question_count": 3,
        "type_counts": {"mcq": 3}
    }
    """
    try:
        body = await req.json()
        task_envelope = TaskEnvelope(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request body: {e}")

    # Extract parameters - supervisor sends RequestPayload in task.parameters
    params = task_envelope.task.parameters
    
    # Extract assessment-specific parameters
    # They can be nested under "assessment_params" or directly in params
    assessment_params = params.get("assessment_params", params)
    
    # Build a clean dict with only assessment parameters
    assessment_data = {
        "subject": assessment_params.get("subject"),
        "assessment_type": assessment_params.get("assessment_type"),
        "difficulty": assessment_params.get("difficulty"),
        "question_count": assessment_params.get("question_count"),
        "type_counts": assessment_params.get("type_counts"),
        "allow_latex": assessment_params.get("allow_latex", True),
        "created_by": assessment_params.get("created_by", "supervisor"),
        "use_rag": assessment_params.get("use_rag", False),
        "rag_top_k": assessment_params.get("rag_top_k", 6),
        "rag_max_chars": assessment_params.get("rag_max_chars", 4000),
        "rag_context": assessment_params.get("rag_context"),
        "pdf_input_paths": assessment_params.get("pdf_input_paths", []),
        "export_pdf": assessment_params.get("export_pdf", False),
        "pdf_output_filename": assessment_params.get("pdf_output_filename"),
    }
    
    # Validate required parameters for assessment generation
    required_fields = ["subject", "assessment_type", "difficulty", "question_count", "type_counts"]
    missing = [f for f in required_fields if not assessment_data.get(f)]
    
    if missing:
        return CompletionReport(
            message_id=str(uuid.uuid4()),
            sender="AssessmentGenerationAgent",
            recipient=task_envelope.sender,
            related_message_id=task_envelope.message_id,
            status="FAILURE",
            results={"error": f"Missing required parameters: {', '.join(missing)}"}
        )

    try:
        # Validate type counts sum
        type_counts = assessment_data["type_counts"]
        question_count = assessment_data["question_count"]
        total_requested = sum(type_counts.values())
        
        if total_requested != question_count:
            return CompletionReport(
                message_id=str(uuid.uuid4()),
                sender="AssessmentGenerationAgent",
                recipient=task_envelope.sender,
                related_message_id=task_envelope.message_id,
                status="FAILURE",
                results={
                    "error": f"Sum of type_counts ({total_requested}) must equal question_count ({question_count})"
                }
            )
        
        # Check LTM cache before generating
        cache_key = ltm.generate_cache_key(assessment_data)
        cached_assessment = await ltm.lookup(cache_key)
        
        if cached_assessment:
            _logger.info(f"LTM cache hit! Returning cached assessment for key {cache_key[:16]}...")
            
            # Handle PDF export for cached assessments if requested
            pdf_path = None
            pdf_exported = False
            if assessment_data.get("export_pdf"):
                try:
                    # Generate filename
                    if assessment_data.get("pdf_output_filename"):
                        safe_filename = Path(assessment_data["pdf_output_filename"]).name
                        if not safe_filename.endswith('.pdf'):
                            safe_filename += '.pdf'
                    else:
                        timestamp = int(datetime.utcnow().timestamp())
                        subject_clean = assessment_data['subject'].replace(' ', '_')
                        safe_filename = f"{subject_clean}_{assessment_data['assessment_type']}_{timestamp}.pdf"
                    
                    output_path = GENERATED_ASSESSMENTS_DIR / safe_filename
                    generate_assessment_pdf(cached_assessment, str(output_path))
                    
                    pdf_path = safe_filename
                    pdf_exported = True
                except Exception as e:
                    _logger.warning(f"PDF export failed for cached assessment: {e}")
            
            # Build result with cached data
            result_data = {
                "output": cached_assessment,
                "cached": True,
                "pdf_exported": pdf_exported
            }
            
            if pdf_path:
                result_data["pdf_path"] = pdf_path
            
            return CompletionReport(
                message_id=str(uuid.uuid4()),
                sender="AssessmentGenerationAgent",
                recipient=task_envelope.sender,
                related_message_id=task_envelope.message_id,
                status="SUCCESS",
                results=result_data
            )
        
        _logger.info(f"LTM cache miss. Generating new assessment for key {cache_key[:16]}...")
        
        # Handle PDF input for RAG
        rag_pdfs_loaded = []
        pdf_input_paths = assessment_data.get("pdf_input_paths", [])
        if pdf_input_paths:
            absolute_paths = []
            for pdf_path in pdf_input_paths:
                # Sanitize filename to prevent path traversal
                safe_filename = Path(pdf_path).name
                abs_path = RAG_DOCUMENTS_DIR / safe_filename
                
                if not abs_path.exists():
                    return CompletionReport(
                        message_id=str(uuid.uuid4()),
                        sender="AssessmentGenerationAgent",
                        recipient=task_envelope.sender,
                        related_message_id=task_envelope.message_id,
                        status="FAILURE",
                        results={"error": f"PDF file not found: {safe_filename}"}
                    )
                
                absolute_paths.append(str(abs_path))
                rag_pdfs_loaded.append(safe_filename)
            
            # Load PDFs into RAG service
            try:
                rag_service.load_pdfs(absolute_paths)
            except Exception as e:
                return CompletionReport(
                    message_id=str(uuid.uuid4()),
                    sender="AssessmentGenerationAgent",
                    recipient=task_envelope.sender,
                    related_message_id=task_envelope.message_id,
                    status="FAILURE",
                    results={"error": f"Failed to load PDFs: {str(e)}"}
                )
        
        # Build RAG context if requested
        rag_context = assessment_data.get("rag_context")
        if assessment_data.get("use_rag") and rag_service.get_document_count() > 0:
            results = rag_service.search(assessment_data["subject"], k=assessment_data["rag_top_k"])
            context_text = "\n\n".join([r.content for r in results])
            rag_max_chars = assessment_data["rag_max_chars"]
            if len(context_text) > rag_max_chars:
                context_text = context_text[:rag_max_chars] + "\n[truncated]"
            rag_context = context_text
        
        # Generate questions using existing service
        all_questions, type_errors = generate_questions_by_type(
            subject=assessment_data["subject"],
            assessment_type=assessment_data["assessment_type"],
            difficulty=assessment_data["difficulty"],
            type_counts=type_counts,
            allow_latex=assessment_data["allow_latex"],
            rag_context=rag_context,
            pdf_paths=None,
            rag_top_k=assessment_data["rag_top_k"],
            rag_max_chars=assessment_data["rag_max_chars"],
        )
        
        # Check for generation errors
        errors = [f"{t}: {e}" for t, e in type_errors.items() if e]
        if errors:
            return CompletionReport(
                message_id=str(uuid.uuid4()),
                sender="AssessmentGenerationAgent",
                recipient=task_envelope.sender,
                related_message_id=task_envelope.message_id,
                status="FAILURE",
                results={"error": "; ".join(errors)}
            )
        
        # Build assessment response
        assessment = {
            "title": f"{assessment_data['subject']} — {assessment_data['assessment_type'].capitalize()} ({assessment_data['difficulty'].capitalize()})",
            "description": f"Auto-generated {assessment_data['assessment_type']} ({assessment_data['difficulty']}) for {assessment_data['subject']}",
            "assessment_type": assessment_data["assessment_type"],
            "subject": assessment_data["subject"],
            "difficulty": assessment_data["difficulty"],
            "total_questions": len(all_questions),
            "questions": all_questions,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {
                "created_by": assessment_data["created_by"],
                "allow_latex": assessment_data["allow_latex"],
                "used_rag": bool(rag_context),
                "type_distribution": {k: v for k, v in type_counts.items() if v > 0}
            }
        }
        
        # Save to LTM cache
        await ltm.save(cache_key, assessment_data, assessment)
        _logger.info(f"Saved assessment to LTM cache with key {cache_key[:16]}...")
        
        # Handle PDF export if requested
        pdf_path = None
        pdf_exported = False
        if assessment_data.get("export_pdf"):
            try:
                # Generate filename
                if assessment_data.get("pdf_output_filename"):
                    # Sanitize custom filename
                    safe_filename = Path(assessment_data["pdf_output_filename"]).name
                    if not safe_filename.endswith('.pdf'):
                        safe_filename += '.pdf'
                else:
                    # Auto-generate filename
                    timestamp = int(datetime.utcnow().timestamp())
                    subject_clean = assessment_data['subject'].replace(' ', '_')
                    safe_filename = f"{subject_clean}_{assessment_data['assessment_type']}_{timestamp}.pdf"
                
                # Full path for PDF export
                output_path = GENERATED_ASSESSMENTS_DIR / safe_filename
                
                # Generate PDF
                generate_assessment_pdf(assessment, str(output_path))
                
                pdf_path = safe_filename  # Return relative path
                pdf_exported = True
            except Exception as e:
                # Don't fail the whole request if PDF export fails
                pdf_path = None
                pdf_exported = False
                assessment["metadata"]["pdf_export_error"] = str(e)
        
        # Build result metadata
        result_data = {
            "output": assessment,
            "cached": False,
            "pdf_exported": pdf_exported
        }
        
        if pdf_path:
            result_data["pdf_path"] = pdf_path
        
        if rag_pdfs_loaded:
            result_data["rag_pdfs_loaded"] = rag_pdfs_loaded
        
        return CompletionReport(
            message_id=str(uuid.uuid4()),
            sender="AssessmentGenerationAgent",
            recipient=task_envelope.sender,
            related_message_id=task_envelope.message_id,
            status="SUCCESS",
            results=result_data
        )
        
    except Exception as e:
        return CompletionReport(
            message_id=str(uuid.uuid4()),
            sender="AssessmentGenerationAgent",
            recipient=task_envelope.sender,
            related_message_id=task_envelope.message_id,
            status="FAILURE",
            results={"error": f"Assessment generation failed: {str(e)}"}
        )


@app.post("/generate", response_model=AssessmentResponse)
async def generate_assessment(request: AssessmentGenerationRequest):
    """
    Generate an assessment based on the provided parameters.
    
    Supports:
    - Multiple question types (mcq, short_text, essay, coding, math)
    - Multiple assessment types (quiz, exam, assignment)
    - RAG context from uploaded PDFs
    - LaTeX support for mathematical notation
    """
    try:
        # Validate type counts
        total_requested = sum(request.type_counts.values())
        if total_requested != request.question_count:
            raise HTTPException(
                status_code=400,
                detail=f"Sum of type_counts ({total_requested}) must equal question_count ({request.question_count})"
            )
        
        # Build RAG context if PDF paths provided
        rag_context = request.rag_context
        if request.pdf_paths:
            results = rag_service.search(request.subject, k=request.rag_top_k)
            context_text = "\n\n".join([r.content for r in results])
            if len(context_text) > request.rag_max_chars:
                context_text = context_text[:request.rag_max_chars] + "\n[truncated]"
            rag_context = context_text
        
        # Generate questions
        all_questions, type_errors = generate_questions_by_type(
            subject=request.subject,
            assessment_type=request.assessment_type,
            difficulty=request.difficulty,
            type_counts=request.type_counts,
            allow_latex=request.allow_latex,
            rag_context=rag_context,
            pdf_paths=None,  # Already handled above
            rag_top_k=request.rag_top_k,
            rag_max_chars=request.rag_max_chars,
        )
        
        # Check for errors
        errors = [f"{t}: {e}" for t, e in type_errors.items() if e]
        if errors:
            raise HTTPException(status_code=500, detail="; ".join(errors))
        
        # Validate total count
        if len(all_questions) != request.question_count:
            raise HTTPException(
                status_code=500,
                detail=f"Expected {request.question_count} questions, got {len(all_questions)}"
            )
        
        # Convert to response format
        questions = [QuestionResponse(**q) for q in all_questions]
        
        return AssessmentResponse(
            title=f"{request.subject} — {request.assessment_type.capitalize()} ({request.difficulty.capitalize()})",
            description=f"Auto-generated {request.assessment_type} ({request.difficulty}) for {request.subject}",
            assessment_type=request.assessment_type,
            subject=request.subject,
            difficulty=request.difficulty,
            total_questions=len(questions),
            questions=questions,
            created_at=datetime.utcnow(),
            metadata={
                "created_by": request.created_by,
                "allow_latex": request.allow_latex,
                "used_rag": bool(rag_context),
                "type_distribution": {k: v for k, v in request.type_counts.items() if v > 0}
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment generation failed: {str(e)}")


@app.post("/upload-pdfs")
async def upload_pdfs(files: List[UploadFile] = File(...)):
    """
    Upload PDF files for RAG processing.
    Returns the paths to the uploaded files.
    """
    try:
        uploaded_paths = []
        
        for file in files:
            if not file.filename.endswith('.pdf'):
                raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF")
            
            # Save file
            file_path = UPLOAD_DIR / f"{datetime.utcnow().timestamp()}_{file.filename}"
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            uploaded_paths.append(str(file_path))
        
        # Load PDFs into RAG service
        rag_service.load_pdfs(uploaded_paths)
        
        return {
            "message": f"Successfully uploaded and processed {len(files)} PDF(s)",
            "paths": uploaded_paths,
            "total_chunks": rag_service.get_document_count()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF upload failed: {str(e)}")


@app.post("/rag/search", response_model=RAGSearchResponse)
async def search_rag(request: RAGSearchRequest):
    """
    Search the RAG knowledge base for relevant content.
    """
    try:
        if rag_service.get_document_count() == 0:
            raise HTTPException(status_code=400, detail="No documents have been loaded yet")
        
        results = rag_service.search(request.query, k=request.top_k)
        
        return RAGSearchResponse(
            query=request.query,
            results=[
                {
                    "content": r.content,
                    "score": float(r.score) if r.score is not None else None,  # Convert numpy to Python float
                    "metadata": r.metadata or {}
                }
                for r in results
            ],
            total_documents=rag_service.get_document_count()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG search failed: {str(e)}")


@app.post("/export-pdf")
async def export_assessment_pdf(assessment: AssessmentResponse):
    """
    Generate and download an assessment as a PDF.
    """
    try:
        # Generate PDF
        output_path = OUTPUT_DIR / f"assessment_{datetime.utcnow().timestamp()}.pdf"
        generate_assessment_pdf(assessment.dict(), str(output_path))
        
        return FileResponse(
            path=output_path,
            media_type="application/pdf",
            filename=f"{assessment.title.replace(' ', '_')}.pdf"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@app.delete("/rag/clear")
async def clear_rag():
    """Clear all documents from the RAG knowledge base."""
    try:
        rag_service.clear()
        
        # Clean up uploaded files
        for file in UPLOAD_DIR.glob("*"):
            file.unlink()
        
        return {
            "message": "RAG knowledge base cleared successfully",
            "documents_remaining": 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear operation failed: {str(e)}")


@app.get("/rag/status")
async def rag_status():
    """Get the current status of the RAG knowledge base."""
    return {
        "documents_loaded": rag_service.get_document_count(),
        "upload_directory": str(UPLOAD_DIR),
        "status": "active" if rag_service.get_document_count() > 0 else "empty"
    }


@app.get("/cache/stats")
async def cache_stats():
    """Get LTM cache statistics"""
    stats = await ltm.get_stats()
    return stats


@app.delete("/cache/clear")
async def clear_cache():
    """Clear all cached assessments from LTM"""
    result = await ltm.clear_cache()
    return result


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)