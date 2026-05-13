# backend/tests/test_vector_service.py

import pytest
import numpy as np
from unittest.mock import patch


@pytest.fixture
def vs(tmp_path):
    """VectorService with mocked embeddings and tmp index dir."""
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


def test_add_chunks_success(vs):
    chunks = [
        {"chunk_index": 0, "text": "Machine learning basics", "word_count": 3},
        {"chunk_index": 1, "text": "Deep learning neural networks", "word_count": 4},
        {"chunk_index": 2, "text": "Python programming tutorial", "word_count": 3},
    ]
    count = vs.add_chunks("file-001", chunks)
    assert count == 3
    assert vs.index_exists("file-001")


def test_add_chunks_with_timestamps(vs):
    chunks = [
        {"chunk_index": 0, "text": "Hello world", "start_time": 0.0, "end_time": 5.0, "word_count": 2},
        {"chunk_index": 1, "text": "Machine learning", "start_time": 5.0, "end_time": 10.0, "word_count": 2},
    ]
    count = vs.add_chunks("audio-001", chunks)
    assert count == 2


def test_add_chunks_with_page_numbers(vs):
    chunks = [
        {"chunk_index": 0, "text": "Page one content", "page_num": 1, "word_count": 3},
        {"chunk_index": 1, "text": "Page two content", "page_num": 2, "word_count": 3},
    ]
    count = vs.add_chunks("pdf-001", chunks)
    assert count == 2


def test_search_returns_results(vs):
    chunks = [{"chunk_index": i, "text": f"chunk {i} content", "word_count": 3} for i in range(5)]
    vs.add_chunks("search-file", chunks)
    results = vs.search("search-file", "chunk content", top_k=3)
    assert len(results) <= 3
    assert all("text" in r for r in results)
    assert all("score" in r for r in results)


def test_search_returns_relevant_results(vs):
    chunks = [{"chunk_index": i, "text": f"Sample text chunk {i}", "word_count": 4} for i in range(10)]
    vs.add_chunks("search-test-file", chunks)
    results = vs.search("search-test-file", "sample text", top_k=3)
    assert len(results) <= 3


def test_search_empty_index(vs):
    results = vs.search("nonexistent-file", "some query", top_k=5)
    assert results == []


def test_search_top_k_limit(vs):
    chunks = [{"chunk_index": i, "text": f"text {i}", "word_count": 2} for i in range(10)]
    vs.add_chunks("limit-test", chunks)
    results = vs.search("limit-test", "text", top_k=3)
    assert len(results) <= 3


def test_delete_index(vs):
    chunks = [{"chunk_index": 0, "text": "to delete", "word_count": 2}]
    vs.add_chunks("delete-file", chunks)
    assert vs.index_exists("delete-file")
    vs.delete_index("delete-file")
    assert not vs.index_exists("delete-file")


def test_delete_nonexistent_index(vs):
    result = vs.delete_index("nonexistent")
    assert result is False


def test_multi_file_isolation(vs):
    vs.add_chunks("file-a", [{"chunk_index": 0, "text": "File A content", "word_count": 3}])
    vs.add_chunks("file-b", [{"chunk_index": 0, "text": "File B content", "word_count": 3}])
    assert vs.index_exists("file-a")
    assert vs.index_exists("file-b")
    results_a = vs.search("file-a", "content", top_k=5)
    results_b = vs.search("file-b", "content", top_k=5)
    assert len(results_a) > 0
    assert len(results_b) > 0


def test_add_empty_chunks(vs):
    count = vs.add_chunks("empty-file", [])
    assert count == 0


def test_index_exists_false(vs):
    assert not vs.index_exists("does-not-exist")


def test_search_with_timestamps_in_results(vs):
    chunks = [
        {
            "chunk_index": 0,
            "text": "Introduction chapter",
            "start_time": 0.0,
            "end_time": 30.0,
            "word_count": 2,
        }
    ]
    vs.add_chunks("ts-file", chunks)
    results = vs.search("ts-file", "introduction", top_k=1)
    assert len(results) == 1
    assert results[0].get("start_time") == 0.0
    assert results[0].get("end_time") == 30.0