from __future__ import annotations

import asyncio
from datetime import datetime
from typing import cast

from fastapi import HTTPException
import numpy as np
from pydantic import BaseModel, Field

from .config import Settings
from .guardrails import STRICT_NO_MENTION, enforce_strict_rag_answer
from .ingestion.chunker import estimate_tokens
from .models.chunk import ChunkModel
from .openrouter_client import ChatMessage
from .openrouter_client import OpenRouterClient, OpenRouterError
from .repacking import apply_repack_strategy
from .retrieval.evaluation import RetrievalMetrics
from .retrieval.fusion import dedupe_keep_order, rrf_fuse
from .retrieval.hybrid_retriever import detect_dominant_language
from .session_store import ChatTurn, get_session


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Ephemeral session id")
    message: str = Field(..., description="User query")
    top_k: int = Field(default=5, ge=1, le=10)
    fast_mode: bool = Field(
        default=False,
        description="Use baseline retrieval (faster, less accurate). Default is accurate mode.",
    )


class ChatResponse(BaseModel):
    answer: str
    citations: list[dict]


def _estimate_prompt_tokens(*, text_parts: list[str]) -> int:
    return sum(estimate_tokens(t) for t in text_parts if t)


def _unique_nonempty(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        s = (raw or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _weighted_embedding_mean(embeddings, *, decay: float = 0.7):
    """
    Weighted average of embeddings. First embedding gets weight 1.0,
    subsequent ones decay exponentially (decay^i).
    """
    embs = np.asarray(embeddings, dtype=np.float32)
    if embs.ndim != 2 or embs.shape[0] == 0:
        return embs[0] if embs.shape[0] > 0 else embs
    n = embs.shape[0]
    weights = np.array([decay**i for i in range(n)], dtype=np.float32)
    weights /= weights.sum()
    return np.average(embs, axis=0, weights=weights).astype(np.float32)


def _build_embedding_query_inputs(
    *,
    settings: Settings,
    queries: list[str],
    include_raw_override: bool | None = None,
) -> list[str]:
    """
    Build embedding inputs for user queries, optionally using instruction-aware format.
    """
    queries = _unique_nonempty(queries)
    if not queries:
        return []

    inputs: list[str] = []
    if settings.embedding_query_use_instruction:
        template = settings.embedding_query_instruction_template
        task = settings.embedding_query_task
        for q in queries:
            try:
                inputs.append(template.format(task=task, query=q))
            except Exception:
                # Fallback: if template is invalid, still provide something reasonable.
                inputs.append(f"Instruct: {task}\nQuery: {q}")

    include_raw = (
        settings.embedding_query_include_raw
        if include_raw_override is None
        else bool(include_raw_override)
    )
    if include_raw or not inputs:
        inputs.extend(queries)

    return _unique_nonempty(inputs)


def _trim_text(text: str, *, max_chars: int) -> str:
    t = (text or "").strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1].rstrip() + "…"


def _build_context_blocks(*, chunks: list, include_neighbors: bool = True) -> list[str]:
    """
    Render numbered context blocks like:
      [1] PREV: ...
          CHUNK: ...
          NEXT: ...
    The numbering must align with the citations list returned to the frontend.
    """
    blocks: list[str] = []
    for i, ch in enumerate(chunks, start=1):
        parts: list[str] = []
        if include_neighbors and getattr(ch, "prev_content", None):
            prev = _trim_text(ch.prev_content or "", max_chars=600)
            if prev:
                parts.append(f"PREV:\n{prev}")
        parts.append(f"CHUNK:\n{(ch.content or '').strip()}")
        if include_neighbors and getattr(ch, "next_content", None):
            nxt = _trim_text(ch.next_content or "", max_chars=600)
            if nxt:
                parts.append(f"NEXT:\n{nxt}")
        blocks.append(f"[{i}] " + "\n\n".join(parts))
    return blocks


def _extract_citation_numbers(answer: str) -> list[int]:
    # Back-compat wrapper used by export rewriting.
    from .guardrails import extract_citation_numbers

    return extract_citation_numbers(answer)


def _normalize_language_tag(raw: str) -> str:
    lang = (raw or "").strip().lower()
    if not lang:
        return "en"
    if lang.startswith("zh"):
        return "zh"
    if lang.startswith("en"):
        return "en"
    return lang


def _decide_language_alignment(
    *,
    settings: Settings,
    user_query: str,
    doc_language: str,
    fast_mode: bool,
) -> tuple[bool, str]:
    doc_lang = _normalize_language_tag(doc_language)

    if fast_mode and not settings.fast_mode_language_alignment:
        return False, "fast_mode_disabled"

    # Query language detector currently provides reliable hints for en/zh.
    if doc_lang in {"en", "zh"}:
        q_lang = detect_dominant_language(user_query)
        if q_lang == doc_lang:
            return False, "already_aligned"

    return True, "enabled"


async def _align_query_for_retrieval(
    *,
    session,
    openrouter: OpenRouterClient,
    user_query: str,
    doc_language: str,
    should_align: bool,
    skip_reason: str,
    metrics: RetrievalMetrics,
) -> str:
    if not should_align:
        await session.log(f"[LOG] Chat: skipping language alignment ({skip_reason}).")
        metrics.add_step("language_alignment", skipped=True, reason=skip_reason)
        return user_query

    await session.log("[LOG] Chat: translating query for keyword alignment...")
    try:
        expanded_query = await openrouter.translate_query_for_doc_language(
            query=user_query, doc_language=str(doc_language)
        )
    except OpenRouterError as e:
        await session.log(
            f"[LOG] WARNING: language alignment failed ({e}); using original query."
        )
        metrics.add_step(
            "language_alignment",
            skipped=True,
            reason="api_error_fallback",
            data={
                "original": user_query,
                "translated": user_query,
            },
        )
        return user_query

    metrics.add_step(
        "language_alignment",
        data={
            "original": user_query,
            "translated": expanded_query,
        },
    )
    return expanded_query


async def _build_normal_mode_query_expansions(
    *,
    session,
    openrouter: OpenRouterClient,
    settings: Settings,
    base_query: str,
    user_query: str,
    doc_language: str,
) -> tuple[list[str], str]:
    variants: list[str] = []
    hyde_text = ""

    tasks: dict[str, asyncio.Task] = {}
    if settings.query_fusion_enabled:
        await session.log("[LOG] Chat: generating query variants (multi-query)...")
        tasks["variants"] = asyncio.create_task(
            openrouter.generate_query_variants(
                query=base_query,
                doc_language=str(doc_language),
                n=settings.query_variants_count,
            )
        )
    if settings.hyde_enabled:
        await session.log("[LOG] Chat: generating HyDE passage (retrieval-only)...")
        tasks["hyde"] = asyncio.create_task(
            openrouter.generate_hyde_passage(
                query=base_query,
                doc_language=str(doc_language),
                max_words=settings.hyde_max_words,
            )
        )

    if tasks:
        task_names = list(tasks.keys())
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for name, result in zip(task_names, results):
            if isinstance(result, Exception):
                await session.log(f"[LOG] WARNING: {name} generation failed: {result}")
                continue
            if name == "variants":
                variants = [v for v in result if isinstance(v, str)]  # type: ignore[union-attr]
            elif name == "hyde":
                hyde_text = str(result or "").strip()

    if settings.query_fusion_enabled:
        query_texts = dedupe_keep_order([base_query, user_query] + variants)
    else:
        query_texts = dedupe_keep_order([base_query, user_query])

    return query_texts, hyde_text


async def run_chat(
    *,
    req: ChatRequest,
    settings: Settings,
    openrouter: OpenRouterClient,
) -> ChatResponse:
    session = get_session(session_id=req.session_id, ttl_seconds=settings.session_ttl_seconds)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session")

    async with session.lock:
        if session.ingest_status != "ready" or session.retriever is None:
            raise HTTPException(
                status_code=400, detail="No active document. Upload and wait until Ready."
            )
        retriever = session.retriever
        doc_language = session.doc_language or retriever.doc_language or "en"

    user_query = req.message.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Empty message")

    metrics = RetrievalMetrics(
        session_id=req.session_id,
        user_query=user_query,
        mode="fast" if req.fast_mode else "normal",
        start_time=datetime.now(),
    )

    should_align, align_reason = _decide_language_alignment(
        settings=settings,
        user_query=user_query,
        doc_language=str(doc_language),
        fast_mode=req.fast_mode,
    )
    expanded_query = await _align_query_for_retrieval(
        session=session,
        openrouter=openrouter,
        user_query=user_query,
        doc_language=str(doc_language),
        should_align=should_align,
        skip_reason=align_reason,
        metrics=metrics,
    )

    async def _search_retriever_async(**kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: retriever.search(**kwargs),
        )

    if req.fast_mode:
        await session.log("[LOG] Chat: fast mode enabled -> baseline retrieval.")

        await session.log("[LOG] Chat: embedding query (instruction-aware)...")
        try:
            query_variants = _unique_nonempty([user_query, expanded_query])
            embed_inputs = _build_embedding_query_inputs(
                settings=settings,
                queries=query_variants,
                include_raw_override=settings.fast_mode_include_raw_query,
            )
            if not embed_inputs:
                raise HTTPException(status_code=400, detail="Empty message")
            q_embs = await openrouter.embeddings(model=settings.embedding_model, inputs=embed_inputs)
        except OpenRouterError as e:
            raise HTTPException(status_code=502, detail=f"OpenRouter embedding error: {e}") from e

        if q_embs.ndim != 2 or q_embs.shape[0] < 1:
            raise HTTPException(status_code=500, detail="Unexpected embedding response shape")

        # Fast mode: weighted aggregation prioritizes earlier (raw user) forms.
        fast_aggregation_decay = float(
            settings.fast_mode_embedding_aggregation_decay
            if settings.fast_mode_embedding_aggregation_decay > 0
            else settings.embedding_aggregation_decay
        )
        query_embedding = _weighted_embedding_mean(q_embs, decay=fast_aggregation_decay)

        # Fast mode: use MRL lower dimension for faster vector search.
        search_dim = settings.embedding_dim_fast_mode
        await session.log(f"[LOG] Chat: hybrid retrieval with MRL (dim={search_dim})...")
        scored = await _search_retriever_async(
            query=user_query,
            query_embedding=query_embedding,
            expanded_query=expanded_query,
            top_k=req.top_k,
            search_dim=search_dim,
            candidate_k_override=settings.fast_mode_candidate_k,
            metrics=metrics,
        )
        retrieved_chunks = [s.chunk for s in scored]

        metrics.add_step("drift_filter", skipped=True, reason="fast_mode")
        metrics.add_step("llm_rerank", skipped=True, reason="fast_mode")
    else:
        base_query = (expanded_query or "").strip() or user_query

        query_texts, hyde_text = await _build_normal_mode_query_expansions(
            session=session,
            openrouter=openrouter,
            settings=settings,
            base_query=base_query,
            user_query=user_query,
            doc_language=str(doc_language),
        )

        # Embed all query texts (and optional HyDE) in one call.
        await session.log("[LOG] Chat: embedding query variants (instruction-aware)...")
        embed_inputs: list[str] = []
        slices: dict[str, slice] = {}
        for q in query_texts:
            inputs_for_q = _build_embedding_query_inputs(settings=settings, queries=[q])
            if not inputs_for_q:
                continue
            start = len(embed_inputs)
            embed_inputs.extend(inputs_for_q)
            end = len(embed_inputs)
            slices[q] = slice(start, end)

        if hyde_text.strip():
            start = len(embed_inputs)
            embed_inputs.append(hyde_text.strip())
            end = len(embed_inputs)
            slices["__hyde__"] = slice(start, end)

        if not embed_inputs:
            raise HTTPException(status_code=400, detail="Empty message")

        try:
            q_embs = await openrouter.embeddings(model=settings.embedding_model, inputs=embed_inputs)
        except OpenRouterError as e:
            raise HTTPException(status_code=502, detail=f"OpenRouter embedding error: {e}") from e

        if q_embs.ndim != 2 or q_embs.shape[0] != len(embed_inputs):
            raise HTTPException(status_code=500, detail="Unexpected embedding response shape")

        def cosine(a: np.ndarray, b: np.ndarray) -> float:
            aa = np.asarray(a, dtype=np.float32).reshape(-1)
            bb = np.asarray(b, dtype=np.float32).reshape(-1)
            denom = float(np.linalg.norm(aa) * np.linalg.norm(bb))
            if denom < 1e-12:
                return 0.0
            return float(np.dot(aa, bb) / denom)

        query_vecs: dict[str, np.ndarray] = {}
        aggregation_decay = float(settings.embedding_aggregation_decay)
        for q, sl in slices.items():
            if q == "__hyde__":
                continue
            vec = _weighted_embedding_mean(q_embs[sl], decay=aggregation_decay)
            query_vecs[q] = vec

        base_vec = query_vecs.get(base_query)
        if base_vec is None and query_vecs:
            base_vec = next(iter(query_vecs.values()))

        # Drift filter (recall-oriented): only drop clearly off-topic variants.
        if base_vec is not None:
            scored_variants: list[tuple[float, str]] = []
            for q in query_texts:
                if q == base_query:
                    continue
                v = query_vecs.get(q)
                if v is None:
                    continue
                scored_variants.append((cosine(base_vec, v), q))

            scored_variants.sort(key=lambda x: x[0], reverse=True)
            kept: list[str] = [base_query]
            for sim, q in scored_variants:
                if settings.drift_filter_enabled and sim < settings.drift_sim_threshold:
                    continue
                if len(kept) >= max(1, settings.query_variants_max):
                    break
                kept.append(q)
            query_texts = kept

        # Optional HyDE drift filter.
        use_hyde = False
        hyde_vec: np.ndarray | None = None
        hyde_slice = slices.get("__hyde__")
        if hyde_slice is not None:
            hyde_vec = _weighted_embedding_mean(q_embs[hyde_slice], decay=aggregation_decay)
            if base_vec is None:
                use_hyde = True
            else:
                sim_hyde = cosine(base_vec, cast(np.ndarray, hyde_vec))
                use_hyde = (not settings.drift_filter_enabled) or (
                    sim_hyde >= settings.hyde_drift_sim_threshold
                )

        await session.log(
            f"[LOG] Chat: fusion queries={len(query_texts)} hyde={'on' if use_hyde else 'off'}"
        )

        # Retrieve per query, then fuse with RRF (robust to score calibration).
        await session.log("[LOG] Chat: retrieval (multi-query + RRF fusion)...")
        rankings: list[list[str]] = []
        id_to_chunk: dict[str, ChunkModel] = {}
        retrieval_jobs: list[tuple[str, np.ndarray, str | None, bool]] = []
        for q in query_texts:
            v = query_vecs.get(q)
            if v is None:
                continue
            retrieval_jobs.append((q, v, q, True))

        if use_hyde and hyde_vec is not None:
            # HyDE is retrieval-only dense expansion. Avoid duplicate BM25 pass.
            retrieval_jobs.append((base_query, hyde_vec, None, False))

        retrieval_parallelism = max(1, int(settings.retrieval_parallelism))
        sem = asyncio.Semaphore(retrieval_parallelism)

        async def _run_retrieval(
            query_text: str,
            emb: np.ndarray,
            expanded: str | None,
            bm25_enabled: bool,
        ) -> tuple[list[str], dict[str, ChunkModel]]:
            async with sem:
                scored_local = await _search_retriever_async(
                    query=query_text,
                    query_embedding=emb,
                    expanded_query=expanded,
                    top_k=settings.fusion_per_query_top_k,
                    bm25_enabled=bm25_enabled,
                    metrics=metrics,
                )
            ranking_ids_local: list[str] = []
            id_map_local: dict[str, ChunkModel] = {}
            for s in scored_local:
                cid = s.chunk.id
                ranking_ids_local.append(cid)
                id_map_local[cid] = s.chunk
            return ranking_ids_local, id_map_local

        if retrieval_jobs:
            retrieval_results = await asyncio.gather(
                *[
                    _run_retrieval(q, emb, expanded, bm25_enabled)
                    for q, emb, expanded, bm25_enabled in retrieval_jobs
                ]
            )
            for ranking_ids, local_map in retrieval_results:
                if ranking_ids:
                    rankings.append(ranking_ids)
                id_to_chunk.update(local_map)

        fused_ids = rrf_fuse(
            rankings, k=settings.rrf_k, max_results=settings.fusion_max_candidates
        )
        metrics.add_step(
            "rrf_fusion",
            data={
                "input_rankings_count": len(rankings),
                "fused_top20": fused_ids[:20],
                "k": settings.rrf_k,
                "max_candidates": settings.fusion_max_candidates,
            },
        )
        candidate_chunks = [id_to_chunk[cid] for cid in fused_ids if cid in id_to_chunk]

        # Fall back to a single retrieval if fusion failed unexpectedly.
        if not candidate_chunks:
            scored = await _search_retriever_async(
                query=base_query,
                query_embedding=base_vec if base_vec is not None else q_embs[0],
                expanded_query=base_query,
                top_k=max(req.top_k, 1),
                metrics=metrics,
            )
            candidate_chunks = [s.chunk for s in scored]

        if not settings.llm_rerank_enabled:
            metrics.add_step("llm_rerank", skipped=True, reason="disabled")
        elif candidate_chunks:
            pool_n = max(1, min(settings.llm_rerank_candidate_pool, len(candidate_chunks)))
            pool = candidate_chunks[:pool_n]
            passages = [(c.id, c.content) for c in pool]

            await session.log(f"[LOG] Chat: LLM rerank pool={pool_n}...")
            try:
                ranked_ids = await openrouter.rerank_passages_yesno(
                    query=base_query,
                    passages=passages,
                    doc_language=str(doc_language),
                    model=settings.llm_rerank_model or None,
                    max_chars=settings.llm_rerank_max_chars,
                )
                candidate_ids = {c.id for c in candidate_chunks}
                metrics.add_step(
                    "llm_rerank",
                    data={
                        "pool_size": pool_n,
                        "ranked_ids": ranked_ids[:10],
                        "filtered": [cid for cid in ranked_ids if cid not in candidate_ids],
                    },
                )
            except OpenRouterError as e:
                await session.log(f"[LOG] WARNING: rerank failed: {e}")
                metrics.add_step("llm_rerank", skipped=True, reason="api_error")
            else:
                id_to_chunk_all = {c.id: c for c in candidate_chunks}
                ordered: list[ChunkModel] = []
                seen: set[str] = set()
                for cid in ranked_ids:
                    ch = id_to_chunk_all.get(cid)
                    if ch is None or cid in seen:
                        continue
                    seen.add(cid)
                    ordered.append(ch)
                for ch in candidate_chunks:
                    if ch.id in seen:
                        continue
                    ordered.append(ch)
                candidate_chunks = ordered
        elif not candidate_chunks:
            metrics.add_step("llm_rerank", skipped=True, reason="no_candidates")

        # Final selection for answer context.
        retrieved_chunks = candidate_chunks[: req.top_k]

    # Re-pack for both normal/fast mode according to strategy.
    repack_strategy = (settings.repack_strategy or "reverse").strip().lower()
    if repack_strategy in {"forward", "none", "off", "disabled", "disable"}:
        await session.log(f"[LOG] Chat: re-pack strategy '{repack_strategy}' -> keeping order.")
    elif repack_strategy == "reverse":
        await session.log("[LOG] Chat: re-pack strategy 'reverse' -> reversing order.")
    else:
        await session.log(
            f"[LOG] WARNING: unknown ERR_REPACK_STRATEGY='{repack_strategy}', defaulting to 'reverse'."
        )
        repack_strategy = "reverse"

    retrieved_chunks = apply_repack_strategy(retrieved_chunks, repack_strategy=repack_strategy)
    metrics.add_step(
        "repack",
        data={
            "strategy": repack_strategy,
            "mode": "fast" if req.fast_mode else "normal",
            "context_count": len(retrieved_chunks),
        },
    )

    # Add final context with previews (no score post-repack).
    final_chunks_data = []
    for i, chunk in enumerate(retrieved_chunks):
        if len(chunk.content) > 200:
            preview = f"{chunk.content[:197]}..."
        else:
            preview = chunk.content
        final_chunks_data.append(
            {
                "chunk_id": chunk.id,
                "rank": i + 1,
                "score": 0.0,
                "preview": preview,
            }
        )
    metrics.add_step("final_context", data={"chunks": final_chunks_data})

    context_blocks = _build_context_blocks(chunks=retrieved_chunks, include_neighbors=True)
    context_text = "\n\n".join(context_blocks)

    system_prompt = (
        "You are a strict RAG QA engine.\n"
        "Rules:\n"
        "1) You MUST answer using ONLY the provided document excerpts in CONTEXT.\n"
        '2) If the answer cannot be found in CONTEXT, reply exactly: "The document does not mention this."\n'
        "3) When you use information from an excerpt, cite it with stacked citations like [1][2].\n"
        "4) Do not use any outside knowledge. Do not guess.\n"
    )

    async with session.lock:
        history_text = "\n".join([f"{t.role}: {t.content}" for t in session.chat_history])

    prompt_tokens = _estimate_prompt_tokens(
        text_parts=[system_prompt, history_text, context_text, user_query]
    )
    if prompt_tokens > settings.chat_model_context_limit_tokens:
        await session.log("[LOG] Chat: token limit reached -> refusing request")
        raise HTTPException(
            status_code=400,
            detail="Session limit reached. Please export and refresh.",
        )

    messages: list[ChatMessage] = [ChatMessage(role="system", content=system_prompt)]
    if history_text:
        messages.append(ChatMessage(role="assistant", content=f"CHAT_HISTORY:\n{history_text}"))
    messages.append(ChatMessage(role="assistant", content=f"CONTEXT:\n{context_text}"))
    messages.append(ChatMessage(role="user", content=user_query))

    await session.log("[LOG] Chat: generating answer (strict RAG)...")
    try:
        answer = await openrouter.chat_completion(
            model=settings.chat_model_simple,
            messages=messages,
            temperature=0.0,
        )
    except OpenRouterError as e:
        raise HTTPException(status_code=502, detail=f"OpenRouter chat error: {e}") from e

    # Guardrails beyond prompting:
    # - require citations for any non-fallback answer
    # - citations must be in range
    # - on failure, retry once (common failure mode: missing/invalid citations)
    gr = enforce_strict_rag_answer(
        answer=answer,
        context_size=len(retrieved_chunks),
        require_citations=True,
    )
    if not gr.ok:
        await session.log(f"[LOG] Guardrails triggered: {gr.reason} -> retrying once")
        retry_user_prompt = (
            "Your previous answer was rejected because it did not follow the required citation rules.\n"
            "Re-answer the user's question using ONLY CONTEXT.\n\n"
            "Output MUST be exactly one of:\n"
            f'- "{STRICT_NO_MENTION}" (if the answer is not in CONTEXT)\n'
            "- OR an answer that includes stacked citations like [1][2], where each n is between "
            f"1 and {len(retrieved_chunks)}.\n\n"
            "Do not add any extra commentary.\n"
            f"Rejection reason: {gr.reason}\n"
        )
        retry_messages = list(messages)
        retry_messages.append(
            ChatMessage(role="assistant", content=f"Previous (invalid) answer:\n{answer}")
        )
        retry_messages.append(ChatMessage(role="user", content=retry_user_prompt))
        try:
            answer2 = await openrouter.chat_completion(
                model=settings.chat_model_simple,
                messages=retry_messages,
                temperature=0.0,
            )
        except OpenRouterError as e:
            await session.log(f"[LOG] Chat retry failed: {e} -> forcing fallback")
            answer = STRICT_NO_MENTION
        else:
            gr2 = enforce_strict_rag_answer(
                answer=answer2,
                context_size=len(retrieved_chunks),
                require_citations=True,
            )
            if not gr2.ok:
                await session.log(
                    f"[LOG] Guardrails retry still failed: {gr2.reason} -> forcing fallback"
                )
                answer = STRICT_NO_MENTION
            else:
                answer = gr2.answer
    else:
        answer = gr.answer

    # IMPORTANT for frontend:
    # - The model cites [1]..[K] based on the CONTEXT numbering.
    # - Therefore the API must return `citations` aligned to that same numbering.
    citations_payload: list[dict] = [c.model_dump() for c in retrieved_chunks]

    cited_nums = _extract_citation_numbers(answer)
    cited_models: list[ChunkModel] = []
    for n in cited_nums:
        idx = n - 1
        if 0 <= idx < len(retrieved_chunks):
            cited_models.append(retrieved_chunks[idx])

    async with session.lock:
        session.chat_history.append(ChatTurn(role="user", content=user_query))
        session.chat_history.append(
            ChatTurn(role="assistant", content=answer, citations=retrieved_chunks)
        )
        session.register_references(cited_models)
        session.latest_evaluation = metrics.to_record()

    await session.log("[LOG] Chat: done.")
    return ChatResponse(answer=answer, citations=citations_payload)
