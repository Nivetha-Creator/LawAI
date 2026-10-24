
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import database
from app.routers import chat, debate, conversations, strategy

app = FastAPI(
    title="LawyerAI",
    description="Indian Legal Information, Debate, and Strategy Analysis Assistant",
    version="2.1.0",
)

# Local Vite origins only (localhost and 127.0.0.1 — browsers treat them as distinct).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    database.init_db()


app.include_router(chat.router, tags=["Legal chat"])
app.include_router(debate.router, tags=["Case debate"])
app.include_router(strategy.router, tags=["Legal strategy"])
app.include_router(conversations.router)


@app.get("/")
def home():
    return {
        "message": "LawyerAI API is running!",
        "features": [
            "Local legal information engine",
            "Local educational debate",
            "Legal strategy analysis",
            "Persistent conversation history",
        ],
        "response_engine": "local",
    }


@app.get("/health")
def health():
    from app.rag.retrieve import rag_enabled
    from app.services import ai_service

    gemini_fallback = ai_service.fallback_enabled()
    return {
        "status": "healthy",
        "response_engine": "local",
        "gemini_fallback": gemini_fallback,
        "rag_enabled": rag_enabled(),
    }
