"""Document text extraction dispatcher (Phase 9).

`extract_document` is the single entry point used by the upload worker.
It routes to the configured backend (`unstructured` via the API service,
or the `legacy` pdfplumber/python-docx/tesseract path in `app.ai.parsers`)
and falls back to legacy on any unstructured-api failure so a missing
service never blocks extraction.
"""

from __future__ import annotations

import logging

from app.ai.extraction.config import ExtractionConfig

logger = logging.getLogger(__name__)


async def extract_document(
    content: bytes,
    content_type: str,
    filename: str,
    cfg: ExtractionConfig,
) -> tuple[str, str]:
    """Extract text. Returns `(text, backend_used)`.

    `backend_used` is `"unstructured"` or `"legacy"` — recorded on the
    Upload row so the UI can show what actually produced the text.
    """
    if cfg.backend == "unstructured":
        try:
            from app.ai.extraction.unstructured_client import extract_via_unstructured

            text = await extract_via_unstructured(content, content_type, filename, cfg)
            if text and text.strip():
                return text, "unstructured"
            logger.warning(
                "unstructured-api returned empty text for %s; falling back to legacy",
                filename,
            )
        except Exception:
            logger.exception(
                "unstructured-api extraction failed for %s; falling back to legacy",
                filename,
            )

    from app.ai.parsers import extract_text

    return extract_text(content, content_type), "legacy"
