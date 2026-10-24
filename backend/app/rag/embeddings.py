"""Embedding providers.

Tests use ``FakeEmbedder``. The local MiniLM adapter is Chroma's ONNX
``ONNXMiniLM_L6_V2`` (all-MiniLM-L6-v2, 384 dimensions). It is constructed
only when a caller embeds text, and it is not a Gemini text-generation call.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

from app.rag.errors import EmbeddingDependencyError

LOCAL_MINILM_MODEL_ID = "onnx-minilm-l6-v2"
LOCAL_MINILM_DIMENSION = 384
_INSTALL_HINT = 'pip install "chromadb>=0.5.5,<1.2"'


class EmbeddingProvider(Protocol):
    model_id: str
    dimension: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in order."""

    def embed_query(self, text: str) -> list[float]:
        """Return the vector for a search query."""


class FakeEmbedder:
    """Deterministic vectors for tests. Does not load a model."""

    model_id = "fake-test"
    dimension = 8

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        digest = hashlib.sha256((text or "").encode("utf-8")).digest()
        return [byte / 255.0 for byte in digest[: self.dimension]]


class LocalMiniLMEmbedder:
    """Local ONNX MiniLM via Chroma. Import and weights load on first embed."""

    model_id = LOCAL_MINILM_MODEL_ID
    dimension = LOCAL_MINILM_DIMENSION

    def __init__(self) -> None:
        self._fn = None

    def _load(self):
        if self._fn is not None:
            return self._fn
        try:
            from chromadb.utils import embedding_functions as embedding_functions
        except ImportError as exc:
            raise EmbeddingDependencyError(
                f"chromadb is not installed. {_INSTALL_HINT}"
            ) from exc
        onnx_cls = getattr(embedding_functions, "ONNXMiniLM_L6_V2", None)
        if onnx_cls is None:
            raise EmbeddingDependencyError(
                "Installed Chroma has no ONNXMiniLM_L6_V2 embedding class. "
                f"Use a 0.5.x or 1.x build. {_INSTALL_HINT}"
            )
        # Constructing this class can download ONNX weights. Callers that only
        # need the protocol should use FakeEmbedder in tests.
        self._fn = onnx_cls()
        return self._fn

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        fn = self._load()
        rows = fn(list(texts))
        return [_as_floats(row) for row in rows]

    def embed_query(self, text: str) -> list[float]:
        fn = self._load()
        embed_query = getattr(fn, "embed_query", None)
        if callable(embed_query):
            rows = embed_query([text])
        else:
            rows = fn([text])
        return _as_floats(rows[0])


def _as_floats(row) -> list[float]:
    return [float(value) for value in row]
