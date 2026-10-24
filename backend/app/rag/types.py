"""Document, chunk, and retrieval types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class DocumentRecord:
    """One local text file plus validated sidecar metadata."""

    document_id: str
    source_title: str
    official_url: str
    jurisdiction: str
    document_version: str
    text: str
    document_hash: str
    source_path: str
    section: str = ""
    effective_date: str = ""
    published_date: str = ""


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    text: str
    content_hash: str
    document_hash: str
    source_title: str
    official_url: str
    jurisdiction: str
    section: str
    effective_date: str
    published_date: str
    document_version: str
    source_path: str
    index: int

    def metadata(self) -> dict[str, str]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "content_hash": self.content_hash,
            "document_hash": self.document_hash,
            "source_title": self.source_title,
            "official_url": self.official_url,
            "jurisdiction": self.jurisdiction,
            "section": self.section,
            "effective_date": self.effective_date,
            "published_date": self.published_date,
            "document_version": self.document_version,
            "source_path": self.source_path,
            "index": str(self.index),
        }

    @staticmethod
    def from_metadata(text: str, metadata: dict[str, str]) -> Chunk:
        return Chunk(
            chunk_id=metadata.get("chunk_id", ""),
            document_id=metadata.get("document_id", ""),
            text=text,
            content_hash=metadata.get("content_hash", ""),
            document_hash=metadata.get("document_hash", ""),
            source_title=metadata.get("source_title", ""),
            official_url=metadata.get("official_url", ""),
            jurisdiction=metadata.get("jurisdiction", ""),
            section=metadata.get("section", ""),
            effective_date=metadata.get("effective_date", ""),
            published_date=metadata.get("published_date", ""),
            document_version=metadata.get("document_version", ""),
            source_path=metadata.get("source_path", ""),
            index=int(metadata.get("index") or 0),
        )


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    distance: float


RetrieveStatus = Literal["disabled", "empty", "hits", "error"]


@dataclass(frozen=True)
class RetrieveResult:
    status: RetrieveStatus
    chunks: list[RetrievedChunk] = field(default_factory=list)
    message: str = ""
