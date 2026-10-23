# LawyerAI

Indian legal information and educational debate assistant.

**No API key is required.** By default, LawyerAI uses a curated local knowledge base and rule-based debate engine. Optional Google Gemini support exists but is disabled unless you explicitly enable it.

## Stack

| Layer | Tech | Default URL |
|--------|------|-------------|
| Frontend | React + Vite | http://localhost:5173 |
| Backend | FastAPI + SQLite | http://127.0.0.1:8000 |
| Docs | Swagger UI | http://127.0.0.1:8000/docs |
| Health | JSON | http://127.0.0.1:8000/health |

## Features

- **Ask Me Anything** — local topic matching (`backend/app/knowledge/topics.py`)
- **Argue a Case** — local opposing-counsel simulation + rule-based feedback
- **Chat history** — SQLite create / list / open / rename / delete

---

## Windows setup (PowerShell)

Use **two separate PowerShell terminals**. Run the backend first, then the frontend.

### Prerequisites

- Python 3.11+ (`python --version`)
- Node.js 20+ and npm (`node --version`, `npm --version`)
- Git (to clone the repo)

### Terminal 1 — Backend

```powershell
cd path\to\LawAI\backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1

# If activation is blocked once:
# Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

pip install -r requirements.txt

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify in a browser or a third terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
# Expect: status=healthy, response_engine=local

# Interactive API docs:
start http://127.0.0.1:8000/docs
```

Leave this terminal running.

### Terminal 2 — Frontend

```powershell
cd path\to\LawAI

npm install
npm run dev
```

Open the URL Vite prints (usually http://localhost:5173), or the **Cursor Cloud Agent forwarded URL for port 5173**.

**API connection (important for Cloud Agents):** leave `VITE_API_BASE_URL` unset. The browser calls same-origin paths (`/chat`, `/debate`, `/conversations`, `/health`). Vite proxies those to FastAPI at `127.0.0.1:8000` inside the VM. You do **not** need to forward port 8000 or open a Ports tab for the backend.

Only set `VITE_API_BASE_URL` if you intentionally bypass the Vite proxy.

---

## macOS / Linux quick start

```bash
# Terminal 1
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2
cd ..
npm install
npm run dev
```

---

## Tests (no network, no API key)

### Backend

```powershell
cd path\to\LawAI\backend
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Get-Location).Path
python -m pytest -q
```

### Frontend

```powershell
cd path\to\LawAI
npm run build
npm run lint -- src
```

---

## Manual smoke checklist

1. Backend `/health` returns `"response_engine": "local"`.
2. Open http://127.0.0.1:8000/docs and confirm `/chat`, `/debate`, `/conversations`.
3. In the UI, ask: `Explain the difference between BNS and IPC.` → curated knowledge answer.
4. Ask something obscure outside the knowledge base → “do not have curated information”.
5. **Argue a Case**: choose Defence, enter a topic, send your own opening argument → opposing counsel replies referencing your point.
6. Click **End debate & request feedback** → rule-based report; reopen the thread → debate stays ended.
7. Rename and delete a conversation from the sidebar.
8. Resize the window / use DevTools device mode for mobile sidebar open/close.

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| `Activate.ps1` cannot be loaded | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` then retry |
| `ModuleNotFoundError: No module named 'app'` | Run uvicorn from the `backend` folder with the venv active |
| Frontend cannot reach API / `ERR_CONNECTION_REFUSED` to `127.0.0.1:8000` | Do **not** set `VITE_API_BASE_URL` to `127.0.0.1` when using a Cloud Agent forwarded URL. Restart `npm run dev` so the Vite proxy is active; keep backend on port 8000 |
| History empty / sidebar error | Backend must be running; click **Retry** in the sidebar |
| Port 8000 already in use | Stop the other process, or change uvicorn’s port and update the proxy target in `vite.config.js` |
| Expecting cloud AI answers | Local mode is the default. Do **not** set `LAWYERAI_USE_LLM` unless you intentionally install `google-genai` and add a key |

Database file (created at runtime): `backend/lawyerai.db` (gitignored).

---

## Optional Gemini fallback (not required)

Default = **local knowledge base only**. Gemini is never required.

When enabled, Gemini is used **only if** the local knowledge base cannot answer an Ask Me Anything question. Debate stays local. AI replies are labelled as unverified fallback—not curated legal advice.

1. `pip install google-genai`
2. Copy `backend/.env.example` → `backend/.env` (never commit `.env`)
3. Set `LAWYERAI_USE_LLM=1` and `GEMINI_API_KEY=...`
4. Restart the backend

Confirm `GET /health` shows `"gemini_fallback": true` only when both flag and key are set.

---

## CORS (local development)

Allowed origins:

- `http://localhost:5173`
- `http://localhost:5174`
- `http://127.0.0.1:5173`
- `http://127.0.0.1:5174`

The API binds to `127.0.0.1` in the recommended uvicorn command so it is not exposed on the public network interface.

---

## Disclaimer

LawyerAI provides general legal information for learning, not legal advice. Consult a qualified advocate for your situation. Official statutes: https://www.indiacode.nic.in/
