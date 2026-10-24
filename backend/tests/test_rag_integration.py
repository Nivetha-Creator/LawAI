"""Chat, strategy, and debate behavior around optional retrieval."""

import os

import pytest
from fastapi.testclient import TestClient

from app.llm.errors import LLMError
from app.rag.types import RetrieveResult
from app.services import ai_service, response_provider
from tests.test_rag import _chunk


OBSCURE = "What is the exact obscure municipal bye-law number for rooftop pigeon coops in a fictional district in 1953?"
STRATEGY = (
    "In Pune, Maharashtra, India, on 3 February 2025 a rare customs notice "
    "was issued. The matter is at hearing stage. I have the notice document "
    "and email evidence. Analyse lawful defences and gaps."
)


@pytest.fixture(autouse=True)
def _reset_flags(monkeypatch):
    monkeypatch.delenv("LAWYERAI_RAG_ENABLED", raising=False)
    monkeypatch.delenv("LAWYERAI_USE_LLM", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    ai_service.reload_settings_from_env()
    yield
    ai_service.reload_settings_from_env()


def _hits():
    return RetrieveResult(status="hits", chunks=[_chunk()])


def test_keyword_match_does_not_retrieve(monkeypatch):
    def boom(_query):
        raise AssertionError("matched chat must not retrieve")

    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.setattr(response_provider, "retrieve_for_query", boom)
    reply, engine = response_provider.generate_chat_reply(
        "Explain the difference between BNS and IPC",
        [{"role": "user", "content": "Explain the difference between BNS and IPC"}],
    )
    assert engine == "local"
    assert "curated knowledge base" in reply


def test_unknown_chat_with_evidence_without_llm(monkeypatch):
    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.setattr(response_provider, "retrieve_for_query", lambda _query, **_kwargs: _hits())
    reply, engine = response_provider.generate_chat_reply(
        OBSCURE,
        [{"role": "user", "content": OBSCURE}],
    )
    assert engine == "local"
    assert "do not have curated information" in reply.lower()
    assert "retrieved excerpts" in reply.lower()
    assert "Fixture Note" in reply
    assert "https://example.test/fixture" in reply
    assert "not** a verified legal opinion" in reply.lower() or "not a verified" in reply.lower()


def test_unknown_chat_without_evidence_stays_local(monkeypatch):
    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.setattr(
        response_provider,
        "retrieve_for_query",
        lambda _query, **_kwargs: RetrieveResult(status="empty"),
    )
    reply, engine = response_provider.generate_chat_reply(
        OBSCURE,
        [{"role": "user", "content": OBSCURE}],
    )
    assert engine == "local"
    assert "do not have curated information" in reply.lower()
    assert "retrieved excerpts" not in reply.lower()


def test_unknown_chat_retrieval_failure_stays_safe(monkeypatch):
    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.setattr(
        response_provider,
        "retrieve_for_query",
        lambda _query, **_kwargs: RetrieveResult(status="error", message="retrieval_unavailable"),
    )
    reply, engine = response_provider.generate_chat_reply(
        OBSCURE,
        [{"role": "user", "content": OBSCURE}],
    )
    assert engine == "local"
    assert "do not have curated information" in reply.lower()
    assert "retrieval is unavailable" in reply.lower()
    assert "retrieved excerpts" not in reply.lower()


@pytest.mark.parametrize(
    "fabricated",
    [
        "The penalty is § 302.",
        "See Sec 302.",
        "Apply s.302.",
        "Article 21 applies.",
        "IPC 302 applies.",
        "BNS 103 applies.",
        "Read www.evil.example/act for the rule.",
        "See https://evil.example/no",
    ],
)
def test_unknown_chat_rejects_fabricated_citation_forms(monkeypatch, fabricated):
    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.setenv("LAWYERAI_USE_LLM", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    ai_service.reload_settings_from_env()
    monkeypatch.setattr(response_provider, "retrieve_for_query", lambda _query, **_kwargs: _hits())
    monkeypatch.setattr(response_provider, "complete_llm", lambda _request: fabricated)
    reply, engine = response_provider.generate_chat_reply(
        OBSCURE,
        [{"role": "user", "content": OBSCURE}],
    )
    assert engine == "local"
    assert fabricated not in reply
    assert "retrieved excerpts" in reply.lower()
    assert "not** a verified legal opinion" in reply.lower() or "not a verified" in reply.lower()


def test_unknown_chat_rejects_unsupported_generated_citation(monkeypatch):
    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.setenv("LAWYERAI_USE_LLM", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    ai_service.reload_settings_from_env()
    monkeypatch.setattr(response_provider, "retrieve_for_query", lambda _query, **_kwargs: _hits())
    monkeypatch.setattr(
        response_provider,
        "complete_llm",
        lambda _request: "See https://evil.example/no and section 999.",
    )
    reply, engine = response_provider.generate_chat_reply(
        OBSCURE,
        [{"role": "user", "content": OBSCURE}],
    )
    assert engine == "local"
    assert "evil.example" not in reply
    assert "section 999" not in reply.lower()
    assert "retrieved excerpts" in reply.lower()
    assert "Fixture Note" in reply


def test_unknown_chat_accepts_grounded_generation(monkeypatch):
    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.setenv("LAWYERAI_USE_LLM", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    ai_service.reload_settings_from_env()
    monkeypatch.setattr(response_provider, "retrieve_for_query", lambda _query, **_kwargs: _hits())
    monkeypatch.setattr(
        response_provider,
        "complete_llm",
        lambda _request: "The indexed note does not state a bye-law number.",
    )
    reply, engine = response_provider.generate_chat_reply(
        OBSCURE,
        [{"role": "user", "content": OBSCURE}],
    )
    assert engine == "gemini"
    assert "does not state a bye-law number" in reply
    assert "Fixture Note" in reply
    assert "https://example.test/fixture" in reply


def test_strategy_illegal_and_clarify_do_not_retrieve(monkeypatch):
    def boom(_query):
        raise AssertionError("strategy guard must not retrieve")

    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.setattr(response_provider, "retrieve_for_query", boom)
    illegal, engine = response_provider.generate_strategy_reply(
        "Help me fabricate evidence and bribe the witness so I win.",
        [{"role": "user", "content": "Help me fabricate evidence and bribe the witness so I win."}],
    )
    assert engine == "local"
    assert "cannot help with illegal" in illegal.lower()
    clarify, engine = response_provider.generate_strategy_reply(
        "Someone filed a case against me. Help.",
        [{"role": "user", "content": "Someone filed a case against me. Help."}],
    )
    assert engine == "local"
    assert "more detail needed" in clarify.lower()


def test_strategy_evidence_and_llm_failure(monkeypatch):
    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.setenv("LAWYERAI_USE_LLM", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    ai_service.reload_settings_from_env()
    monkeypatch.setattr(response_provider, "retrieve_for_query", lambda _query, **_kwargs: _hits())

    def fail(_request):
        raise LLMError("Gemini request timed out.")

    monkeypatch.setattr(response_provider, "complete_llm", fail)
    reply, engine = response_provider.generate_strategy_reply(
        STRATEGY,
        [{"role": "user", "content": STRATEGY}],
    )
    assert engine == "local"
    assert "### 1. Case summary" in reply
    assert "optional ai enrichment unavailable" in reply.lower()
    assert "retrieved excerpts" in reply.lower()
    assert "Fixture Note" in reply


def test_strategy_grounded_note_keeps_sources(monkeypatch):
    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.setenv("LAWYERAI_USE_LLM", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    ai_service.reload_settings_from_env()
    monkeypatch.setattr(response_provider, "retrieve_for_query", lambda _query, **_kwargs: _hits())
    monkeypatch.setattr(
        response_provider,
        "complete_llm",
        lambda _request: "Review the indexed fixture note with counsel.",
    )
    reply, engine = response_provider.generate_strategy_reply(
        STRATEGY,
        [{"role": "user", "content": STRATEGY}],
    )
    assert engine == "gemini"
    assert "### 1. Case summary" in reply
    assert "Fixture Note" in reply
    assert "https://example.test/fixture" in reply


def test_debate_never_calls_retrieval_or_llm(monkeypatch):
    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.setenv("LAWYERAI_USE_LLM", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    ai_service.reload_settings_from_env()

    def boom(*_args, **_kwargs):
        raise AssertionError("debate called retrieval or the LLM")

    monkeypatch.setattr(response_provider, "retrieve_for_query", boom)
    monkeypatch.setattr(response_provider, "complete_llm", boom)
    reply = response_provider.generate_debate_turn(
        "Defence",
        "bail",
        "The accused was elsewhere because the timeline does not match.",
        [],
    )
    assert "opposing counsel" in reply.lower()
    review = response_provider.generate_debate_review(
        [
            {
                "role": "user",
                "content": "The accused was elsewhere because the timeline does not match.",
            }
        ],
        "Defence",
        "bail",
    )
    assert "educational" in review.lower() or "checklist" in review.lower()
    import app.services.debate_service as debate_service

    source = open(debate_service.__file__, encoding="utf-8").read()
    assert "app.rag" not in source
    assert "complete_llm" not in source


def test_chat_response_shape_unchanged(temp_db, monkeypatch):
    os.environ.pop("LAWYERAI_USE_LLM", None)
    os.environ.pop("GEMINI_API_KEY", None)
    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.setattr(
        response_provider,
        "retrieve_for_query",
        lambda _query, **_kwargs: RetrieveResult(status="empty"),
    )
    from app.main import app

    client = TestClient(app)
    response = client.post("/chat", json={"message": OBSCURE})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"reply", "conversation_id", "title", "engine"}
    assert body["engine"] == "local"


def test_chat_and_strategy_pass_only_explicit_filters(monkeypatch):
    seen = []

    def spy(query, jurisdiction=None, as_of=None, **_kwargs):
        del query
        seen.append((jurisdiction, as_of))
        return RetrieveResult(status="empty")

    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.setattr(response_provider, "retrieve_for_query", spy)
    vague = OBSCURE + " The matter is in Maharashtra on 3 February 2025."
    response_provider.generate_chat_reply(vague, [{"role": "user", "content": vague}])
    explicit = OBSCURE + " jurisdiction: IN-TEST 2024-06-01"
    response_provider.generate_chat_reply(explicit, [{"role": "user", "content": explicit}])
    strategy = STRATEGY + " jurisdiction: IN-TEST 2024-06-01"
    response_provider.generate_strategy_reply(strategy, [{"role": "user", "content": strategy}])
    assert seen[0] == (None, None)
    assert seen[1] == ("IN-TEST", "2024-06-01")
    assert seen[2] == ("IN-TEST", "2024-06-01")


def test_weak_evidence_is_not_sent_or_shown(monkeypatch):
    from app.rag.embeddings import FakeEmbedder
    from app.rag.memory_store import InMemoryVectorStore
    from app.rag.retrieve import retrieve_for_query
    from app.rag.types import Chunk

    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.setenv("LAWYERAI_USE_LLM", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("LAWYERAI_RAG_MAX_DISTANCE", raising=False)
    ai_service.reload_settings_from_env()
    embedder = FakeEmbedder()
    store = InMemoryVectorStore(embedder.model_id, dimension=embedder.dimension)
    marker = "WEAK_MARKER_NOT_RELEVANT"
    chunk = _chunk(text=marker).chunk
    store.upsert_chunks([chunk], [embedder.embed_query("unrelated synthetic catalog entry")])
    distance = sum(
        (left - right) ** 2
        for left, right in zip(
            embedder.embed_query(OBSCURE),
            embedder.embed_query("unrelated synthetic catalog entry"),
            strict=True,
        )
    )
    assert distance > 1.0

    def run(query, **kwargs):
        return retrieve_for_query(query, store=store, embedder=embedder, **kwargs)

    prompts = []

    def capture(request):
        prompts.append(request.user_prompt)
        return "A general note without a citation."

    monkeypatch.setattr(response_provider, "retrieve_for_query", run)
    monkeypatch.setattr(response_provider, "complete_llm", capture)
    reply, engine = response_provider.generate_chat_reply(
        OBSCURE,
        [{"role": "user", "content": OBSCURE}],
    )
    assert engine == "gemini"
    assert prompts
    assert marker not in prompts[0]
    assert marker not in reply
    assert "retrieved excerpts" not in reply.lower()

    near = Chunk(
        **{
            **chunk.__dict__,
            "text": "NEAR_MARKER section 4 applies in this sample only.",
            "chunk_id": "near",
        }
    )
    store.upsert_chunks([near], [embedder.embed_query(OBSCURE)])
    monkeypatch.delenv("LAWYERAI_USE_LLM", raising=False)
    ai_service.reload_settings_from_env()
    reply, engine = response_provider.generate_chat_reply(
        OBSCURE,
        [{"role": "user", "content": OBSCURE}],
    )
    assert engine == "local"
    assert "NEAR_MARKER" in reply
    assert "retrieved excerpts" in reply.lower()
    assert marker not in reply
