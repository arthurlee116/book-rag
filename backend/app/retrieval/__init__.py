"""
Retrieval package.

Keep __init__ import-light; HybridRetriever pulls in numpy/faiss and should be
imported explicitly from `backend.app.retrieval.hybrid_retriever`.
"""

__all__ = ["HybridRetriever", "ScoredChunk"]
