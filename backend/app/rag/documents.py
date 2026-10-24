"""Load .txt/.md files that sit beside a required document.json sidecar."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.rag.chunking import file_hash
from app.rag.errors import CorpusPathError, DocumentValidationError
from app.rag.types import DocumentRecord

_REQUIRED = ("source_title", "official_url", "jurisdiction", "document_version")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DOC_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,80}$")


def assert_inside(root: Path, path: Path) -> Path:
    """Resolve ``path`` and reject anything outside ``root``."""
    root_resolved = root.resolve()
    candidate = path.resolve()
    if not candidate.is_relative_to(root_resolved):
        raise CorpusPathError("Path is outside the corpus root.")
    return candidate


def _require_text(payload: dict, key: str, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DocumentValidationError(f"{label} is missing required metadata '{key}'.")
    return value.strip()


def _optional_date(payload: dict, key: str, label: str) -> str:
    if key not in payload or payload[key] in (None, ""):
        return ""
    value = payload[key]
    if not isinstance(value, str) or not _DATE.match(value.strip()):
        raise DocumentValidationError(
            f"{label} has invalid {key}. Use YYYY-MM-DD or omit the field."
        )
    return value.strip()


def _optional_section(payload: dict, label: str) -> str:
    if "section" not in payload or payload["section"] in (None, ""):
        return ""
    value = payload["section"]
    if not isinstance(value, str):
        raise DocumentValidationError(f"{label} section must be a string.")
    return value.strip()


def _document_id(payload: dict, directory: Path) -> str:
    raw = payload.get("document_id")
    if raw in (None, ""):
        slug = re.sub(r"[^a-z0-9]+", "-", directory.name.lower()).strip("-")
        if not slug or not _DOC_ID.match(slug):
            raise DocumentValidationError(
                f"{directory.name} needs a document_id (lowercase letters, numbers, _ or -)."
            )
        return slug
    if not isinstance(raw, str) or not _DOC_ID.match(raw.strip()):
        raise DocumentValidationError(
            f"{directory.name} document_id must be a short lowercase slug."
        )
    return raw.strip()


def _validate_url(url: str, label: str) -> str:
    if not (url.startswith("https://") or url.startswith("http://")):
        raise DocumentValidationError(f"{label} official_url must start with http:// or https://.")
    return url


def load_document_dir(root: Path, directory: Path) -> DocumentRecord:
    """Load one document directory. Does not invent titles, URLs, sections, or dates."""
    root_resolved = root.resolve()
    directory = assert_inside(root_resolved, directory)
    if not directory.is_dir():
        raise DocumentValidationError("Document path is not a directory.")
    sidecar = directory / "document.json"
    if not sidecar.is_file():
        raise DocumentValidationError(f"{directory.name} is missing document.json.")
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DocumentValidationError(f"{directory.name} document.json is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise DocumentValidationError(f"{directory.name} document.json must be an object.")

    label = directory.name
    title = _require_text(payload, "source_title", label)
    url = _validate_url(_require_text(payload, "official_url", label), label)
    jurisdiction = _require_text(payload, "jurisdiction", label)
    version = _require_text(payload, "document_version", label)
    texts = sorted(
        [path for path in directory.iterdir() if path.suffix.lower() in {".md", ".txt"} and path.is_file()]
    )
    if len(texts) != 1:
        raise DocumentValidationError(
            f"{label} must contain exactly one .md or .txt file next to document.json."
        )
    text_path = assert_inside(root_resolved, texts[0])
    raw = text_path.read_bytes()
    try:
        body = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DocumentValidationError(f"{label} text file must be UTF-8.") from exc
    if not body.strip():
        raise DocumentValidationError(f"{label} text file is empty.")
    relative = text_path.relative_to(root_resolved).as_posix()
    return DocumentRecord(
        document_id=_document_id(payload, directory),
        source_title=title,
        official_url=url,
        jurisdiction=jurisdiction,
        document_version=version,
        text=body,
        document_hash=file_hash(raw),
        source_path=relative,
        section=_optional_section(payload, label),
        effective_date=_optional_date(payload, "effective_date", label),
        published_date=_optional_date(payload, "published_date", label),
    )


def load_corpus(root: Path) -> list[DocumentRecord]:
    """Load every document directory under ``root``."""
    root_resolved = root.resolve()
    if not root_resolved.is_dir():
        raise DocumentValidationError("Corpus root is not a directory.")
    documents: list[DocumentRecord] = []
    for sidecar in sorted(root_resolved.rglob("document.json")):
        sidecar = assert_inside(root_resolved, sidecar)
        documents.append(load_document_dir(root_resolved, sidecar.parent))
    return documents
