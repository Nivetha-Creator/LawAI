"""Allow only citations that appear in the retrieved chunks.

Parsing is conservative. A section, article, act-plus-number, or URL is
accepted only when the same normalized reference was extracted from the
evidence (or, for one exact India Code homepage, from the standing
allow-list). Ranges, roman numerals, unknown act abbreviations, and other
syntax we cannot classify are rejected.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from app.rag.types import RetrievedChunk

# Exact homepages only. Paths, query strings, and other hosts are not included.
_INDIA_CODE_HOMEPAGES = frozenset(
    {
        "https://www.indiacode.nic.in",
        "http://www.indiacode.nic.in",
    }
)

_KNOWN_ACTS = frozenset(
    {
        "ipc",
        "bns",
        "bnss",
        "bsa",
        "crpc",
        "cpc",
        "iea",
        "mva",
        "pocso",
        "ndps",
        "hma",
    }
)

_URL = re.compile(
    r"https?://[^\s<>\"')\]]+|(?<![\w/])www\.[^\s<>\"')\]]+",
    re.IGNORECASE,
)
_RANGE = re.compile(
    r"(?:§{1,}|sections?|articles?|sec\.?|secs\.?|s\.|art\.?|arts\.)\s*"
    r"\d+[a-z]?(?:\(\d+\))?\s*(?:-|–|—|/|\bto\b)\s*\d+",
    re.IGNORECASE,
)
_LIST = re.compile(
    r"\b(?:sections?|articles?|sec\.?|secs\.?|s\.|art\.?|arts\.)\s*"
    r"\d+[a-z]?(?:\(\d+\))?(?:\s*(?:,|and)\s*\d+[a-z]?(?:\(\d+\))?)+",
    re.IGNORECASE,
)
_SECTION = re.compile(
    r"(?P<kind>§{1,2}|\b(?:sections?|articles?|sec\.?|secs\.?|s\.|art\.?|arts\.))"
    r"\s*(?P<num>\d+[a-z]?(?:\(\d+\))?)",
    re.IGNORECASE,
)
_ACT = re.compile(
    r"\b(?P<act>BNSS|BNS|BSA|IPC|Cr\.?\s*P\.?\s*C\.?|C\.?\s*P\.?\s*C\.?|"
    r"IEA|MVA|POCSO|NDPS|HMA)\b\s*[,:]?\s*(?P<num>\d+[a-z]?(?:\(\d+\))?)",
    re.IGNORECASE,
)
_LONG_ACT = re.compile(
    r"\b(?P<act>Indian\s+Penal\s+Code|Bharatiya\s+Nyaya\s+Sanhita|"
    r"Code\s+of\s+Criminal\s+Procedure|Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita|"
    r"Indian\s+Evidence\s+Act|Bharatiya\s+Sakshya(?:\s+Adhiniyam)?|"
    r"Motor\s+Vehicles\s+Act)\b\s*[,:]?\s*(?P<num>\d+[a-z]?(?:\(\d+\))?)",
    re.IGNORECASE,
)
_LONG_ACT_KEY = {
    "indianpenalcode": "ipc",
    "bharatiyanyayasanhita": "bns",
    "codeofcriminalprocedure": "crpc",
    "bharatiyanagariksurakshasanhita": "bnss",
    "indianevidenceact": "iea",
    "bharatiyasakshya": "bsa",
    "bharatiyasakshyaadhiniyam": "bsa",
    "motorvehiclesact": "mva",
}
_GENERIC_ACT = re.compile(
    r"\b(?P<act>[A-Z]{2,8})\s*[,:]?\s*(?P<num>\d{1,4}[A-Za-z]?(?:\(\d+\))?)\b"
)
_LEFTOVER_MARKER = re.compile(
    r"§+|\b(?:sections?|articles?|sec\.?|secs\.?|s\.|art\.?|arts\.)\b",
    re.IGNORECASE,
)


def _overlaps(spans: list[tuple[int, int]], start: int, end: int) -> bool:
    return any(start < stop and end > begin for begin, stop in spans)


def _normalize_act(raw: str) -> str:
    return re.sub(r"[^a-z0-9]", "", raw.lower())


def _normalize_url(raw: str) -> str | None:
    text = raw.strip().strip("<>").rstrip(".,);]>'\"")
    if not text:
        return None
    if text.lower().startswith("www."):
        text = "https://" + text
    try:
        parts = urlsplit(text)
    except ValueError:
        return None
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        return None
    if parts.username or parts.password:
        return None
    host = parts.hostname.lower() if parts.hostname else ""
    if not host:
        return None
    port = f":{parts.port}" if parts.port else ""
    path = parts.path.rstrip("/")
    query = f"?{parts.query}" if parts.query else ""
    return f"{parts.scheme.lower()}://{host}{port}{path}{query}"


def _kind_key(kind: str, number: str) -> str | None:
    token = kind.lower().strip(".")
    number = number.lower()
    if token.startswith("§"):
        if len(token) != 1:
            return None
        return f"section:{number}"
    if token.startswith("art"):
        return f"article:{number}"
    if token.startswith("sec") or token in {"s", "section", "sections"}:
        return f"section:{number}"
    return None


def _scan(text: str) -> tuple[set[str], bool]:
    """Return normalized citations and whether the text is ambiguous."""
    found: set[str] = set()
    spans: list[tuple[int, int]] = []
    ambiguous = False
    source = text or ""

    for match in _URL.finditer(source):
        spans.append(match.span())
        normalized = _normalize_url(match.group(0))
        if normalized is None:
            ambiguous = True
        else:
            found.add(f"url:{normalized}")

    for pattern in (_RANGE, _LIST):
        for match in pattern.finditer(source):
            spans.append(match.span())
            ambiguous = True

    for match in _SECTION.finditer(source):
        if _overlaps(spans, match.start(), match.end()):
            continue
        key = _kind_key(match.group("kind"), match.group("num"))
        spans.append(match.span())
        if key is None:
            ambiguous = True
        else:
            found.add(key)

    for match in _ACT.finditer(source):
        if _overlaps(spans, match.start(), match.end()):
            continue
        act = _normalize_act(match.group("act"))
        spans.append(match.span())
        if act not in _KNOWN_ACTS:
            ambiguous = True
        else:
            found.add(f"act:{act}:{match.group('num').lower()}")

    for match in _LONG_ACT.finditer(source):
        if _overlaps(spans, match.start(), match.end()):
            continue
        act = _LONG_ACT_KEY.get(_normalize_act(match.group("act")))
        spans.append(match.span())
        if act is None:
            ambiguous = True
        else:
            found.add(f"act:{act}:{match.group('num').lower()}")

    for match in _GENERIC_ACT.finditer(source):
        if _overlaps(spans, match.start(), match.end()):
            continue
        ambiguous = True
        spans.append(match.span())

    for match in _LEFTOVER_MARKER.finditer(source):
        if not _overlaps(spans, match.start(), match.end()):
            ambiguous = True

    return found, ambiguous


def allowed_citations(chunks: list[RetrievedChunk]) -> set[str]:
    """Citations that may be repeated. Ambiguous evidence syntax is not granted."""
    allowed = {f"url:{url}" for url in _INDIA_CODE_HOMEPAGES}
    for item in chunks:
        official = _normalize_url(item.chunk.official_url or "")
        if official:
            allowed.add(f"url:{official}")
        blob = f"{item.chunk.section}\n{item.chunk.text}\n{item.chunk.official_url}"
        found, _ambiguous = _scan(blob)
        allowed.update(found)
    return allowed


def citations_are_supported(text: str, chunks: list[RetrievedChunk]) -> bool:
    """False when a citation is missing, unknown, or not safely parsed.

    Ordinary numbers that are not attached to a citation marker stay allowed.
    """
    if not chunks:
        return False
    found, ambiguous = _scan(text or "")
    if ambiguous:
        return False
    allowed = allowed_citations(chunks)
    return all(item in allowed for item in found)
