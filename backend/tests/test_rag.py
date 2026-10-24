"""RAG unit tests. No model download and no network."""

import json
import sys

import pytest

from app.rag.chunking import chunk_document
from app.rag.citations import citations_are_supported
from app.rag.chroma_store import ChromaVectorStore
from app.rag.documents import assert_inside, load_corpus, load_document_dir
from app.rag.embeddings import FakeEmbedder, LocalMiniLMEmbedder
from app.rag.errors import (
    CorpusPathError,
    DocumentValidationError,
    EmbeddingDependencyError,
    IncompleteIndexError,
    ModelMismatchError,
    StoreError,
)
from app.rag.ingest import ingest_documents, main as ingest_main
from app.rag.memory_store import InMemoryVectorStore
from app.rag.filters import filters_from_text
from app.rag.retrieve import PROVISIONAL_MAX_DISTANCE, configured_max_distance, rag_enabled, retrieve_for_query
from app.rag.types import Chunk, RetrievedChunk, RetrieveResult


def _write_doc(root, name, text, **overrides):
    folder = root / name
    folder.mkdir()
    (folder / "body.md").write_text(text, encoding="utf-8")
    payload = {
        "source_title": "Fixture Note",
        "official_url": "https://example.test/fixture",
        "jurisdiction": "IN-TEST",
        "document_version": "v0",
    }
    payload.update(overrides)
    (folder / "document.json").write_text(json.dumps(payload), encoding="utf-8")
    return folder


def _chunk(**overrides) -> RetrievedChunk:
    data = dict(
        chunk_id="fixture:body:0:abc",
        document_id="fixture",
        text="Synthetic fixture text about a sample rule. Not legislation.",
        content_hash="abc",
        document_hash="doc",
        source_title="Fixture Note",
        official_url="https://example.test/fixture",
        jurisdiction="IN-TEST",
        section="",
        effective_date="",
        published_date="",
        document_version="v0",
        source_path="fixture/body.md",
        index=0,
    )
    data.update(overrides)
    return RetrievedChunk(chunk=Chunk(**data), distance=0.0)


def test_chunk_ids_are_stable_and_change_when_text_changes(tmp_path):
    _write_doc(tmp_path, "fixture", "Synthetic fixture paragraph. Not legislation.\n")
    document = load_document_dir(tmp_path, tmp_path / "fixture")
    first = chunk_document(document)
    second = chunk_document(document)
    assert [item.chunk_id for item in first] == [item.chunk_id for item in second]
    assert first[0].source_title == "Fixture Note"
    assert first[0].official_url == "https://example.test/fixture"
    assert first[0].effective_date == ""
    assert first[0].section == ""
    changed = document.__class__(**{**document.__dict__, "text": document.text + " Extra sentence."})
    assert chunk_document(changed)[0].chunk_id != first[0].chunk_id


def test_heading_section_is_kept():
    from app.rag.types import DocumentRecord

    document = DocumentRecord(
        document_id="fixture",
        source_title="Fixture Note",
        official_url="https://example.test/fixture",
        jurisdiction="IN-TEST",
        document_version="v0",
        text="## Sample heading\n\nSynthetic body. Not legislation.\n",
        document_hash="hash",
        source_path="fixture/body.md",
        section="",
    )
    chunks = chunk_document(document)
    assert chunks[0].section == "Sample heading"


def test_malformed_sidecar_and_path_escape(tmp_path):
    folder = _write_doc(tmp_path, "broken", "text\n", source_title="")
    with pytest.raises(DocumentValidationError, match="source_title"):
        load_document_dir(tmp_path, folder)

    dated = _write_doc(tmp_path, "dated", "text\n", effective_date="March 1")
    with pytest.raises(DocumentValidationError, match="effective_date"):
        load_document_dir(tmp_path, dated)

    outside = tmp_path / "secret.md"
    outside.write_text("secret", encoding="utf-8")
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    with pytest.raises(CorpusPathError):
        assert_inside(corpus, outside)

    evil = corpus / "evil"
    evil.mkdir()
    (evil / "document.json").write_text(
        json.dumps(
            {
                "source_title": "Fixture Note",
                "official_url": "https://example.test/fixture",
                "jurisdiction": "IN-TEST",
                "document_version": "v0",
                "body_path": "../secret.md",
            }
        ),
        encoding="utf-8",
    )
    (evil / "body.md").symlink_to(outside)
    with pytest.raises(CorpusPathError):
        load_document_dir(corpus, evil)


