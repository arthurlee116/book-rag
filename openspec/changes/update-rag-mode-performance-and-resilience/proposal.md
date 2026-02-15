# Change: Improve Fast/Normal Retrieval Modes for Performance and Resilience

## Why
The current backend retrieval implementation is strong functionally, but there are several issues that reduce performance or reliability in production:

1. Non-critical language alignment failures can fail the whole chat request.
2. HyDE is unintentionally coupled to query fusion toggle.
3. OpenRouter retries include deterministic failures (for example 4xx), adding latency and cost.
4. Normal mode executes independent steps sequentially, increasing latency.
5. Retriever hot paths contain avoidable O(n log n) and O(k*n) overhead.
6. Config defaults are inconsistent between `Settings` defaults and `load_settings()` defaults.

These issues impact both user-perceived speed (especially normal mode) and operational robustness.

## What Changes
- Make language alignment fail-open: if translation fails, continue with original query.
- Decouple HyDE from query fusion so `ERR_HYDE_ENABLED` works independently.
- Restrict retry policy to transient/network failures only.
- Parallelize independent normal-mode steps:
  - query variants generation and HyDE generation
  - per-query retrieval calls
- Optimize retriever hot path:
  - use `argpartition` instead of full `argsort` in MRL top-k selection
  - remove repeated list index lookup in metrics (`self._chunks.index(...)`)
- Align default configuration values for chunk size and drift thresholds.
- Add/expand tests for new behavior.

## Impact
- Affected specs: `retrieval-pipeline`
- Affected code:
  - `backend/app/main.py`
  - `backend/app/openrouter_client.py`
  - `backend/app/retrieval/hybrid_retriever.py`
  - `backend/app/config.py`
  - `backend/tests/*`

## Assumptions
1. User instruction in this thread is treated as explicit approval to implement immediately after proposal creation.
2. Existing API contracts (`/chat` request/response shape) remain stable.
3. Performance optimizations should preserve current retrieval quality intent (recall-oriented normal mode, lower-latency fast mode).
