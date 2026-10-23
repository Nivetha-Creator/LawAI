# LawyerAI

Indian legal information and educational debate assistant. **Phase 2 runs fully offline** using a curated knowledge base and local debate rules—no API key required.

## Stack

- **Frontend:** React + Vite (`npm run dev` → http://localhost:5173)
- **Backend:** FastAPI + SQLite (`uvicorn` → http://127.0.0.1:8000)

## Quick start

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
npm install
npm run dev
```

Open the Vite URL and ensure the backend is running on port 8000.

### Tests (no network, no API key)

```bash
cd backend
source .venv/bin/activate
pytest -q
```

## Optional Gemini LLM

By default, responses use the **local engine**. To enable Gemini (requires `google-genai` and an API key):

1. `pip install google-genai`
2. Copy `backend/.env.example` to `backend/.env`
3. Set `LAWYERAI_USE_LLM=1` and `GEMINI_API_KEY=...`

## Features

- **Ask Me Anything** — topic matching against `backend/app/knowledge/topics.py`
- **Argue a Case** — local opposing counsel simulation + rule-based debate feedback
- **Chat history** — SQLite persistence (create, list, open, rename, delete)

## Disclaimer

LawyerAI provides general legal information for learning, not legal advice. Consult a qualified advocate for your situation.
