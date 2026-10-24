"""In-memory vector store for tests and local dry runs."""

from __future__ import annotations

from app.rag.errors import ModelMismatchError
from app.rag.filters import metadata_accepts
from app.rag.types import Chunk, RetrievedChunk


class InMemoryVectorStore:
    def __init__(self, embedding_model_id: str, *, dimension: int | None = None) -> None:
        self.embedding_model_id = embedding_model_id
        self._dimension = dimension
        self._rows: dict[str, tuple[Chunk, list[float]]] = {}

    def ids_and_hashes(self, document_id: str, *, collection: str = "") -> dict[str, str]:
        del collection
        return {
            chunk.chunk_id: chunk.content_hash
            for chunk, _embedding in self._rows.values()
            if chunk.document_id == document_id
        }

    def delete_chunks(self, ids: list[str], *, collection: str = "") -> None:
        del collection
        for chunk_id in ids:
            self._rows.pop(chunk_id, None)

    def upsert_chunks(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        *,
        collection: str = "",
    ) -> None:
        del collection
        if len(chunks) != len(embeddings):
            raise ModelMismatchError("Embedding count does not match chunk count.")
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            self._check_dimension(embedding)
            self._rows[chunk.chunk_id] = (chunk, list(embedding))

    def query(
        self,
        embedding: list[float],
        *,
        collection: str | None = None,
        k: int = 4,
        where: dict[str, str] | None = None,
        max_distance: float | None = None,
    ) -> list[RetrievedChunk]:
        del collection
        self._check_dimension(embedding)
        scored: list[RetrievedChunk] = []
        for chunk, vector in self._rows.values():
            if not metadata_accepts(chunk.metadata(), where):
                continue
            distance = _squared_l2(embedding, vector)
            if max_distance is not None and distance > max_distance:
                continue
            scored.append(RetrievedChunk(chunk=chunk, distance=distance))
        scored.sort(key=lambda item: item.distance)
        return scored[:k]

    def count(self) -> int:
        return len(self._rows)

    def _check_dimension(self, embedding: list[float]) -> None:
        if self._dimension is None:
            self._dimension = len(embedding)
        if len(embedding) != self._dimension:
            raise ModelMismatchError("Query or document vector size does not match the index.")


def _squared_l2(left: list[float], right: list[float]) -> float:
    """Squared Euclidean distance.

    This matches Chroma's default ``l2`` space (sum of squared differences,
    not the square root). Lower is closer. The value is unbounded above zero.
    """
    return sum((a - b) ** 2 for a, b in zip(left, right, strict=False))