def test_missing_optional_dates_are_blank(tmp_path):
    _write_doc(tmp_path, "plain", "Synthetic text. Not legislation.\n")
    document = load_document_dir(tmp_path, tmp_path / "plain")
    assert document.effective_date == ""
    assert document.published_date == ""
    assert document.section == ""


def test_citation_allow_list_rejects_unknown_url_and_section():
    chunk = _chunk(text="Synthetic fixture. section 4 applies in this sample only.")
    assert citations_are_supported(
        "See section 4 and https://example.test/fixture",
        [chunk],
    )
    assert citations_are_supported(
        "Check https://www.indiacode.nic.in for official text.",
        [chunk],
    )
    assert citations_are_supported("No citation here.", [chunk]) is True
    assert citations_are_supported(
        "There were 2 vehicles on 12 March 2025 and the distance was 25 km.",
        [chunk],
    )
    assert citations_are_supported("See https://evil.example/no", [chunk]) is False
    assert citations_are_supported("Read section 999.", [chunk]) is False
    assert citations_are_supported("The Indian Penal Code was replaced.", [chunk]) is True


def test_fabricated_citation_forms_are_rejected():
    chunk = _chunk(text="Synthetic fixture. section 4 applies in this sample only.")
    rejected = (
        "§ 302",
        "Sec 302",
        "s.302",
        "Article 21",
        "IPC 302",
        "BNS 103",
        "www.evil.example/act",
        "https://evil.example/no",
        "https://www.indiacode.nic.in/handle/123456789/1",
        "Indian Penal Code 302",
        "section IV",
        "sections 4-6",
        "§§ 4",
    )
    for text in rejected:
        assert citations_are_supported(text, [chunk]) is False, text


def test_supported_citation_and_exact_india_code_homepage():
    chunk = _chunk(
        text="Synthetic fixture. section 4 applies. BNS 103 is quoted here only as a sample.",
        section="Section 4",
    )
    assert citations_are_supported("The note mentions § 4 and BNS 103.", [chunk]) is True
    assert citations_are_supported("https://www.indiacode.nic.in/", [chunk]) is True
    assert citations_are_supported("http://www.indiacode.nic.in", [chunk]) is True
    assert citations_are_supported("IPC 302", [chunk]) is False


def test_fake_embedder_is_deterministic():
    embedder = FakeEmbedder()
    assert embedder.dimension == 8
    assert embedder.model_id == "fake-test"
    assert embedder.embed_query("same") == embedder.embed_query("same")
    assert embedder.embed_query("same") != embedder.embed_query("other")
    assert len(embedder.embed_documents(["a", "b"])) == 2


def test_local_embedder_does_not_download_when_chromadb_missing():
    if sys.modules.get("chromadb") is not None or __import__("importlib").util.find_spec("chromadb"):
        pytest.skip("chromadb is installed")
    with pytest.raises(EmbeddingDependencyError, match="chromadb"):
        LocalMiniLMEmbedder().embed_query("synthetic query")


def test_memory_upsert_filter_empty_and_dimension():
    embedder = FakeEmbedder()
    store = InMemoryVectorStore(embedder.model_id, dimension=embedder.dimension)
    assert store.query(embedder.embed_query("nothing"), k=4) == []
    document_chunks = []
    from app.rag.types import DocumentRecord

    for doc_id, jurisdiction, text in (
        ("alpha", "IN-TEST", "alpha synthetic rule"),
        ("beta", "OTHER", "beta synthetic rule"),
    ):
        document = DocumentRecord(
            document_id=doc_id,
            source_title=doc_id,
            official_url="https://example.test/fixture",
            jurisdiction=jurisdiction,
            document_version="v0",
            text=text,
            document_hash=doc_id,
            source_path=f"{doc_id}/body.md",
        )
        document_chunks.extend(chunk_document(document))
    vectors = embedder.embed_documents([item.text for item in document_chunks])
    store.upsert_chunks(document_chunks, vectors)
    alpha_vector = embedder.embed_query("alpha synthetic rule")
    only_alpha = store.query(alpha_vector, where={"jurisdiction": "IN-TEST"})
    assert len(only_alpha) == 1
    assert only_alpha[0].chunk.document_id == "alpha"
    with pytest.raises(ModelMismatchError):
        store.query([0.1, 0.2, 0.3])


