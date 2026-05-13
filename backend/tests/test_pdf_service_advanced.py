# backend/tests/test_pdf_service_advanced.py

import pytest
import fitz


@pytest.fixture
def multi_page_pdf(tmp_path):
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text(
            (50, 50),
            f"Page {i+1} content. Machine learning topic {i+1}. " * 10,
        )
    path = str(tmp_path / "multipage.pdf")
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def single_page_pdf(tmp_path):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Single page document with some content here.")
    path = str(tmp_path / "single.pdf")
    doc.save(path)
    doc.close()
    return path


def test_multi_page_extraction(multi_page_pdf):
    from app.services.pdf_service import extract_text_from_pdf
    pages, full_text = extract_text_from_pdf(multi_page_pdf)
    assert len(pages) == 3
    assert pages[0]["page_num"] == 1
    assert pages[1]["page_num"] == 2
    assert pages[2]["page_num"] == 3


def test_page_word_counts(multi_page_pdf):
    from app.services.pdf_service import extract_text_from_pdf
    pages, _ = extract_text_from_pdf(multi_page_pdf)
    for page in pages:
        assert page["word_count"] > 0


def test_full_text_has_all_pages(multi_page_pdf):
    from app.services.pdf_service import extract_text_from_pdf
    pages, full_text = extract_text_from_pdf(multi_page_pdf)
    for page in pages:
        assert page["text"][:20] in full_text


def test_metadata_page_count(multi_page_pdf):
    from app.services.pdf_service import get_pdf_metadata
    meta = get_pdf_metadata(multi_page_pdf)
    assert meta["page_count"] == 3


def test_single_page_extraction(single_page_pdf):
    from app.services.pdf_service import extract_text_from_pdf
    pages, full_text = extract_text_from_pdf(single_page_pdf)
    assert len(pages) == 1
    assert "Single page" in full_text


def test_metadata_nonexistent_file():
    from app.services.pdf_service import get_pdf_metadata
    meta = get_pdf_metadata("/nonexistent/path.pdf")
    assert meta["page_count"] == 0


def test_extract_text_nonexistent_file():
    from app.services.pdf_service import extract_text_from_pdf
    with pytest.raises(ValueError, match="Cannot open PDF"):
        extract_text_from_pdf("/nonexistent/path.pdf")