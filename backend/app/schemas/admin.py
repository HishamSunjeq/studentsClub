"""Admin API schemas (Phase 2 control plane).

These shape the JSON the frontend admin pages read/write. **Plaintext API
keys are write-only** on credential payloads — they never appear in any
response.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


# ---------- prompts ---------------------------------------------------------


class PromptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    version: int
    role: str
    content: str
    model_hint: str | None
    is_active: bool
    created_at: datetime


class PromptCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1)
    role: str = "system"
    model_hint: str | None = None
    activate: bool = False


class PromptListResponse(BaseModel):
    items: list[PromptResponse]


# ---------- credentials -----------------------------------------------------


class CredentialResponse(BaseModel):
    """Response schema — *never* includes the plaintext key."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    alias: str
    provider: str
    display_name: str
    key_last4: str
    scope: str
    scope_id: uuid.UUID | None
    monthly_budget_usd: Decimal | None
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime


class CredentialCreateRequest(BaseModel):
    alias: str = Field(min_length=1, max_length=80)
    provider: Literal["anthropic", "openai", "cohere", "voyage", "qdrant"]
    api_key: str = Field(min_length=4)
    display_name: str = ""
    monthly_budget_usd: Decimal | None = None


class CredentialUpdateRequest(BaseModel):
    display_name: str | None = None
    monthly_budget_usd: Decimal | None = None
    is_active: bool | None = None


class CredentialRotateRequest(BaseModel):
    api_key: str = Field(min_length=4)


class CredentialTestResponse(BaseModel):
    ok: bool
    detail: str | None = None
    latency_ms: int | None = None


class CredentialListResponse(BaseModel):
    items: list[CredentialResponse]


# ---------- models ----------------------------------------------------------


class ModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    provider: str
    model_id: str
    display_name: str
    kind: str
    context_window: int
    max_output_tokens: int
    input_cost_per_mtoken: Decimal
    output_cost_per_mtoken: Decimal
    supports_streaming: bool
    supports_json_mode: bool
    supports_prompt_cache: bool
    embedding_dim: int | None
    is_active: bool
    sort_order: int


class ModelCreateRequest(BaseModel):
    provider: str
    model_id: str
    display_name: str
    kind: Literal["extraction", "judge", "embedding", "rerank", "chat", "vision"]
    context_window: int = 0
    max_output_tokens: int = 0
    input_cost_per_mtoken: Decimal = Decimal("0")
    output_cost_per_mtoken: Decimal = Decimal("0")
    supports_streaming: bool = False
    supports_json_mode: bool = False
    supports_prompt_cache: bool = False
    embedding_dim: int | None = None
    sort_order: int = 0


class ModelUpdateRequest(BaseModel):
    display_name: str | None = None
    input_cost_per_mtoken: Decimal | None = None
    output_cost_per_mtoken: Decimal | None = None
    context_window: int | None = None
    max_output_tokens: int | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class ModelListResponse(BaseModel):
    items: list[ModelResponse]


# ---------- profiles --------------------------------------------------------


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    subject_id: uuid.UUID | None
    name: str
    prompt_name: str
    judge_prompt_name: str
    extraction_model_id: uuid.UUID | None
    judge_model_id: uuid.UUID | None
    embedding_model_id: uuid.UUID | None
    rerank_model_id: uuid.UUID | None
    credential_alias_extraction: str | None
    credential_alias_judge: str | None
    credential_alias_embedding: str | None
    credential_alias_rerank: str | None
    target_count: int
    difficulty_mix: dict
    judge_threshold: Decimal
    dedup_threshold: Decimal
    top_k_retrieval: int
    top_n_rerank: int
    hybrid_alpha: Decimal
    is_default: bool


class ProfileCreateRequest(BaseModel):
    subject_id: uuid.UUID | None = None
    name: str
    prompt_name: str = "extraction.system"
    judge_prompt_name: str = "judge.rubric"
    extraction_model_id: uuid.UUID | None = None
    judge_model_id: uuid.UUID | None = None
    embedding_model_id: uuid.UUID | None = None
    rerank_model_id: uuid.UUID | None = None
    credential_alias_extraction: str | None = None
    credential_alias_judge: str | None = None
    credential_alias_embedding: str | None = None
    credential_alias_rerank: str | None = None
    target_count: int = 20
    difficulty_mix: dict = Field(default_factory=lambda: {"easy": 0.3, "medium": 0.5, "hard": 0.2})
    judge_threshold: Decimal = Decimal("6.0")
    dedup_threshold: Decimal = Decimal("0.92")
    top_k_retrieval: int = 50
    top_n_rerank: int = 8
    hybrid_alpha: Decimal = Decimal("0.5")
    is_default: bool = False


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    prompt_name: str | None = None
    judge_prompt_name: str | None = None
    extraction_model_id: uuid.UUID | None = None
    judge_model_id: uuid.UUID | None = None
    embedding_model_id: uuid.UUID | None = None
    rerank_model_id: uuid.UUID | None = None
    credential_alias_extraction: str | None = None
    credential_alias_judge: str | None = None
    credential_alias_embedding: str | None = None
    credential_alias_rerank: str | None = None
    target_count: int | None = None
    difficulty_mix: dict | None = None
    judge_threshold: Decimal | None = None
    dedup_threshold: Decimal | None = None
    top_k_retrieval: int | None = None
    top_n_rerank: int | None = None
    hybrid_alpha: Decimal | None = None
    is_default: bool | None = None


class ProfileListResponse(BaseModel):
    items: list[ProfileResponse]
