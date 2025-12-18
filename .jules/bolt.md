## 2024-05-23 - Hybrid Search Re-computation
**Learning:** In hybrid search (Vector + BM25), when using exact search (or MRL) that computes all scores, cache the scores! Re-computing dot products for BM25 candidates that missed the vector cut is wasteful if you already have the full score matrix.
**Action:** Always check if intermediate heavy computations (like full matrix multiplication) can be reused in later fusion stages.