def test_ingest_is_idempotent_and_drops_stale_chunks(tmp_path):
    _write_doc(tmp_path, "alpha", "Alpha synthetic text. Not legislation.\n")
    _write_doc(tmp_path, "beta", "Beta synthetic text. Not legislation.\n")
    embedder = FakeEmbedder()
    calls = {"n": 0}
    real = embedder.embed_documents

    def counting(texts):
        calls["n"] += 1
        return real(texts)

    embedder.embed_documents = counting
    store = InMemoryVectorStore(embedder.model_id, dimension=embedder.dimension)
    documents = load_corpus(tmp_path)
    first = ingest_documents(documents, store, embedder, collection="c1")
    assert first.upserted == 2
    assert store.count() == 2
    second = ingest_documents(documents, store, embedder, collection="c1")
    assert second.skipped_unchanged == 2
    assert second.upserted == 0
    assert calls["n"] == 2
    alpha = next(item for item in documents if item.document_id == "alpha")
    edited = alpha.__class__(**{**alpha.__dict__, "text": "Alpha text was edited. Not legislation.\n"})
    others = [item for item in documents if item.document_id != "alpha"]
    third = ingest_documents([edited, *others], store, embedder, collection="c1")
    assert third.deleted_stale == 1
    assert store.count() == 2
    ids = store.ids_and_hashes("alpha", collection="c1")
    assert ids
    assert "Alpha text was edited" in next(iter(store._rows.values()))[0].text or any(
        "edited" in row[0].text for row in store._rows.values()
    )
    assert any(row[0].document_id == "beta" for row in store._rows.values())


class _Col:
    def __init__(self, name, metadata):
        self.name = name
        self.metadata = dict(metadata or {})
        self.rows = {}
        self.fail = False

    def upsert(self, ids, documents, metadatas, embeddings):
        for index, chunk_id in enumerate(ids):
            self.rows[chunk_id] = {
                "document": documents[index],
                "metadata": metadatas[index],
                "embedding": embeddings[index],
            }

    def delete(self, ids):
        for chunk_id in ids:
            self.rows.pop(chunk_id, None)

    def get(self, where=None, include=None):
        del include
        matched = [
            (chunk_id, row)
            for chunk_id, row in self.rows.items()
            if _meta_match(row["metadata"], where)
        ]
        return {
            "ids": [chunk_id for chunk_id, _row in matched],
            "metadatas": [row["metadata"] for _chunk_id, row in matched],
            "documents": [row["document"] for _chunk_id, row in matched],
        }

    def query(self, query_embeddings, n_results, where=None, include=None):
        del include
        if self.fail:
            raise RuntimeError("store offline")
        query = query_embeddings[0]
        scored = []
        for chunk_id, row in self.rows.items():
            if not _meta_match(row["metadata"], where):
                continue
            # Squared L2, matching Chroma's default l2 (not the square root).
            distance = sum((a - b) ** 2 for a, b in zip(query, row["embedding"]))
            scored.append((distance, chunk_id, row))
        scored.sort(key=lambda item: item[0])
        scored = scored[:n_results]
        return {
            "ids": [[item[1] for item in scored]],
            "documents": [[item[2]["document"] for item in scored]],
            "metadatas": [[item[2]["metadata"] for item in scored]],
            "distances": [[item[0] for item in scored]],
        }

    def modify(self, metadata):
        self.metadata = dict(metadata)

    def count(self):
        return len(self.rows)


def _meta_match(metadata, where):
    from app.rag.filters import metadata_accepts

    return metadata_accepts(metadata, where)


