from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from ..models.chunk import ChunkModel

from .file_parser import ParsedBlock


def estimate_tokens(text: str) -> int:
    """
    Lightweight token estimate (no tokenizer dependency).
    - CJK chars count as ~1 token each
    - Latin words/numbers count as ~1 token each
    """

    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z0-9]+", text))
    return cjk + latin


class Chunker:
    def __init__(self, *, target_tokens: int = 512, overlap_tokens: int = 50) -> None:
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, *, blocks: list[ParsedBlock]) -> list[ChunkModel]:
        chunks: list[ChunkModel] = []
        buf_text: list[str] = []
        buf_rich: list[str] = []
        buf_meta: dict[str, Any] = {}
        buf_tokens = 0
        overlap_text: list[str] = []
        overlap_rich: list[str] = []

        def flush() -> None:
            nonlocal buf_text, buf_rich, buf_meta, buf_tokens, chunks, overlap_text, overlap_rich
            content = "\n\n".join([t for t in buf_text if t.strip()]).strip()
            if not content:
                buf_text, buf_rich, buf_meta, buf_tokens = [], [], {}, 0
                overlap_text, overlap_rich = [], []
                return

            rich_content = "<br/><br/>".join([t for t in buf_rich if t.strip()]).strip()
            chunk_id = uuid4().hex
            chunks.append(
                ChunkModel(
                    id=chunk_id,
                    content=content,
                    rich_content=rich_content or content,
                    prev_content=None,
                    next_content=None,
                    metadata={
                        **buf_meta,
                        "chunk_index": len(chunks),
                    },
                )
            )

            # Build overlap from end of current buffer
            if self.overlap_tokens > 0:
                overlap_text, overlap_rich = [], []
                collected = 0
                for txt, rich in zip(reversed(buf_text), reversed(buf_rich)):
                    t = estimate_tokens(txt)
                    if collected + t <= self.overlap_tokens:
                        overlap_text.insert(0, txt)
                        overlap_rich.insert(0, rich)
                        collected += t
                    else:
                        break

            buf_text, buf_rich, buf_meta, buf_tokens = [], [], {}, 0

        for block in blocks:
            block_text = block.text.strip()
            if not block_text:
                continue
            block_tokens = estimate_tokens(block_text)

            if buf_tokens > 0 and (buf_tokens + block_tokens) > self.target_tokens:
                flush()
                # Start new chunk with overlap from previous
                if overlap_text:
                    buf_text = overlap_text[:]
                    buf_rich = overlap_rich[:]
                    buf_tokens = sum(estimate_tokens(t) for t in buf_text)
                    overlap_text, overlap_rich = [], []

            buf_text.append(block_text)
            buf_rich.append(block.rich_text.strip() or block_text)
            buf_tokens += block_tokens

            # Carry forward chapter-like metadata (best-effort).
            chapter_title = block.metadata.get("chapter_title")
            if chapter_title:
                buf_meta["chapter_title"] = chapter_title
            source = block.metadata.get("source")
            if source:
                buf_meta["source"] = source

        flush()

        # Redundant prev/next content fill (required by spec).
        for i in range(len(chunks)):
            prev_text = chunks[i - 1].content if i > 0 else None
            next_text = chunks[i + 1].content if i < (len(chunks) - 1) else None
            chunks[i].prev_content = prev_text
            chunks[i].next_content = next_text

        return chunks
