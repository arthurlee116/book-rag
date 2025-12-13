from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChunkModel(BaseModel):
    id: str
    content: str  # The current chunk text
    rich_content: str  # Text with basic HTML (<b>, <i>, <h3>) preserved
    prev_content: str | None = None  # Text of the previous chunk (for context)
    next_content: str | None = None  # Text of the next chunk (for context)
    metadata: dict[str, Any] = Field(default_factory=dict)

