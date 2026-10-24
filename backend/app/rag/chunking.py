"""Split local documents into stable chunks."""

from __future__ import annotations

import hashlib
import re

from app.rag.types import Chunk, DocumentRecord

MAX_CHARS = 800
OVERLAP = 100


def content_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", (text or "").strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def file_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _section_slug(section: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (section or "").lower()).strip("-")
    return (slug or "body")[:40]


def chunk_id(document_id: str, section: str, index: int, digest: str) -> str:
    return f"{document_id}:{_section_slug(section)}:{index}:{digest[:12]}"


def _split_sections(text: str, default_section: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current = default_section or ""
    buffer: list[str] = []
    for line in text.splitlines():
        heading = re.match(r"^#{1,3}\s+(.+?)\s*$", line)
        if heading:
            body = "\n".join(buffer).strip()
            if body:
                sections.append((current, body))
            current = heading.group(1).strip()
            buffer = []
        else:
            buffer.append(line)
    tail = "\n".join(buffer).strip()
    if tail:
        sections.append((current, tail))
    return sections


def _pack(paragraphs: list[str]) -> list[str]:
    packed: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > MAX_CHARS:
            if current:
                packed.append(current)
                current = ""
            packed.extend(_hard_windows(paragraph))
            continue
        if not current:
            current = paragraph
            continue
        joined = f"{current}\n\n{paragraph}"
        if len(joined) <= MAX_CHARS:
            current = joined
        else:
            packed.append(current)
            tail = current[-OVERLAP:]
            current = f"{tail}\n\n{paragraph}".strip()
    if current:
        packed.append(current)
    return packed


def _hard_windows(text: str) -> list[str]:
    windows: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + MAX_CHARS)
        windows.append(text[start:end])
        if end >= len(text):
            break
        start = max(0, end - OVERLAP)
    return windows


def chunk_document(document: DocumentRecord) -> list[Chunk]:
    """Chunk a document. The same text and metadata always yield the same ids."""
    sections = _split_sections(document.text, document.section)
    chunks: list[Chunk] = []
    index = 0
    for section, body in sections:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", body) if part.strip()]
        for piece in _pack(paragraphs or [body]):
            digest = content_hash(piece)
            chunks.append(
                Chunk(
                    chunk_id=chunk_id(document.document_id, section, index, digest),
                    document_id=document.document_id,
                    text=piece,
                    content_hash=digest,
                    document_hash=document.document_hash,
                    source_title=document.source_title,
                    official_url=document.official_url,
                    jurisdiction=document.jurisdiction,
                    section=section,
                    effective_date=document.effective_date,
                    published_date=document.published_date,
                    document_version=document.document_version,
                    source_path=document.source_path,
                    index=index,
                )
            )
            index += 1
    return chunks
