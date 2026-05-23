"""AI control plane: prompts, credentials, model registry, generation profiles.

Phase 2 of the AI overhaul. Creates four tables that make every previously
hardcoded knob (prompt text, API key, model, generation tuning) DB-backed
and admin-manageable from the frontend.

Includes seed data:
- `extraction.system` v1 (migrated from the hardcoded constant)
- `judge.rubric` v1, `contextualize.chunk` v1, `subject_qa.system` v1, `hyde.expand` v1
- Catalog of currently-known LLM / embedding / rerank models
- One global default `generation_profile`

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-24
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


_EXTRACTION_PROMPT = """\
You are an expert exam question generator for university students.
Extract meaningful multiple-choice questions from the provided study material.

Return ONLY a valid JSON object matching this exact schema — no markdown, no commentary:
{
  "questions": [
    {
      "text": "Full question text ending with a question mark?",
      "choices": [
        {"text": "Option A", "is_correct": true},
        {"text": "Option B", "is_correct": false},
        {"text": "Option C", "is_correct": false},
        {"text": "Option D", "is_correct": false}
      ],
      "explanation": "Concise explanation of why the correct answer is right.",
      "difficulty": "easy",
      "source_excerpt": "Short verbatim excerpt from the source this question is based on."
    }
  ]
}

Rules:
- Each question MUST have exactly 4 choices with exactly 1 marked is_correct=true.
- difficulty must be one of: easy, medium, hard.
  easy = recall/definition, medium = application/reasoning, hard = analysis/synthesis.
- source_excerpt must be a direct quote from the input (<= 200 chars).
- Do not repeat questions or choices.
- Questions must test understanding, not trivial facts.
"""

_JUDGE_PROMPT = """\
You are a strict exam-question quality reviewer. For each question, output a JSON
object with: score (0-10 float), clarity_score, single_answer_score,
distractor_score, grounding_score, reasons (list of short bullet strings).

Each correct answer MUST be supported by at least one supplied source chunk;
if not, deduct heavily from grounding_score and explain.

Return ONLY a JSON array, one object per input question, in input order.
"""

_CONTEXTUALIZE_PROMPT = """\
You are summarizing a chunk of educational material so a future retriever can
find it. Given the document title, section title (if any), and the chunk text,
return ONE short sentence (<= 30 words) that names the concrete topic / claim
of the chunk in plain language. Output the sentence only, no preamble.
"""

_SUBJECT_QA_PROMPT = """\
You are a study assistant for a specific university subject. Answer student
questions using ONLY the supplied source excerpts. If the excerpts don't
contain the answer, say so plainly.

