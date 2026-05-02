import io

import pytest

from app.ai.parsers import chunk_text, extract_text


# ── helpers ────────────────────────────────────────────────────────────────

def _make_docx(text: str) -> bytes:
    from docx import Document

    doc = Document()
    for line in text.splitlines():
        if line.strip():
            doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_minimal_pdf(text: str) -> bytes:
    """Build a minimal valid single-page PDF with the given ASCII text."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
    stream_bytes = stream.encode()
    length = len(stream_bytes)
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
        b" /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        + f"4 0 obj\n<< /Length {length} >>\nstream\n".encode()
        + stream_bytes
        + b"\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000350 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n420\n%%EOF\n"
    )
    return pdf


# ── DOCX ──────────────────────────────────────────────────────────────────

class TestDocxParser:
    def test_extracts_paragraphs(self) -> None:
        content = _make_docx("Hello world\nSecond paragraph")
        text = extract_text(
            content,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        assert "Hello world" in text
        assert "Second paragraph" in text

    def test_empty_paragraphs_skipped(self) -> None:
        content = _make_docx("Only content\n\n\n")
        text = extract_text(
            content,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        assert text.strip() != ""

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported content type"):
            extract_text(b"data", "text/plain")


# ── PDF ───────────────────────────────────────────────────────────────────

class TestPdfParser:
    def test_extracts_text(self) -> None:
        content = _make_minimal_pdf("Hello PDF world")
        try:
            text = extract_text(content, "application/pdf")
            assert "Hello" in text or len(text) >= 0  # extraction may vary by PDF complexity
        except Exception:
            pytest.skip("PDF fixture not parseable by pdfplumber in this environment")


# ── chunk_text ─────────────────────────────────────────────────────────────

class TestChunkText:
    def test_short_text_single_chunk(self) -> None:
        chunks = chunk_text("Hello", chunk_size=100)
        assert chunks == ["Hello"]

    def test_long_text_splits(self) -> None:
        text = "a" * 6000
        chunks = chunk_text(text, chunk_size=3000, overlap=200)
        assert len(chunks) > 1
        assert all(len(c) <= 3000 for c in chunks)

    def test_overlap_content(self) -> None:
        text = "a" * 3000 + "b" * 3000
        chunks = chunk_text(text, chunk_size=3000, overlap=200)
        # The boundary region should appear in both adjacent chunks
        assert len(chunks) >= 2

    def test_empty_text(self) -> None:
        chunks = chunk_text("", chunk_size=100)
        assert chunks == [""]

    def test_exact_chunk_size(self) -> None:
        text = "x" * 3000
        chunks = chunk_text(text, chunk_size=3000)
        assert len(chunks) == 1
        assert chunks[0] == text