class _Client:
    def __init__(self):
        self.cols = {}

    def get_or_create_collection(self, name, metadata=None, embedding_function=None):
        del embedding_function
        if name not in self.cols:
            self.cols[name] = _Col(name, metadata)
        return self.cols[name]

    def get_collection(self, name, embedding_function=None):
        del embedding_function
        if name not in self.cols:
            raise ValueError("missing collection")
        return self.cols[name]


def test_chroma_wrapper_upsert_filter_empty_failure_and_publish(tmp_path):
    client = _Client()
    embedder = FakeEmbedder()
    store = ChromaVectorStore(
        tmp_path / "chroma",
        embedder.model_id,
        client=client,
    )
    built = store.begin_build()
    with pytest.raises(IncompleteIndexError):
        store.activate(built)
    with pytest.raises(StoreError, match="missing"):
        store._pointer.active()
    assert not (tmp_path / "chroma" / "active_index.json").exists()

    ready = store.begin_build()
    store.mark_ready(ready)
    store.activate(ready)
    assert store.query(embedder.embed_query("empty"), k=3) == []

    from app.rag.types import DocumentRecord

    chunks = []
    for doc_id, jurisdiction, text in (
        ("alpha", "IN-TEST", "alpha synthetic rule"),
        ("beta", "OTHER", "beta synthetic rule"),
    ):
        chunks.extend(
            chunk_document(
                DocumentRecord(
                    document_id=doc_id,
                    source_title=doc_id,
                    official_url="https://example.test/fixture",
                    jurisdiction=jurisdiction,
                    document_version="v0",
                    text=text,
                    document_hash=doc_id,
                    source_path=f"{doc_id}/body.md",
                )
            )
        )
    store.upsert_chunks(
        chunks,
        embedder.embed_documents([item.text for item in chunks]),
        collection=ready,
    )
    # upsert's dimension write must not clear the ready flag before query
    store.mark_ready(ready)
    found = store.query(
        embedder.embed_query("alpha synthetic rule"),
        where={"jurisdiction": "IN-TEST"},
    )
    assert len(found) == 1
    assert found[0].chunk.jurisdiction == "IN-TEST"
    assert found[0].chunk.source_title == "alpha"

    client.cols[ready].fail = True
    with pytest.raises(StoreError):
        store.query(embedder.embed_query("alpha synthetic rule"))

    mismatched = ChromaVectorStore(
        tmp_path / "chroma",
        "other-model",
        client=client,
        collection_name=ready,
    )
    with pytest.raises(ModelMismatchError):
        mismatched.query(embedder.embed_query("alpha synthetic rule"))


def test_invalid_active_pointer_fails_closed(tmp_path):
    sys.modules.pop("chromadb", None)
    client = _Client()
    embedder = FakeEmbedder()
    path = tmp_path / "chroma"
    store = ChromaVectorStore(path, embedder.model_id, client=client)
    vector = embedder.embed_query("synthetic reopen query")
    pointer = path / "active_index.json"
    decoy = client.get_or_create_collection(
        "legal_chunks",
        metadata={"embedding_model_id": embedder.model_id, "index_ready": "true"},
    )
    decoy.rows["decoy"] = {
        "document": "decoy must not be returned",
        "metadata": {"chunk_id": "decoy", "document_id": "decoy"},
        "embedding": vector,
    }
    decoy.fail = True

    with pytest.raises(StoreError, match="Active index pointer is missing"):
        store.query(vector)
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text("{", encoding="utf-8")
    with pytest.raises(StoreError, match="corrupt"):
        store.query(vector)
    pointer.write_text('{"ready": true}\n', encoding="utf-8")
    with pytest.raises(StoreError, match="missing a collection name"):
        store.query(vector)
    pointer.write_text('{"active_collection": "  "}\n', encoding="utf-8")
    with pytest.raises(StoreError, match="empty collection name"):
        store.query(vector)
    pointer.write_text('{"active_collection": "does-not-exist"}\n', encoding="utf-8")
    with pytest.raises(StoreError, match="unknown collection 'does-not-exist'"):
        store.query(vector)
    assert "chromadb" not in sys.modules

    ready = store.begin_build()
    from app.rag.types import DocumentRecord

    document = DocumentRecord(
        document_id="alpha",
        source_title="Alpha",
        official_url="https://example.test/fixture",
        jurisdiction="IN-TEST",
        document_version="v0",
        text="Alpha synthetic rule for reopen.",
        document_hash="1",
        source_path="alpha/body.md",
    )
    chunks = chunk_document(document)
    store.upsert_chunks(chunks, embedder.embed_documents([item.text for item in chunks]), collection=ready)
    store.mark_ready(ready)
    store.activate(ready)
    reopened = ChromaVectorStore(path, embedder.model_id, client=client)
    found = reopened.query(embedder.embed_query("Alpha synthetic rule for reopen."))
    assert reopened.active_collection() == ready
    assert len(found) == 1
    assert found[0].chunk.document_id == "alpha"
    assert "decoy" not in found[0].chunk.text


