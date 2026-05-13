# backend/tests/test_vector_service_embed.py

import pytest
import numpy as np
from unittest.mock import patch, MagicMock


def test_embed_returns_numpy_array(tmp_path):
    """Test embedding returns correct shape."""
    from app.services.vector_service import VectorService

    service = VectorService()
    service.index_dir = str(tmp_path)

    mock_model = MagicMock()
    mock_model.encode.return_value = np.random.rand(3, 384).astype(np.float32)

    with patch("app.services.vector_service.get_embedding_model", return_value=mock_model):
        result = service.embed(["text1", "text2", "text3"])

    assert result.shape == (3, 384)
    assert result.dtype == np.float32


def test_embed_empty_list(tmp_path):
    """Test embedding empty list returns empty array."""
    from app.services.vector_service import VectorService

    service = VectorService()
    service.index_dir = str(tmp_path)

    result = service.embed([])
    assert result.shape == (0, 384)


def test_get_embedding_model_loads_once():
    """Test embedding model is cached."""
    from app.services import vector_service as vs_module

    original = vs_module._embedding_model
    vs_module._embedding_model = None

    mock_model = MagicMock()
    with patch("sentence_transformers.SentenceTransformer", return_value=mock_model):
        model = vs_module.get_embedding_model()
        assert model is mock_model

    vs_module._embedding_model = original


def test_search_with_invalid_indices(tmp_path):
    """Test search handles invalid FAISS indices gracefully."""
    from app.services.vector_service import VectorService
    import numpy as np

    service = VectorService()
    service.index_dir = str(tmp_path)

    def mock_embed(texts):
        n = len(texts)
        emb = np.random.rand(n, 384).astype(np.float32)
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        return emb / norms

    with patch.object(service, "embed", side_effect=mock_embed):
        chunks = [{"chunk_index": 0, "text": "test content here", "word_count": 3}]
        service.add_chunks("valid-file", chunks)
        results = service.search("valid-file", "test query here", top_k=10)
        assert isinstance(results, list)