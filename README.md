# Pathfinder AI

A problem-solving chat assistant: describe any problem, it clarifies if needed, then gives a Problem Summary, Roadmap, Step-by-Step Solution, and Next Steps.

## Setup

### Backend
```
cd backend
venv\Scripts\activate
copy .env.example .env   # then paste your OPENAI_API_KEY into .env
uvicorn main:app --reload --port 8010
```
Runs on http://localhost:8010

### Frontend
```
cd frontend
npm run dev
```
Runs on http://localhost:5180