def test_chroma_reingest_removes_stale_chunk(tmp_path):
    client = _Client()
    embedder = FakeEmbedder()
    store = ChromaVectorStore(
        path=tmp_path / "chroma",
        embedding_model_id=embedder.model_id,
        client=client,
    )
    name = store.begin_build()
    from app.rag.types import DocumentRecord

    original = DocumentRecord(
        document_id="alpha",
        source_title="Alpha",
        official_url="https://example.test/fixture",
        jurisdiction="IN-TEST",
        document_version="v0",
        text="Original synthetic alpha. Not legislation.",
        document_hash="1",
        source_path="alpha/body.md",
    )
    other = DocumentRecord(
        document_id="beta",
        source_title="Beta",
        official_url="https://example.test/fixture",
        jurisdiction="IN-TEST",
        document_version="v0",
        text="Beta stays. Not legislation.",
        document_hash="2",
        source_path="beta/body.md",
    )
    ingest_documents([original, other], store, embedder, collection=name)
    again = ingest_documents([original, other], store, embedder, collection=name)
    assert again.skipped_unchanged == 2
    assert len(client.cols[name].rows) == 2
    edited = original.__class__(**{**original.__dict__, "text": "Edited synthetic alpha. Not legislation."})
    stats = ingest_documents([edited, other], store, embedder, collection=name)
    assert stats.deleted_stale == 1
    texts = [row["document"] for row in client.cols[name].rows.values()]
    assert any("Edited synthetic alpha" in text for text in texts)
    assert any("Beta stays" in text for text in texts)
    assert all("Original synthetic" not in text for text in texts)


def test_rag_disabled_does_not_import_chromadb(monkeypatch):
    monkeypatch.delenv("LAWYERAI_RAG_ENABLED", raising=False)
    sys.modules.pop("chromadb", None)
    assert rag_enabled() is False
    result = retrieve_for_query("synthetic question that must not be logged")
    assert result.status == "disabled"
    assert "chromadb" not in sys.modules
    assert "synthetic question" not in result.message


def test_enabled_without_chromadb_is_an_error_not_a_crash(monkeypatch):
    if __import__("importlib").util.find_spec("chromadb"):
        pytest.skip("chromadb is installed")
    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    result = retrieve_for_query("synthetic question")
    assert result.status == "error"
    assert result.message == "retrieval_unavailable"
    assert "synthetic" not in result.message


def _hit(distance, **overrides) -> RetrievedChunk:
    item = _chunk(**overrides)
    return RetrievedChunk(chunk=item.chunk, distance=distance)


class _RecordingStore:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []
        self.embedding_model_id = "fake-test"

    def query(self, embedding, k=4, where=None, max_distance=None, collection=None):
        del embedding, collection
        self.calls.append({"k": k, "where": where, "max_distance": max_distance})
        return list(self.rows)


def test_distance_config_default_valid_and_invalid(monkeypatch):
    monkeypatch.delenv("LAWYERAI_RAG_MAX_DISTANCE", raising=False)
    assert configured_max_distance() == PROVISIONAL_MAX_DISTANCE == 1.0
    monkeypatch.setenv("LAWYERAI_RAG_MAX_DISTANCE", "")
    assert configured_max_distance() == 1.0
    monkeypatch.setenv("LAWYERAI_RAG_MAX_DISTANCE", "0")
    assert configured_max_distance() == 0.0
    monkeypatch.setenv("LAWYERAI_RAG_MAX_DISTANCE", "0.25")
    assert configured_max_distance() == 0.25
    for raw in ("-0.1", "nan", "inf", "-inf", "nope", "1e309"):
        monkeypatch.setenv("LAWYERAI_RAG_MAX_DISTANCE", raw)
        with pytest.raises(ValueError):
            configured_max_distance()


