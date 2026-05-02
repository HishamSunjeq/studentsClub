import io


def extract_text(content: bytes, content_type: str) -> str:
    if content_type == "application/pdf":
        return _extract_pdf(content)
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return _extract_docx(content)
    if content_type in ("image/png", "image/jpeg", "image/webp"):
        return _extract_image(content)
    raise ValueError(f"Unsupported content type: {content_type!r}")


def _extract_pdf(content: bytes) -> str:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n\n".join(p for p in pages if p.strip())


def _extract_docx(content: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(content))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _extract_image(content: bytes) -> str:
    import pytesseract
    from PIL import Image

    img = Image.open(io.BytesIO(content))
    return pytesseract.image_to_string(img)


def chunk_text(text: str, chunk_size: int = 3000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks for AI processing."""
    if len(text) <= chunk_size:
        return [text]
    step = max(chunk_size - overlap, 1)
    return [text[i : i + chunk_size] for i in range(0, len(text), step)]
