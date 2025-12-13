"""
Models package.

Avoid importing heavy dependencies at package import time so lightweight tooling
(like unittest discovery) can run without requiring the full backend deps.
"""

__all__ = ["ChunkModel"]  # for type-checkers / consumers