def test_retrieval_keeps_only_relevant_hits_and_passes_filters(monkeypatch):
    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.delenv("LAWYERAI_RAG_MAX_DISTANCE", raising=False)
    strong = _hit(
        0.2,
        text="STRONG_CHUNK",
        effective_date="2020-01-15",
        document_version="v9-not-a-date",
    )
    rows = [
        strong,
        _hit(1.5, text="WEAK_CHUNK", effective_date="2020-01-15"),
        _hit(float("nan"), text="NAN_CHUNK", effective_date="2020-01-15"),
        _hit(float("-inf"), text="NEG_CHUNK", effective_date="2020-01-15"),
        _hit(0.1, text="OTHER_JURISDICTION", jurisdiction="OTHER", effective_date="2020-01-15"),
        _hit(0.1, text="UNDATED_CHUNK", effective_date="", document_version="current"),
        _hit(0.1, text="FUTURE_CHUNK", effective_date="2099-01-01"),
    ]
    store = _RecordingStore(rows)
    result = retrieve_for_query(
        "synthetic question",
        store=store,
        embedder=FakeEmbedder(),
        jurisdiction="IN-TEST",
        as_of="2024-06-01",
    )
    assert result.status == "hits"
    assert [item.chunk.text for item in result.chunks] == ["STRONG_CHUNK"]
    assert store.calls[0]["max_distance"] == 1.0
    assert store.calls[0]["k"] == 32
    assert store.calls[0]["where"] == {"jurisdiction": "IN-TEST"}
    assert "$gte" not in str(store.calls[0]["where"])
    assert "$lte" not in str(store.calls[0]["where"])

    unfiltered = _RecordingStore(rows)
    open_result = retrieve_for_query(
        "synthetic question",
        store=unfiltered,
        embedder=FakeEmbedder(),
    )
    kept = {item.chunk.text for item in open_result.chunks}
    assert "STRONG_CHUNK" in kept
    assert "OTHER_JURISDICTION" in kept
    assert "UNDATED_CHUNK" in kept
    assert "WEAK_CHUNK" not in kept
    assert "NAN_CHUNK" not in kept
    assert "FUTURE_CHUNK" in kept
    assert unfiltered.calls[0]["where"] is None
    assert unfiltered.calls[0]["k"] == 4

    empty = retrieve_for_query(
        "synthetic question",
        store=_RecordingStore([]),
        embedder=FakeEmbedder(),
    )
    assert empty.status == "empty"
    assert empty.chunks == []

    monkeypatch.setenv("LAWYERAI_RAG_MAX_DISTANCE", "nan")
    broken = _RecordingStore(rows)
    failed = retrieve_for_query(
        "synthetic question",
        store=broken,
        embedder=FakeEmbedder(),
    )
    assert failed.status == "error"
    assert failed.message == "retrieval_unavailable"
    assert broken.calls == []
    assert "nan" not in failed.message


def _assert_no_range_operator(where):
    from app.rag.filters import contains_range_operator

    assert contains_range_operator(where) is False


class _RankedStore:
    """Returns at most ``k`` nearest rows and records the Chroma arguments."""

    def __init__(self, rows):
        self.rows = sorted(rows, key=lambda item: item.distance)
        self.calls = []
        self.embedding_model_id = "fake-test"

    def query(self, embedding, k=4, where=None, max_distance=None, collection=None):
        del embedding, collection
        from app.rag.filters import metadata_accepts

        self.calls.append({"k": k, "where": where, "max_distance": max_distance})
        chosen = []
        for item in self.rows:
            if where is not None and not metadata_accepts(item.chunk.metadata(), where):
                continue
            if max_distance is not None and item.distance > max_distance:
                continue
            chosen.append(item)
            if len(chosen) >= k:
                break
        return chosen


