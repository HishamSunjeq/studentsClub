"""Top-tier RAG stack: hybrid (dense + sparse) on Qdrant, with
contextual retrieval, HyDE query expansion, and reranking (Phase 3+).
"""

CHUNKS_COLLECTION = "chunks"
QUESTIONS_COLLECTION = "questions"

# Bump whenever the embed pipeline meaningfully changes (model, sparse
# encoder, or contextualization prompt). Stored on each row so a
# `re-embed` job can find anything stale.
EMBEDDING_VERSION = "v1"
