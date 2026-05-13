# backend/tests/test_vector_service_advanced.py

import pytest
import numpy as np
from unittest.mock import patch


@pytest.fixture
def vs(tmp_path):
    from app.services.vector_service import VectorService
    service = VectorService()
    service.index_dir = str(tmp_path)

    def mock_embed(texts):
        n = len(texts)
        emb = np.random.rand(n, 384).astype(np.float32)
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        return emb / norms

    with patch.object(service, "embed", side_effect=mock_embed):
        yield service


def test_load_index_missing(vs):
    index, meta = vs.load_index("missing-file")
    assert index is None
    assert meta is None


def test_load_index_after_add(vs):
    chunks = [{"chunk_index": 0, "text": "test", "word_count": 1}]
    vs.add_chunks("load-test", chunks)
    index, meta = vs.load_index("load-test")
    assert index is not None
    assert meta is not None
    assert len(meta) == 1


def test_search_respects_top_k(vs):
    chunks = [{"chunk_index": i, "text": f"text {i}", "word_count": 2} for i in range(10)]
    vs.add_chunks("topk-test", chunks)
    for k in [1, 3, 5]:
        results = vs.search("topk-test", "text", top_k=k)
        assert len(results) <= k


def test_search_result_has_required_fields(vs):
    chunks = [
        {
            "chunk_index": 0,
            "text": "hello world",
            "start_time": 1.0,
            "end_time": 5.0,
            "word_count": 2,
        }
    ]
    vs.add_chunks("fields-test", chunks)
    results = vs.search("fields-test", "hello", top_k=1)
    assert len(results) == 1
    r = results[0]
    assert "chunk_index" in r
    assert "text" in r
    assert "score" in r
    assert "start_time" in r
    assert "end_time" in r


def test_search_sorted_by_score(vs):
    chunks = [{"chunk_index": i, "text": f"doc {i}", "word_count": 2} for i in range(5)]
    vs.add_chunks("sort-test", chunks)
    results = vs.search("sort-test", "doc", top_k=5)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_index_exists_after_add(vs):
    assert not vs.index_exists("new-file")
    vs.add_chunks("new-file", [{"chunk_index": 0, "text": "hi", "word_count": 1}])
    assert vs.index_exists("new-file")


def test_delete_both_files(vs, tmp_path):
    chunks = [{"chunk_index": 0, "text": "delete me", "word_count": 2}]
    vs.add_chunks("del-both", chunks)

    index_path = tmp_path / "del-both.index"
    meta_path = tmp_path / "del-both_meta.json"
    assert index_path.exists()
    assert meta_path.exists()

    vs.delete_index("del-both")
    assert not index_path.exists()
    assert not meta_path.exists()
    
def test_get_meta_path(tmp_path):
    from app.services.vector_service import VectorService
    service = VectorService()
    service.index_dir = str(tmp_path)
    path = service._get_meta_path("file-123")
    assert "file-123_meta.json" in path


def test_get_index_path(tmp_path):
    from app.services.vector_service import VectorService
    service = VectorService()
    service.index_dir = str(tmp_path)
    path = service._get_index_path("file-123")
    assert "file-123.index" in path


def test_load_index_missing_meta(tmp_path):
    """Index exists but meta is missing."""
    import faiss
    import numpy as np
    from app.services.vector_service import VectorService

    service = VectorService()
    service.index_dir = str(tmp_path)

    # Create index but no meta
    index = faiss.IndexFlatIP(384)
    faiss.write_index(index, str(tmp_path / "orphan.index"))

    idx, meta = service.load_index("orphan")
    assert idx is None
    assert meta is None


def test_search_k_larger_than_index(vs):
    """top_k larger than number of vectors."""
    chunks = [{"chunk_index": 0, "text": "only one", "word_count": 2}]
    vs.add_chunks("small-index", chunks)
    results = vs.search("small-index", "query", top_k=100)
    assert len(results) == 1


def test_embed_single_text(vs):
    """Test embedding a single text."""
    import numpy as np
    result = vs.embed(["single text"])
    assert result.shape[0] == 1


def test_add_chunks_with_page_and_timestamps(vs):
    """Chunks with both page_num and timestamps."""
    chunks = [
        {
            "chunk_index": 0,
            "text": "content",
            "page_num": 1,
            "start_time": 0.0,
            "end_time": 5.0,
            "word_count": 1,
        }
    ]
    count = vs.add_chunks("mixed-file", chunks)
    assert count == 1
    results = vs.search("mixed-file", "content", top_k=1)
    assert results[0]["page_num"] == 1
    assert results[0]["start_time"] == 0.0