"""Ingest a local corpus into a vector store. No network and no scraping."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from app.rag.chunking import chunk_document
from app.rag.documents import load_corpus
from app.rag.embeddings import EmbeddingProvider, FakeEmbedder, LocalMiniLMEmbedder
from app.rag.errors import (
    CorpusPathError,
    DocumentValidationError,
    EmbeddingDependencyError,
    IncompleteIndexError,
    ModelMismatchError,
    StoreError,
)
from app.rag.types import DocumentRecord


@dataclass
class IngestStats:
    documents: int = 0
    upserted: int = 0
    skipped_unchanged: int = 0
    deleted_stale: int = 0


def ingest_documents(
    documents: list[DocumentRecord],
    store,
    embedder: EmbeddingProvider,
    *,
    collection: str,
) -> IngestStats:
    if getattr(store, "embedding_model_id", None) not in {None, embedder.model_id}:
        raise ModelMismatchError("Store embedding model does not match the embedder.")
    stats = IngestStats()
    for document in documents:
        stats.documents += 1
        chunks = chunk_document(document)
        desired = {chunk.chunk_id: chunk.content_hash for chunk in chunks}
        existing = store.ids_and_hashes(document.document_id, collection=collection)
        if existing == desired:
            stats.skipped_unchanged += 1
            continue
        stale = [chunk_id for chunk_id in existing if chunk_id not in desired]
        if stale:
            store.delete_chunks(stale, collection=collection)
            stats.deleted_stale += len(stale)
        if not chunks:
            continue
        vectors = embedder.embed_documents([chunk.text for chunk in chunks])
        if any(len(vector) != embedder.dimension for vector in vectors):
            raise ModelMismatchError("Embedder returned an unexpected vector size.")
        store.upsert_chunks(chunks, vectors, collection=collection)
        stats.upserted += len(chunks)
    return stats


def ingest_corpus(root: Path, store, embedder: EmbeddingProvider, *, collection: str) -> IngestStats:
    documents = load_corpus(root)
    return ingest_documents(documents, store, embedder, collection=collection)


def _embedder_from_env() -> EmbeddingProvider:
    name = os.getenv("LAWYERAI_EMBEDDING_PROVIDER", "local-minilm").strip().lower() or "local-minilm"
    if name == "fake-test":
        return FakeEmbedder()
    if name == "local-minilm":
        return LocalMiniLMEmbedder()
    raise EmbeddingDependencyError(
        "Unsupported embedding provider. This build supports local-minilm only."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest a local LawyerAI corpus into Chroma.")
    parser.add_argument("--corpus-root", required=True, help="Directory of document folders")
    parser.add_argument(
        "--chroma-path",
        default=os.getenv("LAWYERAI_CHROMA_PATH", "data/chroma"),
        help="Persistent Chroma directory",
    )
    args = parser.parse_args(argv)
    root = Path(args.corpus_root)
    try:
        root = root.resolve()
        if not root.is_dir():
            print("Corpus root is not a directory.", file=sys.stderr)
            return 2
        from app.rag.chroma_store import ChromaVectorStore

        embedder = _embedder_from_env()
        store = ChromaVectorStore(Path(args.chroma_path), embedder.model_id)
        collection = store.begin_build()
        stats = ingest_corpus(root, store, embedder, collection=collection)
        store.mark_ready(collection)
        store.activate(collection)
    except (
        DocumentValidationError,
        CorpusPathError,
        ModelMismatchError,
        IncompleteIndexError,
        EmbeddingDependencyError,
        StoreError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(
        "Ingested "
        f"{stats.documents} documents, upserted {stats.upserted} chunks, "
        f"skipped {stats.skipped_unchanged} unchanged, deleted {stats.deleted_stale} stale."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
