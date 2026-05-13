# backend/app/utils/text_chunker.py

from typing import List, Dict, Optional
import re


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> List[Dict]:
    """
    Split text into overlapping chunks of ~chunk_size words.
    Returns list of dicts with text and word positions.
    """
    if not text or not text.strip():
        return []

    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = text.strip()

    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]

        chunks.append({
            "chunk_index": chunk_index,
            "text":        " ".join(chunk_words),
            "word_start":  start,
            "word_end":    end,
            "word_count":  len(chunk_words),
        })

        chunk_index += 1
        start += chunk_size - overlap
        if start >= len(words):
            break

    return chunks


def chunk_segments_with_timestamps(
    segments: List[Dict],
    chunk_size: int = 40,   # ~40 words ≈ 12-15 seconds per chunk
    overlap: int = 5,
) -> List[Dict]:
    """
    Chunk transcription segments preserving timestamps.
    Small chunks = precise timestamps.

    segments: [{text, start, end}, ...]
    Returns:  [{chunk_index, text, start_time, end_time, word_count}, ...]
    """
    if not segments:
        return []

    chunks      = []
    chunk_index = 0
    current_words = []
    current_start = segments[0]["start"]
    current_end   = segments[0]["end"]
    last_end      = segments[-1]["end"]

    for seg in segments:
        seg_words   = seg["text"].strip().split()
        current_end = seg["end"]
        current_words.extend(seg_words)

        if len(current_words) >= chunk_size:
            chunks.append({
                "chunk_index": chunk_index,
                "text":        " ".join(current_words[:chunk_size]),
                "start_time":  round(current_start, 2),
                "end_time":    round(current_end, 2),
                "word_count":  chunk_size,
            })
            chunk_index += 1

            # Overlap — keep last N words, update start time
            current_words = current_words[chunk_size - overlap:]
            current_start = seg["start"]

    # Final remaining chunk
    if current_words:
        chunks.append({
            "chunk_index": chunk_index,
            "text":        " ".join(current_words),
            "start_time":  round(current_start, 2),
            "end_time":    round(last_end, 2),
            "word_count":  len(current_words),
        })

    return chunks


def chunk_pdf_pages(
    pages: List[Dict],
    chunk_size: int = 500,
    overlap: int = 50,
) -> List[Dict]:
    """
    Chunk PDF text preserving page numbers.

    pages: [{page_num, text}, ...]
    Returns: [{chunk_index, text, page_num, word_count}, ...]
    """
    if not pages:
        return []

    all_chunks  = []
    chunk_index = 0

    for page in pages:
        page_num  = page["page_num"]
        page_text = page["text"].strip()

        if not page_text:
            continue

        page_chunks = chunk_text(page_text, chunk_size, overlap)

        for chunk in page_chunks:
            all_chunks.append({
                "chunk_index": chunk_index,
                "text":        chunk["text"],
                "page_num":    page_num,
                "word_count":  chunk["word_count"],
            })
            chunk_index += 1

    return all_chunks