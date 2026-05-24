"""HTTP client for the `unstructured-api` document-extraction service (Phase 9).

Posts the raw file to `/general/v0/general` and joins the returned element
JSON into plain text. Unlike pdfplumber, the `auto`/`hi_res`/`ocr_only`
strategies route image/scanned pages through tesseract with the configured
OCR languages, which applies proper Unicode bidi ordering — fixing the
reversed-Arabic bug.
"""

from __future__ import annotations

import logging

import httpx

from app.ai.extraction.config import ExtractionConfig
from app.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=10.0, read=300.0, write=60.0, pool=10.0)


async def extract_via_unstructured(
    content: bytes,
    content_type: str,
    filename: str,
    cfg: ExtractionConfig,
) -> str:
    """Call unstructured-api and return the joined element text.

    Raises on connection error or non-2xx so the dispatcher can fall back
    to the legacy extractor.
    """
    url = f"{settings.unstructured_api_url.rstrip('/')}/general/v0/general"

    data: list[tuple[str, str]] = [("strategy", cfg.strategy)]
    # `languages` is repeated, one entry per OCR language.
    for lang in cfg.ocr_languages or ["eng"]:
        data.append(("languages", lang))
    if cfg.extract_tables:
        data.append(("pdf_infer_table_structure", "true"))
    if cfg.hi_res_model_name:
        data.append(("hi_res_model_name", cfg.hi_res_model_name))
    if cfg.max_characters:
        data.append(("max_characters", str(cfg.max_characters)))

    files = {"files": (filename, content, content_type)}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, data=data, files=files)
        resp.raise_for_status()
        elements = resp.json()

    return _join_elements(elements, extract_tables=cfg.extract_tables)


def _join_elements(elements: list[dict], *, extract_tables: bool) -> str:
    parts: list[str] = []
    for el in elements:
        if not isinstance(el, dict):
            continue
        el_type = el.get("type")
        if el_type == "Table" and extract_tables:
            meta = el.get("metadata") or {}
            html = meta.get("text_as_html")
            parts.append(html or el.get("text", ""))
            continue
        text = el.get("text")
        if text and text.strip():
            parts.append(text)
    return "\n\n".join(parts)
