from __future__ import annotations

from collections import defaultdict


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        s = (raw or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def rrf_fuse(
    rankings: list[list[str]],
    *,
    k: int = 60,
    max_results: int | None = None,
) -> list[str]:
    """
    Reciprocal Rank Fusion (RRF).

    Each `rankings[i]` is an ordered list of doc IDs (best first).
    Fused score is: sum(1 / (k + rank)).
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    if not rankings:
        return []

    scores: dict[str, float] = defaultdict(float)
    first_rank: dict[str, int] = {}

    for r in rankings:
        for idx, doc_id in enumerate(r, start=1):
            if not doc_id:
                continue
            scores[doc_id] += 1.0 / (k + idx)
            if doc_id not in first_rank:
                first_rank[doc_id] = idx

    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], first_rank.get(kv[0], 10**9), kv[0]))
    fused = [doc_id for doc_id, _ in ordered]
    if max_results is not None:
        return fused[: max(0, int(max_results))]
    return fused

