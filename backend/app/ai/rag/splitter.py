"""Heading-aware recursive splitter (Phase 3).

Walks the document top-down:
- Markdown-style headers ('# ', '## ', '### ', or upper-case lines) -> sections
- Within each section: paragraph-split on \n\n, then sentence-split if a
  paragraph is too long
- Yields chunks with (section_title, text, position).

The splitter avoids cutting mid-sentence and tries to keep chunks around
`target_chars` characters with a hard cap at `max_chars`. We don't use
tiktoken here — char count is a good-enough proxy and dependency-free.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


@dataclass
class SplitChunk:
    position: int
    section_title: str | None
    text: str


def split_document(
    text: str,
    *,
    target_chars: int = 2000,
    max_chars: int = 3500,
    min_chars: int = 300,
) -> list[SplitChunk]:
    if not text or not text.strip():
        return []

    sections = _split_into_sections(text)

    chunks: list[SplitChunk] = []
    position = 0
    for section_title, body in sections:
        for piece in _pack_paragraphs(body, target_chars=target_chars, max_chars=max_chars):
            if len(piece.strip()) < min_chars and chunks:
                # Tail piece too small — merge into the previous chunk in the same section.
                if chunks[-1].section_title == section_title:
                    chunks[-1] = SplitChunk(
                        position=chunks[-1].position,
                        section_title=section_title,
                        text=chunks[-1].text + "\n\n" + piece.strip(),
                    )
                    continue
            chunks.append(
                SplitChunk(position=position, section_title=section_title, text=piece.strip())
            )
            position += 1

    return chunks


def _split_into_sections(text: str) -> list[tuple[str | None, str]]:
    """Return (section_title, body) tuples in document order."""
    matches = list(_HEADER_RE.finditer(text))
    if not matches:
        return [(None, text)]

    sections: list[tuple[str | None, str]] = []
    # Leading text before the first header (if any)
    if matches[0].start() > 0:
        leading = text[: matches[0].start()].strip()
        if leading:
            sections.append((None, leading))

    for i, m in enumerate(matches):
        title = m.group(2).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        if body:
            sections.append((title, body))

    return sections


def _pack_paragraphs(body: str, *, target_chars: int, max_chars: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    out: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for para in paragraphs:
        if len(para) > max_chars:
            # Flush, then sentence-split the long paragraph.
            if buf:
                out.append("\n\n".join(buf))
                buf = []
                buf_len = 0
            out.extend(_sentence_chunks(para, target_chars=target_chars, max_chars=max_chars))
            continue

        if buf_len + len(para) + 2 > max_chars and buf:
            out.append("\n\n".join(buf))
            buf = [para]
            buf_len = len(para)
        else:
            buf.append(para)
            buf_len += len(para) + 2
            if buf_len >= target_chars:
                out.append("\n\n".join(buf))
                buf = []
                buf_len = 0
    if buf:
        out.append("\n\n".join(buf))
    return out


def _sentence_chunks(text: str, *, target_chars: int, max_chars: int) -> list[str]:
    sentences = _SENTENCE_END.split(text)
    out: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for sent in sentences:
        s = sent.strip()
        if not s:
            continue
        if buf_len + len(s) + 1 > max_chars and buf:
            out.append(" ".join(buf))
            buf = [s]
            buf_len = len(s)
        else:
            buf.append(s)
            buf_len += len(s) + 1
            if buf_len >= target_chars:
                out.append(" ".join(buf))
                buf = []
                buf_len = 0
    if buf:
        out.append(" ".join(buf))
    return out
