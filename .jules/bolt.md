## 2024-05-23 - Hybrid Search Re-computation
**Learning:** In hybrid search (Vector + BM25), when using exact search (or MRL) that computes all scores, cache the scores! Re-computing dot products for BM25 candidates that missed the vector cut is wasteful if you already have the full score matrix.
**Action:** Always check if intermediate heavy computations (like full matrix multiplication) can be reused in later fusion stages.

## 2025-12-22 - Avoid Lazy-Loading the App Entrypoint
**Learning:** In this Vite/Rolldown build, `React.lazy(() => import("./App"))` at the entrypoint introduces an extra JS chunk request and can worsen first-load metrics even when the chunk itself is small.
**Action:** Keep code-splitting for secondary panels, but import `App` eagerly in `src/main.tsx` to remove the entrypoint waterfall.
