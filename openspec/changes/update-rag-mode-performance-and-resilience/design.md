## Context
The service intentionally uses a high-recall normal mode and a low-latency fast mode. We need to preserve this product intent while removing reliability regressions and avoidable latency overhead.

## Goals / Non-Goals
- Goals:
- Keep behavior compatible for existing clients.
- Improve p50/p95 latency in normal mode by parallelizing independent work.
- Improve robustness by avoiding hard failures in optional preprocessing steps.
- Non-Goals:
- No API redesign.
- No model/vendor change.
- No architectural persistence changes.

## Decisions
- Decision: translation alignment is optional preprocessing and MUST fail open.
- Decision: HyDE and query fusion toggles are independent controls.
- Decision: retries are limited to network/transient server conditions.
- Decision: normal-mode independent tasks run concurrently with bounded concurrency.
- Decision: retriever top-k uses partial selection (`argpartition`) for MRL path.

## Risks / Trade-offs
- Parallelism can increase burst CPU usage.
- Mitigation: bound concurrency with semaphore.

- Restricting retries may reduce automatic recovery for some edge errors.
- Mitigation: include 429 and 5xx in retry policy and keep 3 attempts.

## Migration Plan
1. Land reliability fixes first (fail-open + retry policy).
2. Land retrieval parallelization and hot-path optimization.
3. Land config consistency and tests.
4. Validate end-to-end.

## Open Questions
- None. This change follows the user’s explicit instruction to proceed autonomously.
