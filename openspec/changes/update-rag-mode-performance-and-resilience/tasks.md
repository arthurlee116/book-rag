## 1. Proposal Validation
- [x] 1.1 Run `openspec validate update-rag-mode-performance-and-resilience --strict --no-interactive`

## 2. Backend Reliability
- [x] 2.1 Make translation alignment fail-open in chat flow
- [x] 2.2 Decouple HyDE execution from query fusion toggle
- [x] 2.3 Restrict OpenRouter retry conditions to transient failures

## 3. Backend Performance
- [x] 3.1 Parallelize independent normal-mode LLM preprocessing tasks
- [x] 3.2 Parallelize per-query retrieval execution with bounded concurrency
- [x] 3.3 Optimize MRL top-k selection to avoid full sort
- [x] 3.4 Remove O(k*n) chunk index lookup in retrieval metrics

## 4. Config and Tests
- [x] 4.1 Align inconsistent config defaults
- [x] 4.2 Add/update unit tests for:
- [x] 4.3 HyDE independent toggle behavior
- [x] 4.4 Translation fail-open behavior
- [x] 4.5 Retriever MRL/index optimizations behavior

## 5. Full Validation
- [x] 5.1 Run backend unit tests
- [x] 5.2 Run frontend lint and build
- [x] 5.3 Run OpenSpec strict validation