def test_as_of_date_filter_is_applied_in_python(monkeypatch):
    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.delenv("LAWYERAI_RAG_MAX_DISTANCE", raising=False)
    rows = [
        _hit(0.05, text="BEFORE", effective_date="2019-12-31", chunk_id="before"),
        _hit(0.06, text="EQUAL", effective_date="2024-06-01", chunk_id="equal"),
        _hit(0.07, text="AFTER", effective_date="2024-06-02", chunk_id="after"),
        _hit(0.08, text="BLANK", effective_date="", published_date="2020-01-01", chunk_id="blank"),
        _hit(0.09, text="MISSING", effective_date="", document_version="2020-01-01", chunk_id="missing"),
        _hit(0.10, text="INVALID", effective_date="2024-13-40", chunk_id="invalid"),
        _hit(0.11, text="OTHER", jurisdiction="OTHER", effective_date="2020-01-01", chunk_id="other"),
    ]
    store = _RankedStore(rows)
    result = retrieve_for_query(
        "synthetic question",
        store=store,
        embedder=FakeEmbedder(),
        jurisdiction="IN-TEST",
        as_of="2024-06-01",
        k=4,
    )
    assert [item.chunk.text for item in result.chunks] == ["BEFORE", "EQUAL"]
    _assert_no_range_operator(store.calls[0]["where"])
    assert store.calls[0]["where"] == {"jurisdiction": "IN-TEST"}
    assert store.calls[0]["k"] == 32

    date_only = _RankedStore(rows)
    dated = retrieve_for_query(
        "synthetic question",
        store=date_only,
        embedder=FakeEmbedder(),
        as_of="2024-06-01",
        k=4,
    )
    assert [item.chunk.text for item in dated.chunks] == ["BEFORE", "EQUAL", "OTHER"]
    assert date_only.calls[0]["where"] is None
    _assert_no_range_operator(date_only.calls[0]["where"])

    jurisdiction_only = _RankedStore(rows)
    places = retrieve_for_query(
        "synthetic question",
        store=jurisdiction_only,
        embedder=FakeEmbedder(),
        jurisdiction="IN-TEST",
        k=4,
    )
    assert "AFTER" in {item.chunk.text for item in places.chunks}
    assert "BLANK" in {item.chunk.text for item in places.chunks}
    assert "OTHER" not in {item.chunk.text for item in places.chunks}
    assert jurisdiction_only.calls[0]["k"] == 4
    assert jurisdiction_only.calls[0]["where"] == {"jurisdiction": "IN-TEST"}


def test_as_of_overfetch_finds_older_chunk_behind_newer_neighbors(monkeypatch):
    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.delenv("LAWYERAI_RAG_MAX_DISTANCE", raising=False)
    newer = [
        _hit(0.01 * (index + 1), text=f"NEWER_{index}", effective_date="2099-01-01", chunk_id=f"new-{index}")
        for index in range(6)
    ]
    older = _hit(0.2, text="ELIGIBLE_OLDER", effective_date="2020-01-15", chunk_id="old")
    store = _RankedStore([*newer, older])
    result = retrieve_for_query(
        "synthetic question",
        store=store,
        embedder=FakeEmbedder(),
        as_of="2024-06-01",
        k=1,
    )
    assert result.status == "hits"
    assert [item.chunk.text for item in result.chunks] == ["ELIGIBLE_OLDER"]
    assert store.calls[0]["k"] == 8
    _assert_no_range_operator(store.calls[0]["where"])

    beyond = [
        _hit(0.01 * (index + 1), text=f"FAR_NEWER_{index}", effective_date="2099-01-01", chunk_id=f"far-{index}")
        for index in range(40)
    ]
    hidden = _hit(0.9, text="TOO_FAR_BACK", effective_date="2020-01-15", chunk_id="hidden")
    capped = _RankedStore([*beyond, hidden])
    missed = retrieve_for_query(
        "synthetic question",
        store=capped,
        embedder=FakeEmbedder(),
        as_of="2024-06-01",
        k=1,
    )
    assert missed.status == "empty"
    assert missed.chunks == []
    assert capped.calls[0]["k"] == 8
    assert all("NEWER" not in item.chunk.text for item in missed.chunks)


