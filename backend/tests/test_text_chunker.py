# backend/tests/test_text_chunker.py

import pytest
from app.utils.text_chunker import (
    chunk_text,
    chunk_segments_with_timestamps,
    chunk_pdf_pages,
)


# ── chunk_text ────────────────────────────────────────────────────────────────

def test_chunk_text_basic():
    text = " ".join([f"word{i}" for i in range(200)])
    chunks = chunk_text(text, chunk_size=50, overlap=5)
    assert len(chunks) > 1
    for c in chunks:
        assert "text" in c
        assert "chunk_index" in c
        assert "word_count" in c


def test_chunk_text_empty():
    assert chunk_text("", chunk_size=100) == []
    assert chunk_text("   ", chunk_size=100) == []


def test_chunk_text_smaller_than_chunk_size():
    text = "This is a short text"
    chunks = chunk_text(text, chunk_size=500)
    assert len(chunks) == 1
    assert chunks[0]["text"] == text


def test_chunk_text_overlap():
    words = [f"w{i}" for i in range(100)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=20, overlap=5)
    assert len(chunks) > 1
    # Verify overlap — last words of chunk 0 appear at start of chunk 1
    c0_words = chunks[0]["text"].split()
    c1_words = chunks[1]["text"].split()
    overlap_words = c0_words[-5:]
    assert overlap_words == c1_words[:5]


def test_chunk_text_indices():
    text = " ".join([f"word{i}" for i in range(50)])
    chunks = chunk_text(text, chunk_size=20, overlap=5)
    for i, c in enumerate(chunks):
        assert c["chunk_index"] == i


# ── chunk_segments_with_timestamps ───────────────────────────────────────────

def test_chunk_segments_empty():
    assert chunk_segments_with_timestamps([]) == []


def test_chunk_segments_basic():
    segments = [
        {"text": " ".join([f"word{i}" for i in range(20)]), "start": 0.0, "end": 10.0},
        {"text": " ".join([f"word{i}" for i in range(20)]), "start": 10.0, "end": 20.0},
        {"text": " ".join([f"word{i}" for i in range(20)]), "start": 20.0, "end": 30.0},
    ]
    chunks = chunk_segments_with_timestamps(segments, chunk_size=30, overlap=5)
    assert len(chunks) >= 1
    for c in chunks:
        assert "start_time" in c
        assert "end_time" in c
        assert "text" in c
        assert c["start_time"] >= 0.0


def test_chunk_segments_preserves_timestamps():
    segments = [
        {"text": "Hello world machine learning", "start": 0.0, "end": 5.0},
        {"text": "Deep learning neural networks", "start": 5.0, "end": 10.0},
    ]
    chunks = chunk_segments_with_timestamps(segments, chunk_size=3, overlap=0)
    assert len(chunks) >= 1
    assert chunks[0]["start_time"] == 0.0


def test_chunk_segments_single_segment():
    segments = [{"text": "Just one segment here", "start": 1.5, "end": 4.5}]
    chunks = chunk_segments_with_timestamps(segments, chunk_size=100, overlap=5)
    assert len(chunks) == 1
    assert chunks[0]["start_time"] == 1.5
    assert chunks[0]["end_time"] == 4.5


def test_chunk_segments_small_chunk_size():
    segments = [
        {"text": " ".join([f"w{i}" for i in range(50)]), "start": 0.0, "end": 25.0},
        {"text": " ".join([f"w{i}" for i in range(50)]), "start": 25.0, "end": 50.0},
    ]
    chunks = chunk_segments_with_timestamps(segments, chunk_size=20, overlap=3)
    assert len(chunks) >= 3
    # All chunks have valid timestamps
    for c in chunks:
        assert c["start_time"] >= 0.0
        assert c["end_time"] >= c["start_time"]


# ── chunk_pdf_pages ───────────────────────────────────────────────────────────

def test_chunk_pdf_pages_empty():
    assert chunk_pdf_pages([]) == []


def test_chunk_pdf_pages_basic():
    pages = [
        {"page_num": 1, "text": " ".join([f"word{i}" for i in range(100)])},
        {"page_num": 2, "text": " ".join([f"word{i}" for i in range(100)])},
    ]
    chunks = chunk_pdf_pages(pages, chunk_size=50, overlap=5)
    assert len(chunks) >= 2
    for c in chunks:
        assert "page_num" in c
        assert "text" in c
        assert "chunk_index" in c


def test_chunk_pdf_pages_preserves_page_numbers():
    pages = [
        {"page_num": 3, "text": "Content from page three here"},
        {"page_num": 7, "text": "Content from page seven here"},
    ]
    chunks = chunk_pdf_pages(pages, chunk_size=500, overlap=0)
    assert chunks[0]["page_num"] == 3
    assert chunks[1]["page_num"] == 7


def test_chunk_pdf_pages_skips_empty():
    pages = [
        {"page_num": 1, "text": "Real content here"},
        {"page_num": 2, "text": "   "},   # empty
        {"page_num": 3, "text": "More content"},
    ]
    chunks = chunk_pdf_pages(pages, chunk_size=500, overlap=0)
    page_nums = [c["page_num"] for c in chunks]
    assert 2 not in page_nums
    assert 1 in page_nums
    assert 3 in page_nums


def test_chunk_pdf_pages_sequential_indices():
    pages = [
        {"page_num": 1, "text": " ".join([f"w{i}" for i in range(200)])},
    ]
    chunks = chunk_pdf_pages(pages, chunk_size=50, overlap=10)
    for i, c in enumerate(chunks):
        assert c["chunk_index"] == i