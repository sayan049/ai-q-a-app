# backend/tests/test_pdf_service.py

import pytest
import fitz  # PyMuPDF


@pytest.fixture
def simple_pdf(tmp_path):
    """Create a simple PDF for testing."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Page 1: Machine learning and artificial intelligence.")
    page.insert_text((50, 100), "This is test content for our PDF service.")
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Page 2: Deep learning and neural networks.")
    pdf_path = str(tmp_path / "test.pdf")
    doc.save(pdf_path)
    doc.close()
    return pdf_path


@pytest.fixture
def empty_pdf(tmp_path):
    """Create a PDF with no text (simulates scanned PDF)."""
    doc = fitz.open()
    doc.new_page()  # Empty page
    pdf_path = str(tmp_path / "empty.pdf")
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def test_extract_text_success(simple_pdf):
    """Test successful text extraction from PDF."""
    from app.services.pdf_service import extract_text_from_pdf

    pages, full_text = extract_text_from_pdf(simple_pdf)

    assert len(pages) == 2
    assert pages[0]["page_num"] == 1
    assert pages[1]["page_num"] == 2
    assert "Machine learning" in full_text
    assert "Deep learning" in full_text


def test_extract_text_page_structure(simple_pdf):
    """Test page metadata in extraction result."""
    from app.services.pdf_service import extract_text_from_pdf

    pages, _ = extract_text_from_pdf(simple_pdf)

    for page in pages:
        assert "page_num" in page
        assert "text" in page
        assert "word_count" in page
        assert page["word_count"] > 0


def test_extract_text_empty_pdf(empty_pdf):
    """Test that empty PDF raises ValueError."""
    from app.services.pdf_service import extract_text_from_pdf

    with pytest.raises(ValueError, match="PDF appears to contain only images"):
        extract_text_from_pdf(empty_pdf)


def test_extract_text_corrupted_file(tmp_path):
    """Test that corrupted PDF raises ValueError."""
    from app.services.pdf_service import extract_text_from_pdf

    corrupted_path = str(tmp_path / "corrupted.pdf")
    with open(corrupted_path, "wb") as f:
        f.write(b"this is not a valid pdf file content")

    with pytest.raises(ValueError, match="Cannot open PDF file"):
        extract_text_from_pdf(corrupted_path)


def test_get_pdf_metadata(simple_pdf):
    """Test PDF metadata extraction."""
    from app.services.pdf_service import get_pdf_metadata

    metadata = get_pdf_metadata(simple_pdf)
    assert "page_count" in metadata
    assert metadata["page_count"] == 2


def test_full_text_concatenation(simple_pdf):
    """Test that full text includes content from all pages."""
    from app.services.pdf_service import extract_text_from_pdf

    _, full_text = extract_text_from_pdf(simple_pdf)

    assert "Page 1" in full_text
    assert "Page 2" in full_text
    assert "\n\n" in full_text  # Pages separated by double newline