## 2024-05-23 - Hybrid Search Re-computation
**Learning:** In hybrid search (Vector + BM25), when using exact search (or MRL) that computes all scores, cache the scores! Re-computing dot products for BM25 candidates that missed the vector cut is wasteful if you already have the full score matrix.
**Action:** Always check if intermediate heavy computations (like full matrix multiplication) can be reused in later fusion stages.

## 2025-12-22 - Avoid Lazy-Loading the App Entrypoint
**Learning:** In this Vite/Rolldown build, `React.lazy(() => import("./App"))` at the entrypoint introduces an extra JS chunk request and can worsen first-load metrics even when the chunk itself is small.
**Action:** Keep code-splitting for secondary panels, but import `App` eagerly in `src/main.tsx` to remove the entrypoint waterfall.

## 2025-12-22 - Avoid Above-the-Fold React.lazy Waterfalls
**Learning:** Lazy-loading multiple above-the-fold panels (Upload/Chat/Logs/Eval) causes a chunk waterfall because all `React.lazy()` imports fire immediately on first render; this adds extra request overhead and can delay first meaningful UI.
**Action:** Keep only secondary/conditional panels (e.g. `DocumentPanel`) as dynamic imports; import the main panels eagerly so the initial route ships in a single app chunk.