def test_retrieval_failure_does_not_return_unfiltered_hits(monkeypatch):
    monkeypatch.setenv("LAWYERAI_RAG_ENABLED", "true")
    monkeypatch.delenv("LAWYERAI_RAG_MAX_DISTANCE", raising=False)

    class _Boom:
        embedding_model_id = "fake-test"

        def query(self, embedding, k=4, where=None, max_distance=None, collection=None):
            del embedding, k, where, max_distance, collection
            raise StoreError("Vector store request failed.")

    failed = retrieve_for_query(
        "synthetic question",
        store=_Boom(),
        embedder=FakeEmbedder(),
        as_of="2024-06-01",
    )
    assert failed.status == "error"
    assert failed.chunks == []
    assert failed.message == "retrieval_unavailable"

    invalid = retrieve_for_query(
        "synthetic question",
        store=_RankedStore([_hit(0.1, text="SHOULD_NOT_LEAK", effective_date="2020-01-01")]),
        embedder=FakeEmbedder(),
        as_of="not-a-date",
    )
    assert invalid.status == "error"
    assert invalid.chunks == []


def test_chroma_rows_drop_bad_distances_and_blank_dates():
    from app.rag.chroma_store import _rows_from_query

    dated = _chunk(effective_date="2020-01-15").chunk.metadata()
    blank = _chunk(text="UNDATED", effective_date="", document_version="current").chunk.metadata()
    found = {
        "ids": [["near", "weak", "nan", "missing", "blank"]],
        "documents": [["NEAR", "WEAK", "NAN", "MISSING", "UNDATED"]],
        "metadatas": [[dated, dated, dated, dated, blank]],
        "distances": [[0.2, 1.5, float("nan"), float("inf")]],
    }
    where = {"effective_date": {"$gte": "1000-01-01", "$lte": "2024-06-01"}}
    rows = _rows_from_query(found, 1.0, where)
    assert [item.chunk.text for item in rows] == ["NEAR"]


def test_query_text_filters_are_explicit_only():
    jurisdiction, as_of = filters_from_text(
        "In Pune, Maharashtra, India, on 3 February 2025 a notice was issued."
    )
    assert jurisdiction is None
    assert as_of is None
    jurisdiction, as_of = filters_from_text(
        "Question jurisdiction: IN-TEST about 2024-06-01 and not 2024-02-31."
    )
    assert jurisdiction == "IN-TEST"
    assert as_of == "2024-06-01"
    jurisdiction, as_of = filters_from_text(
        "jurisdiction: IN-TEST jurisdiction: OTHER 2020-01-01 2021-01-01"
    )
    assert jurisdiction is None
    assert as_of is None


def test_memory_store_uses_squared_l2_cutoff():
    embedder = FakeEmbedder()
    store = InMemoryVectorStore(embedder.model_id, dimension=embedder.dimension)
    from app.rag.types import DocumentRecord

    document = DocumentRecord(
        document_id="alpha",
        source_title="alpha",
        official_url="https://example.test/fixture",
        jurisdiction="IN-TEST",
        document_version="v0",
        text="alpha synthetic rule",
        document_hash="alpha",
        source_path="alpha/body.md",
        effective_date="2020-01-15",
    )
    chunks = chunk_document(document)
    store.upsert_chunks(chunks, embedder.embed_documents([item.text for item in chunks]))
    vector = embedder.embed_query("alpha synthetic rule")
    assert store.query(vector, max_distance=0.0)
    assert store.query(vector, max_distance=0.0, where={"jurisdiction": "OTHER"}) == []
    assert store.query(
        vector,
        where={"effective_date": {"$lte": "2019-01-01", "$gte": "1000-01-01"}},
    ) == []


def test_cli_missing_package_exits_without_scraping(tmp_path):
    if __import__("importlib").util.find_spec("chromadb"):
        pytest.skip("chromadb is installed")
    _write_doc(tmp_path, "fixture", "Synthetic fixture. Not legislation.\n")
    code = ingest_main(
        ["--corpus-root", str(tmp_path), "--chroma-path", str(tmp_path / "chroma")]
    )
    assert code == 2
