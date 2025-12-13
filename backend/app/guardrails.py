from __future__ import annotations

import re
from dataclasses import dataclass


STRICT_NO_MENTION = "The document does not mention this."


@dataclass(frozen=True)
class GuardrailResult:
    ok: bool
    answer: str
    reason: str | None = None


_CITATION_RE = re.compile(r"\[(\d+)\]")


def extract_citation_numbers(text: str) -> list[int]:
    nums: list[int] = []
    for m in _CITATION_RE.finditer(text):
        try:
            nums.append(int(m.group(1)))
        except ValueError:
            continue
    # ordered unique
    seen: set[int] = set()
    ordered: list[int] = []
    for n in nums:
        if n in seen:
            continue
        seen.add(n)
        ordered.append(n)
    return ordered


def enforce_strict_rag_answer(
    *,
    answer: str,
    context_size: int,
    require_citations: bool = True,
) -> GuardrailResult:
    """
    Enforces guardrails on the assistant answer:
    - If the answer is not the strict "no mention" string, require at least one citation [n]
    - Citations must be in range 1..context_size
    - If guardrails fail, return the strict fallback response
    """

    raw = (answer or "").strip()
    if not raw:
        return GuardrailResult(ok=False, answer=STRICT_NO_MENTION, reason="empty_answer")

    if raw == STRICT_NO_MENTION:
        return GuardrailResult(ok=True, answer=raw)

    nums = extract_citation_numbers(raw)

    if require_citations and not nums:
        return GuardrailResult(
            ok=False,
            answer=STRICT_NO_MENTION,
            reason="missing_citations",
        )

    if any(n < 1 or n > context_size for n in nums):
        return GuardrailResult(
            ok=False,
            answer=STRICT_NO_MENTION,
            reason="out_of_range_citations",
        )

    return GuardrailResult(ok=True, answer=raw)

