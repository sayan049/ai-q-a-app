# backend/app/services/vector_service.py

import os
import json
import numpy as np
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)

# Lazy-load heavy dependencies
_embedding_model = None
_faiss = None


def get_faiss():
    global _faiss
    if _faiss is None:
        import faiss
        _faiss = faiss
    return _faiss


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence-transformers model...")
            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Embedding model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise RuntimeError(f"Embedding model unavailable: {str(e)}")
    return _embedding_model


class VectorService:
    """
    Manages FAISS indexes for semantic search.
    Each file gets its own FAISS index stored on disk.
    Chunk metadata stored alongside as JSON.
    """

    EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 output dimension

    def __init__(self):
        self.index_dir = settings.index_dir

    def _get_index_path(self, file_id: str) -> str:
        return os.path.join(self.index_dir, f"{file_id}.index")

    def _get_meta_path(self, file_id: str) -> str:
        return os.path.join(self.index_dir, f"{file_id}_meta.json")

    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        if not texts:
            return np.array([]).reshape(0, self.EMBEDDING_DIM)

        model = get_embedding_model()
        embeddings = model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,  # L2 normalize for cosine similarity
            convert_to_numpy=True,
        )
        return embeddings.astype(np.float32)

    def add_chunks(self, file_id: str, chunks: List[Dict]) -> int:
        """
        Build and save FAISS index for a file's chunks.

        chunks: [{chunk_index, text, start_time?, end_time?, page_num?, word_count}, ...]
        Returns: number of chunks indexed
        """
        faiss = get_faiss()

        if not chunks:
            logger.warning(f"No chunks to index for file {file_id}")
            return 0

        texts = [c["text"] for c in chunks]
        logger.info(f"Generating embeddings for {len(texts)} chunks (file: {file_id})")

        embeddings = self.embed(texts)

        # Create flat L2 index (suitable for our scale)
        index = faiss.IndexFlatIP(self.EMBEDDING_DIM)  # Inner product (cosine with normalized)

        # Add vectors
        index.add(embeddings)

        # Save index to disk
        index_path = self._get_index_path(file_id)
        faiss.write_index(index, index_path)
        logger.info(f"FAISS index saved to {index_path} ({index.ntotal} vectors)")

        # Save metadata (chunk text + timestamps + page numbers)
        meta_path = self._get_meta_path(file_id)
        metadata = []
        for i, chunk in enumerate(chunks):
            metadata.append({
                "chunk_index": chunk.get("chunk_index", i),
                "text": chunk["text"],
                "start_time": chunk.get("start_time"),
                "end_time": chunk.get("end_time"),
                "page_num": chunk.get("page_num"),
                "word_count": chunk.get("word_count", 0),
            })

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        return index.ntotal

    def load_index(self, file_id: str):
        """Load FAISS index from disk. Returns (index, metadata) or (None, None)."""
        faiss = get_faiss()

        index_path = self._get_index_path(file_id)
        meta_path = self._get_meta_path(file_id)

        if not os.path.exists(index_path):
            logger.warning(f"FAISS index not found: {index_path}")
            return None, None

        if not os.path.exists(meta_path):
            logger.warning(f"Metadata not found: {meta_path}")
            return None, None

        try:
            index = faiss.read_index(index_path)
        except Exception as e:
            logger.error(f"Failed to load FAISS index {index_path}: {e}")
            return None, None

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load metadata {meta_path}: {e}")
            return None, None

        return index, metadata

    def search(
        self,
        file_id: str,
        query: str,
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Search for most relevant chunks given a query.

        Returns: [{text, score, chunk_index, start_time, end_time, page_num}, ...]
        Sorted by relevance score (descending).
        """
        index, metadata = self.load_index(file_id)

        if index is None or not metadata:
            logger.warning(f"No index found for file {file_id}")
            return []

        if index.ntotal == 0:
            return []

        # Embed query
        query_embedding = self.embed([query])

        # Search
        k = min(top_k, index.ntotal)
        scores, indices = index.search(query_embedding, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(metadata):
                continue

            chunk = metadata[idx]
            results.append({
                "chunk_index": chunk.get("chunk_index", idx),
                "text": chunk["text"],
                "score": float(score),
                "start_time": chunk.get("start_time"),
                "end_time": chunk.get("end_time"),
                "page_num": chunk.get("page_num"),
                "word_count": chunk.get("word_count", 0),
            })

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def delete_index(self, file_id: str) -> bool:
        """Delete FAISS index and metadata files for a file."""
        deleted = False
        for path in [self._get_index_path(file_id), self._get_meta_path(file_id)]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    deleted = True
                except OSError as e:
                    logger.error(f"Failed to delete {path}: {e}")
        return deleted

    def index_exists(self, file_id: str) -> bool:
        """Check if FAISS index exists for a file."""
        return os.path.exists(self._get_index_path(file_id))


# Module-level singleton
vector_service = VectorService()