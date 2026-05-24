"""Pydantic schemas shared across orchestrator stages (Phase 4)."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.ai.base import ChoiceDraft


class DocumentAnalysis(BaseModel):
    doc_type: str = "study_material"
    language: str | None = None
    suggested_total_questions: int = 20
    section_outline: list[str] = Field(default_factory=list)


class Section(BaseModel):
    position: int
    title: str | None
    text: str
    target_questions: int = 5


class RetrievedChunk(BaseModel):
    chunk_id: uuid.UUID
    upload_id: uuid.UUID | None
    section_title: str | None
    text: str
    score: float = 0.0


class RetrievedContext(BaseModel):
    section_position: int
    query: str
    hyde: str | None = None
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    degraded: bool = False
    degraded_reason: str | None = None


class CandidateQuestion(BaseModel):
    text: str
    choices: list[ChoiceDraft]
    explanation: str | None = None
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    source_chunk_ids: list[uuid.UUID] = Field(default_factory=list)
    source_excerpt: str | None = None


class SectionDraft(BaseModel):
    section_position: int
    questions: list[CandidateQuestion]
    tokens_input: int = 0
    tokens_output: int = 0
    model: str = ""


class JudgedQuestion(BaseModel):
    question: CandidateQuestion
    quality_score: float = 0.0
    auto_rejected: bool = False
    judge_notes: str | None = None
