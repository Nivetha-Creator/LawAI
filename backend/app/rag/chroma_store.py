"""Persistent Chroma store. The chromadb package is imported only when opened."""

from __future__ import annotations

import math
import uuid
from pathlib import Path
from typing import Any

from app.rag.errors import IncompleteIndexError, ModelMismatchError, StoreError
from app.rag.filters import metadata_accepts
from app.rag.publish import IndexPointer
from app.rag.types import Chunk, RetrievedChunk


class _PrecomputedEmbedding:
    """Placeholder so Chroma does not construct its default ONNX embedder."""

    @staticmethod
    def name() -> str:
        return "lawyerai-precomputed"

    def __call__(self, input):  # noqa: A002 — Chroma protocol name
        raise StoreError("Pass embeddings explicitly; this store does not embed text.")

    def embed_query(self, input):  # noqa: A002
        raise StoreError("Pass embeddings explicitly; this store does not embed text.")


def _import_chromadb():
    try:
        import chromadb
    except ImportError as exc:
        raise StoreError(
            'chromadb is not installed. pip install "chromadb>=0.5.5,<1.2"'
        ) from exc
    return chromadb


class ChromaVectorStore:
    def __init__(
        self,
        path: Path,
        embedding_model_id: str,
        *,
        collection_name: str = "legal_chunks",
        client: Any = None,
    ) -> None:
        self.path = path
        self.embedding_model_id = embedding_model_id
        self.default_name = collection_name
        self._client = client
        self._pointer = IndexPointer(path / "active_index.json")
        self._ef = _PrecomputedEmbedding()

    def _client_obj(self):
        if self._client is None:
            chromadb = _import_chromadb()
            self.path.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self.path))
        return self._client

    def _metadata(self, ready: str) -> dict[str, str]:
        return {
            "embedding_model_id": self.embedding_model_id,
            "index_ready": ready,
        }

    def _open(self, name: str, *, create: bool, from_pointer: bool = False) -> Any:
        client = self._client_obj()
        try:
            if create:
                collection = client.get_or_create_collection(
                    name=name,
                    metadata=self._metadata("false"),
                    embedding_function=self._ef,
                )
            else:
                collection = client.get_collection(
                    name=name,
                    embedding_function=self._ef,
                )
        except Exception as exc:  # noqa: BLE001 — surface store failures
            if from_pointer and not create:
                raise StoreError(
                    f"Active index pointer references unknown collection {name!r}."
                ) from exc
            raise StoreError("Vector store request failed.") from exc
        self._check_model(collection)
        return collection

    def _check_model(self, collection: Any) -> None:
        metadata = dict(getattr(collection, "metadata", None) or {})
        found = metadata.get("embedding_model_id")
        if found and found != self.embedding_model_id:
            raise ModelMismatchError(
                "Index embedding model does not match the configured embedder."
            )

    def begin_build(self) -> str:
        name = f"{self.default_name}_{uuid.uuid4().hex[:8]}"
        self._open(name, create=True)
        return name

    def mark_ready(self, name: str) -> None:
        collection = self._open(name, create=False)
        metadata = dict(collection.metadata or {})
        metadata["embedding_model_id"] = self.embedding_model_id
        metadata["index_ready"] = "true"
        collection.modify(metadata=metadata)

    def is_ready(self, name: str) -> bool:
        try:
            collection = self._open(name, create=False)
        except (StoreError, ModelMismatchError):
            return False
        return (collection.metadata or {}).get("index_ready") == "true"

    def activate(self, name: str) -> None:
        if not self.is_ready(name):
            raise IncompleteIndexError("Refusing to activate an incomplete index.")
        previous = self._published_name()
        self._pointer.write(name)
        try:
            current = self._pointer.active()
        except StoreError:
            current = ""
        if current != name:
            if previous:
                self._pointer.write(previous)
            raise StoreError("Active index pointer was not updated.")

    def active_collection(self) -> str:
        """Published collection only. Never substitutes ``default_name``."""
        return self._pointer.active()

    def _published_name(self) -> str | None:
        """Previous valid name, if any. A missing pointer is not a collection."""
        if not self._pointer.path.is_file():
            return None
        try:
            return self._pointer.active()
        except StoreError:
            return None

    def ids_and_hashes(self, document_id: str, *, collection: str) -> dict[str, str]:
        collection_obj = self._open(collection, create=True)
        try:
            found = collection_obj.get(where={"document_id": document_id})
        except Exception as exc:  # noqa: BLE001
            raise StoreError("Vector store request failed.") from exc
        ids = found.get("ids") or []
        metadatas = found.get("metadatas") or []
        pairs: dict[str, str] = {}
        for chunk_id, metadata in zip(ids, metadatas, strict=False):
            if metadata:
                pairs[chunk_id] = str(metadata.get("content_hash") or "")
        return pairs

    def delete_chunks(self, ids: list[str], *, collection: str) -> None:
        if not ids:
            return
        collection_obj = self._open(collection, create=True)
        try:
            collection_obj.delete(ids=ids)
        except Exception as exc:  # noqa: BLE001
            raise StoreError("Vector store request failed.") from exc

    def upsert_chunks(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        *,
        collection: str,
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ModelMismatchError("Embedding count does not match chunk count.")
        if not chunks:
            return
        width = len(embeddings[0])
        if any(len(vector) != width for vector in embeddings):
            raise ModelMismatchError("Embedding vectors have mixed sizes.")
        collection_obj = self._open(collection, create=True)
        metadata = dict(collection_obj.metadata or {})
        recorded = metadata.get("embedding_dimension")
        if recorded and recorded != str(width):
            raise ModelMismatchError("Embedding dimension does not match the index.")
        if not recorded:
            metadata["embedding_dimension"] = str(width)
            metadata["embedding_model_id"] = self.embedding_model_id
            metadata.setdefault("index_ready", "false")
            collection_obj.modify(metadata=metadata)
        try:
            collection_obj.upsert(
                ids=[chunk.chunk_id for chunk in chunks],
                documents=[chunk.text for chunk in chunks],
                metadatas=[chunk.metadata() for chunk in chunks],
                embeddings=embeddings,
            )
        except Exception as exc:  # noqa: BLE001
            raise StoreError("Vector store request failed.") from exc

    def query(
        self,
        embedding: list[float],
        *,
        collection: str | None = None,
        k: int = 4,
        where: dict[str, str] | None = None,
        max_distance: float | None = None,
    ) -> list[RetrievedChunk]:
        from_pointer = collection is None
        name = self.active_collection() if from_pointer else collection
        collection_obj = self._open(name, create=False, from_pointer=from_pointer)
        metadata = dict(collection_obj.metadata or {})
        if metadata.get("index_ready") != "true":
            raise StoreError("Active collection is not ready.")
        recorded = metadata.get("embedding_dimension")
        if recorded and recorded != str(len(embedding)):
            raise ModelMismatchError("Query vector size does not match the index.")
        try:
            found = collection_obj.query(
                query_embeddings=[embedding],
                n_results=k,
                where=where or None,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:  # noqa: BLE001
            raise StoreError("Vector store request failed.") from exc
        return _rows_from_query(found, max_distance, where)


def _finite_distance(raw: object) -> float | None:
    """Chroma default ``l2`` is squared Euclidean and should be >= 0.

    Missing, negative, and non-finite values are dropped. They are not
    treated as a perfect match.
    """
    try:
        distance = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(distance) or distance < 0:
        return None
    return distance


def _rows_from_query(
    found: dict,
    max_distance: float | None,
    where: dict | None = None,
) -> list[RetrievedChunk]:
    ids = (found.get("ids") or [[]])[0] or []
    documents = (found.get("documents") or [[]])[0] or []
    metadatas = (found.get("metadatas") or [[]])[0] or []
    distances = (found.get("distances") or [[]])[0] or []
    rows: list[RetrievedChunk] = []
    for index, chunk_id in enumerate(ids):
        if index >= len(distances):
            continue
        distance = _finite_distance(distances[index])
        if distance is None:
            continue
        if max_distance is not None and distance > max_distance:
            continue
        metadata = dict(metadatas[index] or {})
        metadata.setdefault("chunk_id", chunk_id)
        if not metadata_accepts(metadata, where):
            continue
        text = documents[index] if index < len(documents) else ""
        rows.append(RetrievedChunk(chunk=Chunk.from_metadata(text or "", metadata), distance=distance))
    return rows
