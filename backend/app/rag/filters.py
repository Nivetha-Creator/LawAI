"""Optional retrieval filters.

Jurisdiction and effective date are applied only when the caller can name
them reliably. Missing metadata is never filled in, and ``document_version``
is never treated as an effective date.
"""

from __future__ import annotations

import re
from datetime import datetime

_ISO_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_JURISDICTION = re.compile(r"\bjurisdiction\s*[:=]\s*(\S+)", re.IGNORECASE)
_RANGE_OPS = frozenset({"$gt", "$gte", "$lt", "$lte"})
# When an as-of date is set, nearest neighbors that fail the date check must
# not hide an eligible chunk. Ask the store for this many candidates at most,
# then keep at most ``k`` that pass. This is not a full scan.
DATE_CANDIDATE_LIMIT = 32


def is_iso_date(value: str) -> bool:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        return False
    return parsed.strftime("%Y-%m-%d") == value


def filters_from_text(text: str) -> tuple[str | None, str | None]:
    """Return ``(jurisdiction, as_of)`` or ``(None, None)`` when unknown.

    Jurisdiction is taken only from a single explicit ``jurisdiction: TOKEN``
    (or ``jurisdiction=TOKEN``) marker. City and state words are not mapped
    onto corpus labels.

    ``as_of`` is taken only when the text contains one valid ``YYYY-MM-DD``
    date. Natural-language dates are ignored. Several different ISO dates are
    treated as ambiguous and do not create a filter.
    """
    labels: list[str] = []
    for match in _JURISDICTION.finditer(text or ""):
        label = match.group(1).strip(".,);]")
        if label:
            labels.append(label)
    jurisdiction = labels[0] if len(set(labels)) == 1 else None

    dates = [item for item in _ISO_DATE.findall(text or "") if is_iso_date(item)]
    unique = list(dict.fromkeys(dates))
    as_of = unique[0] if len(unique) == 1 else None
    return jurisdiction, as_of


def build_where(jurisdiction: str | None, as_of: str | None) -> dict | None:
    """Chroma ``where`` document. Only jurisdiction equality is included.

    Chroma 1.1 rejects ``$gte`` / ``$lte`` unless the operand is a number, and
    it rejects more than one operator in a single field clause. ``as_of`` is
    validated here and applied later by ``passes_as_of``. A blank jurisdiction
    adds no clause.
    """
    if as_of is not None and not is_iso_date(as_of):
        raise ValueError("as_of must be a real YYYY-MM-DD date.")
    if jurisdiction and str(jurisdiction).strip():
        return {"jurisdiction": str(jurisdiction).strip()}
    return None


def candidate_limit(k: int, as_of: str | None) -> int:
    """Neighbors to request. As-of queries over-fetch up to a fixed cap."""
    if k < 1:
        raise ValueError("k must be at least 1.")
    if not as_of:
        return k
    return min(max(k * 8, k), max(DATE_CANDIDATE_LIMIT, k))


def passes_as_of(metadata: dict, as_of: str | None) -> bool:
    """True when no as-of date is set, or ``effective_date`` is on or before it.

    Missing, blank, and invalid effective dates fail when a date is requested.
    ``document_version`` and ``published_date`` are ignored.
    """
    if as_of is None:
        return True
    if not is_iso_date(as_of):
        raise ValueError("as_of must be a real YYYY-MM-DD date.")
    actual = metadata.get("effective_date")
    text = "" if actual is None else str(actual).strip()
    if not is_iso_date(text):
        return False
    return text <= as_of


def contains_range_operator(where: dict | None) -> bool:
    """True when a Chroma where document contains an inequality operator."""
    if not isinstance(where, dict):
        return False
    for key, value in where.items():
        if key in _RANGE_OPS:
            return True
        if isinstance(value, dict) and contains_range_operator(value):
            return True
        if isinstance(value, list):
            if any(isinstance(item, dict) and contains_range_operator(item) for item in value):
                return True
    return False


def metadata_accepts(metadata: dict, where: dict | None) -> bool:
    """True when chunk metadata satisfies ``where``.

    A date comparison never matches a blank or invalid ``effective_date``.
    """
    if not where:
        return True
    if "$and" in where:
        return all(metadata_accepts(metadata, clause) for clause in where["$and"])
    if "$or" in where:
        return any(metadata_accepts(metadata, clause) for clause in where["$or"])
    for key, expected in where.items():
        if str(key).startswith("$"):
            return False
        actual = "" if metadata.get(key) is None else str(metadata.get(key))
        if isinstance(expected, dict):
            if not _date_ops(actual, expected):
                return False
        elif actual != str(expected):
            return False
    return True


def _date_ops(actual: str, ops: dict) -> bool:
    if not is_iso_date(actual):
        return False
    for op, raw in ops.items():
        bound = str(raw)
        if op == "$eq" and actual != bound:
            return False
        if op == "$lte" and actual > bound:
            return False
        if op == "$gte" and actual < bound:
            return False
        if op not in {"$eq", "$lte", "$gte"}:
            return False
    return True
