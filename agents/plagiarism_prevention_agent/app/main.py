"""
Plagiarism Prevention Agent (PPA)
Main FastAPI application entry point
"""

# Import config first to set environment variables before other imports
import app.config  # noqa: F401

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.routers import similarity, rephrase, process
from app.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Plagiarism Prevention Agent",
    description="AI agent for detecting plagiarism and rephrasing text to improve originality",
    version="1.0.0"
)

# CORS middleware - Allow all origins for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(similarity.router, prefix="/api/v1", tags=["Similarity"])
app.include_router(rephrase.router, prefix="/api/v1", tags=["Rephrasing"])
app.include_router(process.router, prefix="/api/v1", tags=["Processing"])

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Plagiarism Prevention Agent API",
        "version": "1.0.0",
        "endpoints": {
            "check_similarity": "/api/v1/check-similarity",
            "rephrase_text": "/api/v1/rephrase-text",
            "process_text": "/api/v1/process-text"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

