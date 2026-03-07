from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RetrievalStep(BaseModel):
    """Base model for a single retrieval step."""

    name: str
    skipped: bool = False
    reason: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class ChunkPreview(BaseModel):
    """Preview for final context chunks."""

    chunk_id: str
    rank: int
    score: float
    preview: str = Field(..., max_length=200)


class EvaluationRecord(BaseModel):
    """Full evaluation record for a chat query."""

    session_id: str
    user_query: str
    mode: str  # "normal" or "fast"
    timestamp: str  # ISO8601
    steps: List[RetrievalStep] = Field(default_factory=list)
    final_context: List[ChunkPreview] = Field(default_factory=list)


@dataclass
class RetrievalMetrics:
    """Mutable collector for retrieval metrics during pipeline execution."""

    session_id: str
    user_query: str
    mode: str
    start_time: datetime
    steps: List[Dict[str, Any]] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def add_step(
        self,
        name: str,
        *,
        skipped: bool = False,
        reason: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        step_data = {
            "name": name,
            "skipped": skipped,
            "reason": reason,
            "data": data if data else None,
        }
        with self._lock:
            self.steps.append(step_data)

    def to_record(self) -> EvaluationRecord:
        timestamp = self.start_time.isoformat()
        with self._lock:
            steps_snapshot = list(self.steps)

        pyd_steps = [RetrievalStep(**step) for step in steps_snapshot]
        # Extract final_context from the last "final_context" step
        final_chunks = []
        for step in reversed(steps_snapshot):
            if step.get("name") == "final_context":
                raw_chunks = step.get("data", {}).get("chunks", [])
                final_chunks = [
                    ChunkPreview(
                        chunk_id=c["chunk_id"],
                        rank=c["rank"],
                        score=c["score"],
                        preview=c["preview"],
                    )
                    for c in raw_chunks
                    if isinstance(c, dict) and all(k in c for k in ["chunk_id", "rank", "score", "preview"])
                ]
                break
        return EvaluationRecord(
            session_id=self.session_id,
            user_query=self.user_query,
            mode=self.mode,
            timestamp=timestamp,
            steps=pyd_steps,
            final_context=final_chunks,
        )
