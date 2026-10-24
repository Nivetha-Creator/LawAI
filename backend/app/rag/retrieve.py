"""Query the active index. Chroma is imported only while RAG is enabled."""

from __future__ import annotations

import math
import os
from pathlib import Path

from app.rag.embeddings import FakeEmbedder, LocalMiniLMEmbedder
from app.rag.errors import EmbeddingDependencyError, ModelMismatchError, StoreError
from app.rag.filters import (
    build_where,
    candidate_limit,
    contains_range_operator,
    metadata_accepts,
    passes_as_of,
)
from app.rag.types import RetrieveResult

# Chroma collections are created without ``hnsw:space``, so the server default
# applies: squared Euclidean (``l2``), not cosine and not the square root.
# Lower is closer. There is no measured cutoff for this corpus — chromadb is
# not installed in the test environment — so 1.0 is an uncalibrated gate.
# It only replaces "keep every neighbor". Calibrate before relying on it.
PROVISIONAL_MAX_DISTANCE = 1.0

_ON = {"1", "true", "yes", "on"}


def rag_enabled() -> bool:
    return os.getenv("LAWYERAI_RAG_ENABLED", "").strip().lower() in _ON


def _default_embedder():
    name = os.getenv("LAWYERAI_EMBEDDING_PROVIDER", "local-minilm").strip().lower() or "local-minilm"
    if name == "fake-test":
        return FakeEmbedder()
    if name == "local-minilm":
        return LocalMiniLMEmbedder()
    raise EmbeddingDependencyError("Unsupported embedding provider.")


def _default_store(model_id: str):
    from app.rag.chroma_store import ChromaVectorStore

    path = Path(os.getenv("LAWYERAI_CHROMA_PATH", "data/chroma"))
    name = os.getenv("LAWYERAI_CHROMA_COLLECTION", "legal_chunks").strip() or "legal_chunks"
    return ChromaVectorStore(path, model_id, collection_name=name)


def configured_max_distance() -> float:
    """Squared-L2 cutoff. Blank means the provisional default.

    Negative, non-finite, and non-numeric values raise ``ValueError``.
    Squared L2 has no finite upper bound, so a large finite value is accepted
    and simply makes the gate very loose.
    """
    raw = os.getenv("LAWYERAI_RAG_MAX_DISTANCE", "").strip()
    if not raw:
        return PROVISIONAL_MAX_DISTANCE
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError("LAWYERAI_RAG_MAX_DISTANCE must be a finite number >= 0.") from exc
    if not math.isfinite(value) or value < 0:
        raise ValueError("LAWYERAI_RAG_MAX_DISTANCE must be a finite number >= 0.")
    return value


def _keep_hit(item, where: dict | None, max_distance: float) -> bool:
    distance = getattr(item, "distance", None)
    try:
        value = float(distance)
    except (TypeError, ValueError):
        return False
    if not math.isfinite(value) or value < 0 or value > max_distance:
        return False
    chunk = getattr(item, "chunk", None)
    metadata = chunk.metadata() if chunk is not None and hasattr(chunk, "metadata") else {}
    return metadata_accepts(metadata, where)


def retrieve_for_query(
    query: str,
    *,
    store=None,
    embedder=None,
    k: int = 4,
    where: dict | None = None,
    jurisdiction: str | None = None,
    as_of: str | None = None,
) -> RetrieveResult:
    """Return hits, or a disabled/empty/error result. Never raises for callers.

    Hits farther than the squared-L2 cutoff are discarded. Jurisdiction
    equality is the only metadata clause sent to the store. An as-of date is
    applied in Python to ``effective_date`` and never as a string inequality.
    An explicit ``where`` replaces the jurisdiction clause and disables the
    as-of check. No usable hit is reported as ``empty``.
    """
    if not rag_enabled():
        return RetrieveResult(status="disabled")
    try:
        max_distance = configured_max_distance()
        if where is None:
            where = build_where(jurisdiction, as_of)
            as_of_bound = as_of
        else:
            as_of_bound = None
        if contains_range_operator(where):
            raise ValueError("Date inequalities cannot be sent to the vector store.")
        embedder = embedder or _default_embedder()
        store = store or _default_store(embedder.model_id)
        if getattr(store, "embedding_model_id", embedder.model_id) != embedder.model_id:
            raise ModelMismatchError("Index embedding model does not match the configured embedder.")
        vector = embedder.embed_query(query)
        hits = store.query(
            vector,
            k=candidate_limit(k, as_of_bound),
            where=where,
            max_distance=max_distance,
        )
        kept = []
        for item in hits:
            if not _keep_hit(item, where, max_distance):
                continue
            chunk = getattr(item, "chunk", None)
            metadata = chunk.metadata() if chunk is not None and hasattr(chunk, "metadata") else {}
            if not passes_as_of(metadata, as_of_bound):
                continue
            kept.append(item)
            if len(kept) >= k:
                break
        hits = kept
    except (StoreError, ModelMismatchError, EmbeddingDependencyError, ValueError, OSError):
        return RetrieveResult(status="error", message="retrieval_unavailable")
    except Exception:
        return RetrieveResult(status="error", message="retrieval_unavailable")
    if not hits:
        return RetrieveResult(status="empty")
    return RetrieveResult(status="hits", chunks=hits)
