"""
Retrieval package.

Keep __init__ import-light; HybridRetriever pulls in numpy/faiss and should be
imported explicitly from `backend.app.retrieval.hybrid_retriever`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Only for type checkers; do not import heavy modules at runtime.
    from .hybrid_retriever import HybridRetriever, ScoredChunk


def __getattr__(name: str) -> Any:
    """
    Preserve historical `from backend.app.retrieval import HybridRetriever` usage
    without importing heavy dependencies at package import time.
    """

    if name in {"HybridRetriever", "ScoredChunk"}:
        from warnings import warn

        warn(
            f"`backend.app.retrieval.{name}` is deprecated; import it from "
            "`backend.app.retrieval.hybrid_retriever` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from .hybrid_retriever import HybridRetriever, ScoredChunk

        return {"HybridRetriever": HybridRetriever, "ScoredChunk": ScoredChunk}[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    # Keep introspection usable while remaining import-light.
    return sorted(list(globals().keys()) + ["HybridRetriever", "ScoredChunk"])


__all__: list[str] = []
