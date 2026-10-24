"""Render retrieved chunks inside a reply. No extra citations are added."""

from __future__ import annotations

from app.rag.types import RetrievedChunk


def evidence_block(chunks: list[RetrievedChunk]) -> str:
    parts: list[str] = []
    for item in chunks:
        chunk = item.chunk
        section = chunk.section or "(no section label)"
        parts.append(
            "\n".join(
                [
                    f"[{chunk.chunk_id}]",
                    f"Title: {chunk.source_title}",
                    f"Section: {section}",
                    f"URL: {chunk.official_url}",
                    f"Jurisdiction: {chunk.jurisdiction}",
                    f"Version: {chunk.document_version}",
                    chunk.text,
                ]
            )
        )
    return "\n\n".join(parts)


def format_excerpts(chunks: list[RetrievedChunk]) -> str:
    lines = [
        "",
        "**Retrieved excerpts**",
        "These are quotations from the local index. They are **not** a verified legal opinion "
        "and **not** a generated answer.",
        "",
    ]
    for item in chunks:
        chunk = item.chunk
        section = chunk.section or "(no section label)"
        lines.append(f"- **{chunk.source_title}** — {section}")
        lines.append(f"  Source: {chunk.official_url}")
        lines.append(f"  {chunk.text}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_source_footer(chunks: list[RetrievedChunk]) -> str:
    lines = ["", "**Sources used**"]
    for item in chunks:
        chunk = item.chunk
        section = f" — {chunk.section}" if chunk.section else ""
        lines.append(f"- {chunk.source_title}{section} ({chunk.official_url})")
    return "\n".join(lines)
