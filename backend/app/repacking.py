from __future__ import annotations


def repack_chunks_reverse(chunks: list) -> list:
    """
    Re-pack chunks in reverse order: most relevant at the end (closer to query).
    Research shows this improves LLM attention to relevant content.
    """
    if len(chunks) <= 1:
        return chunks
    return chunks[::-1]


def repack_chunks(chunks: list, *, strategy: str) -> list:
    """
    Re-pack chunks according to strategy.

    Supported strategies:
    - "reverse": reverse chunk order (most relevant near end of context)
    - "forward": keep current order (no re-packing)
    """
    normalized = (strategy or "").strip().lower()
    if normalized in {"forward", "none", "off", "disabled", "disable"}:
        return chunks
    # Default behavior is "reverse" (including empty/unknown values).
    return repack_chunks_reverse(chunks)


def apply_repack_strategy(
    chunks: list,
    *,
    fast_mode: bool,
    repack_strategy: str,
) -> list:
    """
    Apply configured re-packing unless fast mode explicitly opts out.
    """
    if fast_mode:
        return chunks
    return repack_chunks(chunks, strategy=repack_strategy)

