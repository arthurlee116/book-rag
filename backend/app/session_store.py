from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from .models.chunk import ChunkModel
from .retrieval.hybrid_retriever import HybridRetriever, ScoredChunk


@dataclass
class ChatTurn:
    role: str  # "user" | "assistant" (and optionally "system")
    content: str
    # For assistant turns only: citations returned alongside this message.
    citations: list[ChunkModel] = field(default_factory=list)


@dataclass
class SessionState:
    session_id: str
    created_at: float = field(default_factory=lambda: time.time())
    last_access_at: float = field(default_factory=lambda: time.time())
    expires_at: float = 0.0

    filename: str | None = None
    doc_language: str | None = None

    chunks: list[ChunkModel] = field(default_factory=list)
    retriever: HybridRetriever | None = None

    chat_history: list[ChatTurn] = field(default_factory=list)

    # Used for export: stable mapping chunk.id -> global reference number
    reference_ids: dict[str, int] = field(default_factory=dict)
    references: list[ChunkModel] = field(default_factory=list)

    # Processing state
    ingest_status: str = "idle"  # "idle" | "processing" | "ready" | "error"
    ingest_error: str | None = None

    # SSE logs
    log_seq: int = 0
    log_history: deque[tuple[int, str]] = field(default_factory=lambda: deque(maxlen=2000))
    log_event: asyncio.Event = field(default_factory=asyncio.Event)

    # concurrency
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def touch(self, *, ttl_seconds: int) -> None:
        now = time.time()
        self.last_access_at = now
        self.expires_at = now + ttl_seconds

    async def log(self, message: str) -> None:
        line = message if message.endswith("\n") else f"{message}\n"
        self.log_seq += 1
        self.log_history.append((self.log_seq, line))
        self.log_event.set()

    def register_references(self, citations: list[ChunkModel]) -> None:
        """
        Assigns stable global reference numbers to chunk IDs in order of first use.
        """
        for c in citations:
            if c.id in self.reference_ids:
                continue
            self.reference_ids[c.id] = len(self.references) + 1
            self.references.append(c)


# Global in-memory session store (ephemeral; cleared on process restart)
SESSIONS: dict[str, SessionState] = {}


def get_or_create_session(*, session_id: str, ttl_seconds: int) -> SessionState:
    s = SESSIONS.get(session_id)
    if s is None:
        s = SessionState(session_id=session_id)
        SESSIONS[session_id] = s
    s.touch(ttl_seconds=ttl_seconds)
    return s


def get_session(*, session_id: str, ttl_seconds: int) -> SessionState | None:
    s = SESSIONS.get(session_id)
    if s is None:
        return None
    s.touch(ttl_seconds=ttl_seconds)
    return s


def delete_session(session_id: str) -> None:
    SESSIONS.pop(session_id, None)


def cleanup_expired_sessions() -> int:
    now = time.time()
    expired = [sid for sid, s in SESSIONS.items() if s.expires_at and s.expires_at <= now]
    for sid in expired:
        SESSIONS.pop(sid, None)
    return len(expired)
