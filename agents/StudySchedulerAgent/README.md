📚 Study Scheduler Agent

Project: Multi-Agent System (Section A: Education & Learning Agents)

An intelligent, adaptive agent designed to automatically generate and optimize personalized study timetables for university students.

Status

Team

Base URL

Prototype Ready

Section A, Group X

http://127.0.0.1:8000

1. 🤖 Agent Overview

Refined Agent Description (For Supervisor LLM)

The Study Scheduler Agent is an autonomous planning system that generates, optimizes, and maintains personalized, adaptive study timetables. It is explicitly invoked by the user (via the Supervisor Agent) to create a new schedule or request an optimization of their current one. The agent processes student profile data, subject difficulty, personal availability, current deadlines, and performance metrics to produce a prioritized daily study plan and define adaptive rules for future adjustments.

Core Agentic Logic

The agent’s scheduling algorithm prioritizes subjects based on a weighted formula:

$$\text{Priority Score} = \text{Subject Difficulty Score} \times \text{Performance Feedback Score}$$

Result: Subjects with a higher Priority Score (e.g., High Difficulty + Weak Performance) are allocated longer, more frequent study sessions.

2. 💻 Technical Details

Architecture

The agent follows a modular architecture for clear separation of concerns:

Backend: FastAPI (Python) — Handles API communication, data validation (Pydantic), and the core scheduling algorithm.

Frontend (Prototype UI): React (TSX) + Tailwind CSS — Provides a functional and visually polished interface for demonstration and testing.

API Endpoints

The agent exposes the following endpoints, accessible via the base URL: http://127.0.0.1:8000.

Method

Endpoint

Description

POST

/generate_schedule/

Primary Function. Receives the full AgentInput JSON, executes the scheduling algorithm, and returns the generated schedule (AgentOutput).

GET

/health/

Supervisor Check. Returns {"status": "ok"} to confirm the service is running and ready for calls.

3. ⚙️ Setup and Run Instructions

To run the Study Scheduler Agent locally, you must run both the Python backend (FastAPI) and the React frontend.

3.1 Backend Setup (FastAPI)

Navigate to the backend/ directory.

cd backend


Install dependencies (FastAPI, Uvicorn, Pydantic).

pip install -r requirements.txt


Run the server. Keep this terminal window open.

python -m uvicorn main:app --reload


The API will be available at http://127.0.0.1:8000.

3.2 Frontend Setup (React/TSX)

Navigate to the frontend/ directory in a new terminal window.

cd ../frontend


Install Node dependencies.

npm install


Start the development server.

npm run dev
