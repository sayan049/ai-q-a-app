# backend/app/services/pdf_service.py

import fitz  # PyMuPDF
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> Tuple[List[Dict], str]:
    """
    Extract text from PDF, page by page.

    Returns:
        pages: [{page_num, text, word_count}, ...]
        full_text: concatenated text of all pages
    """
    pages = []
    full_text_parts = []

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        logger.error(f"Failed to open PDF {file_path}: {e}")
        raise ValueError(f"Cannot open PDF file: {str(e)}")

    try:
        if doc.page_count == 0:
            raise ValueError("PDF has no pages")

        for page_num in range(doc.page_count):
            try:
                page = doc.load_page(page_num)
                text = page.get_text("text")  # type: ignore

                if text:
                    text = text.strip()
                    words = text.split()
                    pages.append({
                        "page_num": page_num + 1,  # 1-indexed
                        "text": text,
                        "word_count": len(words),
                    })
                    full_text_parts.append(text)

            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                continue

    finally:
        doc.close()

    full_text = "\n\n".join(full_text_parts)

    if not full_text.strip():
        raise ValueError(
            "PDF appears to contain only images or scanned content. "
            "Text extraction returned no content. "
            "Please use a PDF with selectable text."
        )

    return pages, full_text


def get_pdf_metadata(file_path: str) -> Dict:
    """Extract PDF metadata (title, author, page count, etc.)"""
    try:
        doc = fitz.open(file_path)
        metadata = doc.metadata
        page_count = doc.page_count
        doc.close()

        return {
            "page_count": page_count,
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "creator": metadata.get("creator", ""),
        }
    except Exception as e:
        logger.warning(f"Could not extract PDF metadata: {e}")
        return {"page_count": 0}