When citing, use the marker [#CHUNK_ID] exactly where each claim appears;
multiple citations are fine. Do not invent citations.
"""

_HYDE_PROMPT = """\
You are expanding a search query for retrieval. Given the user query (or section
topic), write a short hypothetical answer or definition (<= 80 words) that uses
the vocabulary a textbook would use for this topic. Output prose only — no
preamble, no bullet points, no citations.
"""


def upgrade() -> None:
    # ---- enums --------------------------------------------------------------
    op.execute("CREATE TYPE ai_credential_provider AS ENUM ('anthropic','openai','cohere','voyage','qdrant')")
    op.execute("CREATE TYPE ai_credential_scope AS ENUM ('global','subject')")
    op.execute("CREATE TYPE ai_model_kind AS ENUM ('extraction','judge','embedding','rerank','chat','vision')")

    # ---- ai_prompts ---------------------------------------------------------
    op.create_table(
        "ai_prompts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("role", sa.Text(), nullable=False, server_default="system"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_hint", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ai_prompts_name", "ai_prompts", ["name"])
    op.create_index("ix_ai_prompts_name_version", "ai_prompts", ["name", "version"], unique=True)
    op.execute(
        "CREATE UNIQUE INDEX ux_ai_prompts_active_per_name "
        "ON ai_prompts (name) WHERE is_active = true"
    )

    # ---- ai_credentials -----------------------------------------------------
    op.create_table(
        "ai_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.Column(
            "provider",
            postgresql.ENUM(
                "anthropic", "openai", "cohere", "voyage", "qdrant",
                name="ai_credential_provider",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("display_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("key_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("key_last4", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "scope",
            postgresql.ENUM("global", "subject", name="ai_credential_scope", create_type=False),
            nullable=False,
            server_default="global",
        ),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("monthly_budget_usd", sa.Numeric(10, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ai_credentials_provider", "ai_credentials", ["provider"])
    op.create_index("ix_ai_credentials_alias", "ai_credentials", ["alias"], unique=True)

    # ---- ai_models ----------------------------------------------------------
    op.create_table(
        "ai_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column(
            "kind",
            postgresql.ENUM(
                "extraction", "judge", "embedding", "rerank", "chat", "vision",
                name="ai_model_kind",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("context_window", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_cost_per_mtoken", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("output_cost_per_mtoken", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("supports_streaming", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("supports_json_mode", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("supports_prompt_cache", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("embedding_dim", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ai_models_provider", "ai_models", ["provider"])
    op.create_index("ix_ai_models_kind", "ai_models", ["kind"])
    op.create_index("ix_ai_models_provider_model_id", "ai_models", ["provider", "model_id"], unique=True)

    # ---- generation_profiles -----------------------------------------------
    op.create_table(
        "generation_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("prompt_name", sa.Text(), nullable=False, server_default="extraction.system"),
        sa.Column("judge_prompt_name", sa.Text(), nullable=False, server_default="judge.rubric"),
        sa.Column("extraction_model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True),
        sa.Column("judge_model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True),
        sa.Column("embedding_model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rerank_model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True),
        sa.Column("credential_alias_extraction", sa.Text(), nullable=True),
        sa.Column("credential_alias_judge", sa.Text(), nullable=True),
        sa.Column("credential_alias_embedding", sa.Text(), nullable=True),
        sa.Column("credential_alias_rerank", sa.Text(), nullable=True),
        sa.Column("target_count", sa.Integer(), nullable=False, server_default="20"),
        sa.Column(
            "difficulty_mix",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text('\'{"easy": 0.3, "medium": 0.5, "hard": 0.2}\'::jsonb'),
        ),
        sa.Column("judge_threshold", sa.Numeric(3, 1), nullable=False, server_default="6.0"),
        sa.Column("dedup_threshold", sa.Numeric(3, 2), nullable=False, server_default="0.92"),
        sa.Column("top_k_retrieval", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("top_n_rerank", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("hybrid_alpha", sa.Numeric(3, 2), nullable=False, server_default="0.5"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_generation_profiles_subject_id", "generation_profiles", ["subject_id"])
    op.execute(
        "CREATE UNIQUE INDEX ux_gen_profiles_default_global "
        "ON generation_profiles ((true)) WHERE subject_id IS NULL AND is_default = true"
    )
    op.execute(
        "CREATE UNIQUE INDEX ux_gen_profiles_default_per_subject "
        "ON generation_profiles (subject_id) WHERE subject_id IS NOT NULL AND is_default = true"
    )

    # ---- seeds --------------------------------------------------------------
    _seed_prompts()
    _seed_models()
    _seed_default_profile()


def _seed_prompts() -> None:
    prompts = sa.table(
        "ai_prompts",
        sa.column("name", sa.Text),
        sa.column("version", sa.Integer),
        sa.column("role", sa.Text),
        sa.column("content", sa.Text),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        prompts,
        [
            {"name": "extraction.system", "version": 1, "role": "system", "content": _EXTRACTION_PROMPT, "is_active": True},
            {"name": "judge.rubric",      "version": 1, "role": "system", "content": _JUDGE_PROMPT,      "is_active": True},
            {"name": "contextualize.chunk", "version": 1, "role": "system", "content": _CONTEXTUALIZE_PROMPT, "is_active": True},
            {"name": "subject_qa.system", "version": 1, "role": "system", "content": _SUBJECT_QA_PROMPT, "is_active": True},
            {"name": "hyde.expand",       "version": 1, "role": "system", "content": _HYDE_PROMPT,       "is_active": True},
        ],
    )


def _seed_models() -> None:
    models = sa.table(
        "ai_models",
        sa.column("provider", sa.Text),
        sa.column("model_id", sa.Text),
        sa.column("display_name", sa.Text),
        sa.column("kind", sa.Text),
        sa.column("context_window", sa.Integer),
        sa.column("max_output_tokens", sa.Integer),
        sa.column("input_cost_per_mtoken", sa.Numeric),
        sa.column("output_cost_per_mtoken", sa.Numeric),
        sa.column("supports_streaming", sa.Boolean),
        sa.column("supports_json_mode", sa.Boolean),
        sa.column("supports_prompt_cache", sa.Boolean),
        sa.column("embedding_dim", sa.Integer),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(
        models,
        [
            # Anthropic
            {"provider": "anthropic", "model_id": "claude-opus-4-7",  "display_name": "Claude Opus 4.7",  "kind": "extraction", "context_window": 200_000, "max_output_tokens": 8192,
             "input_cost_per_mtoken": 15.0,  "output_cost_per_mtoken": 75.0,
             "supports_streaming": True, "supports_json_mode": True, "supports_prompt_cache": True, "embedding_dim": None, "sort_order": 10},
            {"provider": "anthropic", "model_id": "claude-sonnet-4-6", "display_name": "Claude Sonnet 4.6", "kind": "extraction", "context_window": 200_000, "max_output_tokens": 8192,
             "input_cost_per_mtoken": 3.0,   "output_cost_per_mtoken": 15.0,
             "supports_streaming": True, "supports_json_mode": True, "supports_prompt_cache": True, "embedding_dim": None, "sort_order": 20},
            {"provider": "anthropic", "model_id": "claude-haiku-4-5",  "display_name": "Claude Haiku 4.5",  "kind": "judge",      "context_window": 200_000, "max_output_tokens": 8192,
             "input_cost_per_mtoken": 1.0,   "output_cost_per_mtoken": 5.0,
             "supports_streaming": True, "supports_json_mode": True, "supports_prompt_cache": True, "embedding_dim": None, "sort_order": 30},

            # OpenAI
            {"provider": "openai", "model_id": "gpt-4o",       "display_name": "GPT-4o",       "kind": "extraction", "context_window": 128_000, "max_output_tokens": 4096,
             "input_cost_per_mtoken": 2.5,  "output_cost_per_mtoken": 10.0,
             "supports_streaming": True, "supports_json_mode": True, "supports_prompt_cache": False, "embedding_dim": None, "sort_order": 40},
            {"provider": "openai", "model_id": "gpt-4o-mini",  "display_name": "GPT-4o mini",  "kind": "judge",      "context_window": 128_000, "max_output_tokens": 4096,
             "input_cost_per_mtoken": 0.15, "output_cost_per_mtoken": 0.6,
             "supports_streaming": True, "supports_json_mode": True, "supports_prompt_cache": False, "embedding_dim": None, "sort_order": 50},

            # Embeddings
            {"provider": "openai", "model_id": "text-embedding-3-small", "display_name": "text-embedding-3-small", "kind": "embedding", "context_window": 8191, "max_output_tokens": 0,
             "input_cost_per_mtoken": 0.02, "output_cost_per_mtoken": 0.0,
             "supports_streaming": False, "supports_json_mode": False, "supports_prompt_cache": False, "embedding_dim": 1536, "sort_order": 60},
            {"provider": "openai", "model_id": "text-embedding-3-large", "display_name": "text-embedding-3-large", "kind": "embedding", "context_window": 8191, "max_output_tokens": 0,
             "input_cost_per_mtoken": 0.13, "output_cost_per_mtoken": 0.0,
             "supports_streaming": False, "supports_json_mode": False, "supports_prompt_cache": False, "embedding_dim": 3072, "sort_order": 70},

            # Rerankers
            {"provider": "cohere", "model_id": "rerank-v3",  "display_name": "Cohere Rerank v3",  "kind": "rerank", "context_window": 0, "max_output_tokens": 0,
             "input_cost_per_mtoken": 2.0, "output_cost_per_mtoken": 0.0,
             "supports_streaming": False, "supports_json_mode": False, "supports_prompt_cache": False, "embedding_dim": None, "sort_order": 80},
            {"provider": "voyage", "model_id": "rerank-2",   "display_name": "Voyage rerank-2",   "kind": "rerank", "context_window": 0, "max_output_tokens": 0,
             "input_cost_per_mtoken": 5.0, "output_cost_per_mtoken": 0.0,
             "supports_streaming": False, "supports_json_mode": False, "supports_prompt_cache": False, "embedding_dim": None, "sort_order": 90},
        ],
    )


def _seed_default_profile() -> None:
    """Insert a single global default profile, wiring the seeded models by lookup."""
    op.execute(
        """
        INSERT INTO generation_profiles
            (name, prompt_name, judge_prompt_name,
             extraction_model_id, judge_model_id, embedding_model_id, rerank_model_id,
             is_default)
        SELECT
            'Global default',
            'extraction.system',
            'judge.rubric',
            (SELECT id FROM ai_models WHERE provider='anthropic' AND model_id='claude-opus-4-7'),
            (SELECT id FROM ai_models WHERE provider='anthropic' AND model_id='claude-haiku-4-5'),
            (SELECT id FROM ai_models WHERE provider='openai'    AND model_id='text-embedding-3-small'),
            (SELECT id FROM ai_models WHERE provider='cohere'    AND model_id='rerank-v3'),
            true
        """
    )


def downgrade() -> None:
    op.drop_index("ux_gen_profiles_default_per_subject", table_name="generation_profiles")
    op.drop_index("ux_gen_profiles_default_global", table_name="generation_profiles")
    op.drop_index("ix_generation_profiles_subject_id", table_name="generation_profiles")
    op.drop_table("generation_profiles")

    op.drop_index("ix_ai_models_provider_model_id", table_name="ai_models")
    op.drop_index("ix_ai_models_kind", table_name="ai_models")
    op.drop_index("ix_ai_models_provider", table_name="ai_models")
    op.drop_table("ai_models")

    op.drop_index("ix_ai_credentials_alias", table_name="ai_credentials")
    op.drop_index("ix_ai_credentials_provider", table_name="ai_credentials")
    op.drop_table("ai_credentials")

    op.drop_index("ux_ai_prompts_active_per_name", table_name="ai_prompts")
    op.drop_index("ix_ai_prompts_name_version", table_name="ai_prompts")
    op.drop_index("ix_ai_prompts_name", table_name="ai_prompts")
    op.drop_table("ai_prompts")

    op.execute("DROP TYPE ai_model_kind")
    op.execute("DROP TYPE ai_credential_scope")
    op.execute("DROP TYPE ai_credential_provider")
