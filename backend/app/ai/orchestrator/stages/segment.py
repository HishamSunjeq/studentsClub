"""Stage 2: produce orchestrator `Section` objects from extracted text (Phase 4).

We reuse the heading-aware splitter from Phase 3 (`app.ai.rag.splitter`)
and group its chunks back together by section title — orchestrator
sections are coarser than embedding chunks (a section can hold multiple
embed chunks). Each section gets a target question count derived from
its proportional length.
"""

from __future__ import annotations

import math
from collections import OrderedDict

from app.ai.orchestrator.schemas import DocumentAnalysis, Section
from app.ai.rag.splitter import split_document


def segment_document(text: str, analysis: DocumentAnalysis) -> list[Section]:
    chunks = split_document(text)
    if not chunks:
        return []

    # Group chunks by section_title preserving document order.
    grouped: "OrderedDict[str | None, list[str]]" = OrderedDict()
    for c in chunks:
        grouped.setdefault(c.section_title, []).append(c.text)

    total_chars = sum(sum(len(t) for t in texts) for texts in grouped.values())
    target_total = max(5, analysis.suggested_total_questions)

    sections: list[Section] = []
    leftover = target_total
    items = list(grouped.items())
    for i, (title, texts) in enumerate(items):
        joined = "\n\n".join(texts)
        section_chars = len(joined)

        if i == len(items) - 1:
            target_q = max(1, leftover)
        else:
            share = section_chars / max(1, total_chars)
            target_q = max(1, int(math.floor(share * target_total)))
            leftover = max(1, leftover - target_q)

        sections.append(
            Section(
                position=i,
                title=title,
                text=joined[:16000],  # safety cap per section
                target_questions=target_q,
            )
        )

    return sections
