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
- **Legal Strategy** — lawful defences, evidence gaps, procedure, and next steps (`POST /strategy`)
- **Argue a Case** — local opposing-counsel simulation + rule-based feedback
- **Chat history** — SQLite create / list / open / rename / delete

### Legal Strategy Analysis (safe usage)

Use the **Legal Strategy** tab when you want a structured review of a situation.

1. Provide jurisdiction, approximate dates, allegations, procedural stage, and available evidence.
2. LawyerAI asks clarifying questions if essentials are missing — it does **not** invent facts.
3. A complete analysis includes: case summary, relevant law (curated KB only when matched), lawful defences, evidence gaps, procedural issues, opposing arguments, strengths/risks, and practical next steps.
4. “Loopholes” means **lawful** arguments and evidentiary/procedural weaknesses — never illegal tactics.
5. Illegal requests (fabricating evidence, bribery, etc.) are refused with lawful alternatives.
6. Optional Gemini (same `LAWYERAI_USE_LLM` + `GEMINI_API_KEY` as chat) may add an **unverified** note only when no curated law topic matched; it is labelled clearly and is not treated as verified law.
7. Do not paste unnecessary IDs or confidential case files into the chat.

**Limitations:** educational guidance only; not a prediction of winning; may not cover every area of Indian law; always verify on [India Code](https://www.indiacode.nic.in/) and with a qualified advocate.

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

**API connection (important for Cloud Agents):** leave `VITE_API_BASE_URL` unset. The browser calls same-origin paths (`/chat`, `/strategy`, `/debate`, `/conversations`, `/health`). Vite proxies those to FastAPI at `127.0.0.1:8000` inside the VM. You do **not** need to forward port 8000 or open a Ports tab for the backend.

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
5. **Legal Strategy**: paste a detailed situation (place, date, stage, evidence) → eight-section analysis; try a thin prompt → clarifying questions; try an illegal tactic → refusal.
6. **Argue a Case**: choose Defence, enter a topic, send your own opening argument → opposing counsel replies referencing your point.
7. Click **End debate & request feedback** → rule-based report; reopen the thread → debate stays ended.
8. Rename and delete a conversation from the sidebar.
9. Resize the window / use DevTools device mode for mobile sidebar open/close.

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

When enabled, the configured LLM is used **only if** the local knowledge base cannot answer an Ask Me Anything question, and for Legal Strategy **only** to add an unverified note when no curated law topic matched. Debate stays local. AI replies are labelled as unverified fallback—not curated legal advice.

Chat and strategy call a small provider interface (`backend/app/llm/`). Gemini is the only adapter. `LAWYERAI_LLM_PROVIDER` defaults to `gemini`.

1. `pip install google-genai`
2. Copy `backend/.env.example` → `backend/.env` (never commit `.env`)
3. Set `LAWYERAI_USE_LLM=1` and `GEMINI_API_KEY=...` (optional `GEMINI_MODEL`, `GEMINI_TIMEOUT_SECONDS`)
4. Restart the backend

Confirm `GET /health` shows `"gemini_fallback": true` only when both flag and key are set.

---

## Optional local RAG (off by default)

Retrieval uses ChromaDB and a **local** MiniLM embedder (Chroma's ONNX `ONNXMiniLM_L6_V2`). It does not call a hosted embedding API, and it does not use Gemini to embed text. Gemini text generation is unchanged and stays behind `LAWYERAI_USE_LLM`.

`LAWYERAI_RAG_ENABLED` defaults to off. While it is off, the app does not import Chroma and does not need the package installed.

When it is on:

- **Ask Me Anything** still prefers the keyword knowledge base. Retrieval runs only for questions the local engine marks unknown.
- **Legal Strategy** still refuses illegal requests and asks clarifying questions before any retrieval. Retrieval runs only when a complete analysis has no curated law match.
- **Debate Practice** stays local and does not call the LLM or the index.
- If chunks are found and the LLM is off or fails, the reply quotes those chunks and labels them as retrieved excerpts, not a verified legal answer.
- Generated citations are kept only when every recognized reference is supported by the retrieved chunks. That includes `section` / `sec.` / `s.` / `§`, `article` / `art.`, act-plus-number forms such as `IPC 302` and `BNS 103`, and both `http(s)://` and `www.` URLs. The only standing URL is the exact India Code homepage, with no extra path. Ranges, roman numerals, and other unclear citation syntax are rejected. Otherwise the reply falls back to retrieved excerpts, which are not a verified legal opinion.
- The index uses Chroma's default distance: **squared L2** (`hnsw:space` is left unset, so the server default `l2` applies). That is the sum of squared differences, not cosine similarity and not the square root. Lower is closer, and the value has no finite upper bound. This repository has not measured those distances on a real collection.
- `LAWYERAI_RAG_MAX_DISTANCE` defaults to **1.0** when unset. That cutoff is **provisional and uncalibrated**. It only stops the previous behavior of keeping every neighbor. It may hide useful chunks and may still let weak chunks through. Set a finite number `>= 0` after you compare distances on your own index. Neighbors farther than the cutoff, and queries that match nothing, are treated as no evidence: they are not sent to the LLM and are not shown as retrieved excerpts. The reply stays on the local engine.
- Metadata filters are optional. A jurisdiction filter is sent to Chroma as an exact equality match, and only when the question contains one explicit `jurisdiction: TOKEN` (or `jurisdiction=TOKEN`) marker. Place names such as "Maharashtra" are not guessed. An effective-date filter is applied in Python, not as a Chroma inequality, and only when the question contains exactly one real `YYYY-MM-DD` date. Chunks whose `effective_date` is missing, blank, invalid, or later than that date are excluded. `document_version` and `published_date` are not substitutes. With a date filter, retrieval reads at most 32 nearest neighbors (or `k`, if `k` is larger) and then keeps at most `k` that pass. If the question does not establish a jurisdiction or a single ISO date, that filter is left off.

Indexed files stay on this machine (`LAWYERAI_CHROMA_PATH`, default `data/chroma`). Do not put confidential case files in the corpus. The repository does not download or scrape official legislation; you supply local `.md` or `.txt` files yourself.

Install only if you enable RAG (Python 3.12, Chroma 0.5.5 through 1.1):

```bash
pip install "chromadb>=0.5.5,<1.2"
```

Each document is a folder with `document.json` and exactly one `.md` or `.txt` file. Required JSON fields: `source_title`, `official_url`, `jurisdiction`, `document_version`. Optional: `effective_date`, `published_date`, `section`, `document_id`. Dates must be `YYYY-MM-DD`. Missing required fields are rejected.

```bash
cd backend
# LAWYERAI_RAG_ENABLED=true
python -m app.rag.ingest --corpus-root path\to\corpus --chroma-path data\chroma
```

The ingester builds a new collection and switches the active pointer only after that build is marked ready. An incomplete build does not replace the active collection. A missing, corrupt, or empty `active_index.json`, or a pointer that names a collection that is not in the store, raises an error. Queries do not fall back to the default collection name `legal_chunks`. This is not a background updater and does not by itself guarantee zero downtime across processes.

`GET /health` includes `"rag_enabled": false` unless the flag is on.

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
