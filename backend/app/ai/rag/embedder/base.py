"""Embedder protocol (Phase 3)."""

from __future__ import annotations

from typing import Protocol


class Embedder(Protocol):
    name: str
    dim: int
    version: str

    async def embed(self, texts: list[str]) -> list[list[float]]: ...
