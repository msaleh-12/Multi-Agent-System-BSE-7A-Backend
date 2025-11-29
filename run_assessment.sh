#!/bin/bash
# run_assessment.sh
echo "Starting Exam Readiness Agent..."
uvicorn agents.exam_readiness.app:app --host 0.0.0.0 --port 8003 --reload