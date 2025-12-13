from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from starlette.responses import Response

from .config import Settings, load_settings
from .guardrails import STRICT_NO_MENTION, enforce_strict_rag_answer
from .ingestion.chunker import Chunker
from .ingestion.chunker import estimate_tokens
from .ingestion.file_parser import FileParser
from .openrouter_client import OpenRouterClient, OpenRouterError
from .openrouter_client import ChatMessage
from .retrieval.fusion import dedupe_keep_order, rrf_fuse
from .retrieval.hybrid_retriever import HybridRetriever
from .session_store import ChatTurn, cleanup_expired_sessions, get_or_create_session, get_session


async def _cleanup_loop(settings: Settings, shutdown_event: asyncio.Event) -> None:
    while not shutdown_event.is_set():
        cleanup_expired_sessions()
        try:
            await asyncio.wait_for(
                shutdown_event.wait(), timeout=settings.session_cleanup_interval_seconds
            )
        except TimeoutError:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    app.state.settings = settings
    app.state.openrouter = OpenRouterClient(settings)
    shutdown_event = asyncio.Event()
    app.state.shutdown_event = shutdown_event
    cleanup_task = asyncio.create_task(_cleanup_loop(settings, shutdown_event))
    try:
        yield
    finally:
        shutdown_event.set()
        cleanup_task.cancel()
        await app.state.openrouter.aclose()


app = FastAPI(title="ERR Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_settings() -> Settings:
    return app.state.settings


def get_openrouter() -> OpenRouterClient:
    return app.state.openrouter


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def _ingest_file(
    *,
    session_id: str,
    filename: str,
    content: bytes,
    settings: Settings,
    openrouter: OpenRouterClient,
) -> None:
    session = get_session(session_id=session_id, ttl_seconds=settings.session_ttl_seconds)
    if session is None:
        return

    async with session.lock:
        session.ingest_status = "processing"
        session.ingest_error = None
        session.filename = filename
        session.chunks = []
        session.retriever = None
        session.chat_history = []
        session.reference_ids = {}
        session.references = []

    await session.log(f"[LOG] Received file: {filename}")
    await session.log("[LOG] Parsing document...")

    parser = FileParser()
    try:
        blocks = parser.parse(filename=filename, content=content)
    except Exception as e:  # noqa: BLE001
        async with session.lock:
            session.ingest_status = "error"
            session.ingest_error = str(e)
        await session.log(f"[LOG] ERROR parsing: {e}")
        return

    await session.log(f"[LOG] Extracted {len(blocks)} blocks")
    await session.log("[LOG] Chunking into ~500-token chunks...")

    chunker = Chunker(target_tokens=500)
    chunks = chunker.chunk(blocks=blocks)
    await session.log(f"[LOG] Created {len(chunks)} chunks")
    if not chunks:
        async with session.lock:
            session.ingest_status = "error"
            session.ingest_error = "No chunks created from document"
        await session.log("[LOG] ERROR: No chunks created from document")
        return

    # Embed chunks in batches.
    await session.log("[LOG] Building vector embeddings (batched)...")
    batch_size = 32
    embeddings_list: list[list[float]] = []
    detected_embedding_dim: int | None = None
    total_batches = (len(chunks) + batch_size - 1) // batch_size

    for b in range(total_batches):
        start = b * batch_size
        end = min(len(chunks), (b + 1) * batch_size)
        await session.log(f"[LOG] Embedding batch {b+1}/{total_batches} ({start}-{end})...")
        texts = [c.content for c in chunks[start:end]]
        try:
            embs = await openrouter.embeddings(model=settings.embedding_model, inputs=texts)
        except OpenRouterError as e:
            async with session.lock:
                session.ingest_status = "error"
                session.ingest_error = str(e)
            await session.log(f"[LOG] ERROR embedding: {e}")
            return

        if embs.ndim != 2 or embs.shape[0] != len(texts):
            async with session.lock:
                session.ingest_status = "error"
                session.ingest_error = f"Unexpected embeddings shape: {tuple(embs.shape)}"
            await session.log(f"[LOG] ERROR embedding: Unexpected embeddings shape {tuple(embs.shape)}")
            return

        batch_dim = int(embs.shape[1])
        if detected_embedding_dim is None:
            detected_embedding_dim = batch_dim
            await session.log(f"[LOG] Detected embedding dim: {detected_embedding_dim}")
        elif batch_dim != detected_embedding_dim:
            async with session.lock:
                session.ingest_status = "error"
                session.ingest_error = (
                    f"Inconsistent embedding dim across batches: "
                    f"expected {detected_embedding_dim}, got {batch_dim}"
                )
            await session.log(
                "[LOG] ERROR embedding: Inconsistent embedding dim across batches "
                f"(expected {detected_embedding_dim}, got {batch_dim})"
            )
            return
        embeddings_list.extend(embs.tolist())

    embeddings = embeddings_list
    await session.log("[LOG] Building FAISS + BM25 indexes in memory...")

    if detected_embedding_dim is None:
        async with session.lock:
            session.ingest_status = "error"
            session.ingest_error = "Could not determine embedding dimension"
        await session.log("[LOG] ERROR: Could not determine embedding dimension")
        return

    if settings.embedding_dim and settings.embedding_dim != detected_embedding_dim:
        await session.log(
            "[LOG] WARNING: OPENROUTER_EMBEDDING_DIM="
            f"{settings.embedding_dim} but model returned {detected_embedding_dim}; "
            f"using {detected_embedding_dim}"
        )

    retriever = HybridRetriever(
        embedding_dim=detected_embedding_dim,
        vector_weight=0.8,
        bm25_weight=0.2,
        candidate_k=100,
    )
    try:
        import numpy as np

        retriever.build(chunks=chunks, embeddings=np.asarray(embeddings, dtype=np.float32))
    except Exception as e:  # noqa: BLE001
        async with session.lock:
            session.ingest_status = "error"
            session.ingest_error = str(e)
        await session.log(f"[LOG] ERROR building indexes: {e}")
        return

    async with session.lock:
        session.chunks = chunks
        session.retriever = retriever
        session.doc_language = retriever.doc_language
        session.ingest_status = "ready"

    await session.log("[LOG] Ready.")


@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
    settings: Settings = Depends(get_settings),
    openrouter: OpenRouterClient = Depends(get_openrouter),
) -> dict[str, str]:
    session_id = (x_session_id or "").strip() or uuid4().hex
    session = get_or_create_session(session_id=session_id, ttl_seconds=settings.session_ttl_seconds)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    await session.log("[LOG] Upload accepted; starting background ingestion...")
    asyncio.create_task(
        _ingest_file(
            session_id=session_id,
            filename=file.filename or "upload",
            content=content,
            settings=settings,
            openrouter=openrouter,
        )
    )

    return {"session_id": session_id, "status": "processing"}


@app.get("/api/logs/{session_id}")
async def logs(
    session_id: str,
    settings: Settings = Depends(get_settings),
) -> EventSourceResponse:
    session = get_session(session_id=session_id, ttl_seconds=settings.session_ttl_seconds)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session")

    async def event_generator():
        # Replay recent history first.
        history = list(session.log_history)
        last_seq = 0
        for seq, line in history:
            last_seq = max(last_seq, seq)
            yield {"event": "log", "data": line.rstrip("\n")}

        # Then stream new events.
        while True:
            try:
                await asyncio.wait_for(session.log_event.wait(), timeout=15.0)
                session.log_event.clear()

                history = list(session.log_history)
                # If we missed too much and the deque rotated, just replay everything we still have.
                earliest_seq = history[0][0] if history else 0
                if earliest_seq and earliest_seq > last_seq:
                    last_seq = earliest_seq - 1

                for seq, line in history:
                    if seq <= last_seq:
                        continue
                    last_seq = seq
                    yield {"event": "log", "data": line.rstrip("\n")}
            except TimeoutError:
                # heartbeat to keep connection alive
                yield {"event": "ping", "data": "keepalive"}

    return EventSourceResponse(event_generator())


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Ephemeral session id")
    message: str = Field(..., description="User query")
    top_k: int = Field(default=5, ge=1, le=10)


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


def _build_embedding_query_inputs(*, settings: Settings, queries: list[str]) -> list[str]:
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
                inputs.append(f"Instruct: {task}\nQuery:{q}")

    if settings.embedding_query_include_raw or not inputs:
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


@app.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    settings: Settings = Depends(get_settings),
    openrouter: OpenRouterClient = Depends(get_openrouter),
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

    await session.log("[LOG] Chat: translating query for keyword alignment...")
    try:
        expanded_query = await openrouter.translate_query_for_doc_language(
            query=user_query, doc_language=str(doc_language)
        )
    except OpenRouterError as e:
        raise HTTPException(status_code=502, detail=f"OpenRouter translate error: {e}") from e

    base_query = (expanded_query or "").strip() or user_query

    query_texts: list[str] = [base_query]
    hyde_text: str = ""
    if settings.query_fusion_enabled:
        await session.log("[LOG] Chat: generating query variants (multi-query)...")
        try:
            variants = await openrouter.generate_query_variants(
                query=base_query,
                doc_language=str(doc_language),
                n=settings.query_variants_count,
            )
        except OpenRouterError as e:
            await session.log(f"[LOG] WARNING: query variants failed: {e}")
            variants = []

        # Keep the raw query too (useful for cross-lingual names / phrasing).
        query_texts = dedupe_keep_order([base_query, user_query] + variants)

        if settings.hyde_enabled:
            await session.log("[LOG] Chat: generating HyDE passage (retrieval-only)...")
            try:
                hyde_text = await openrouter.generate_hyde_passage(
                    query=base_query,
                    doc_language=str(doc_language),
                    max_words=settings.hyde_max_words,
                )
            except OpenRouterError as e:
                await session.log(f"[LOG] WARNING: HyDE generation failed: {e}")
                hyde_text = ""
    else:
        query_texts = dedupe_keep_order([base_query, user_query])

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

    import numpy as np

    def cosine(a: np.ndarray, b: np.ndarray) -> float:
        aa = np.asarray(a, dtype=np.float32).reshape(-1)
        bb = np.asarray(b, dtype=np.float32).reshape(-1)
        denom = float(np.linalg.norm(aa) * np.linalg.norm(bb))
        if denom < 1e-12:
            return 0.0
        return float(np.dot(aa, bb) / denom)

    query_vecs: dict[str, np.ndarray] = {}
    for q, sl in slices.items():
        if q == "__hyde__":
            continue
        vec = np.mean(q_embs[sl], axis=0, dtype=np.float32)
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
        hyde_vec = np.mean(q_embs[hyde_slice], axis=0, dtype=np.float32)
        if base_vec is None:
            use_hyde = True
        else:
            sim_hyde = cosine(base_vec, hyde_vec)
            use_hyde = (not settings.drift_filter_enabled) or (
                sim_hyde >= settings.hyde_drift_sim_threshold
            )

    await session.log(
        f"[LOG] Chat: fusion queries={len(query_texts)} hyde={'on' if use_hyde else 'off'}"
    )

    # Retrieve per query, then fuse with RRF (robust to score calibration).
    await session.log("[LOG] Chat: retrieval (multi-query + RRF fusion)...")
    rankings: list[list[str]] = []
    id_to_chunk: dict[str, object] = {}

    for q in query_texts:
        v = query_vecs.get(q)
        if v is None:
            continue
        scored = retriever.search(
            query=q,
            query_embedding=v,
            expanded_query=q,
            top_k=settings.fusion_per_query_top_k,
        )
        ranking_ids: list[str] = []
        for s in scored:
            cid = s.chunk.id
            ranking_ids.append(cid)
            id_to_chunk[cid] = s.chunk
        if ranking_ids:
            rankings.append(ranking_ids)

    if use_hyde and hyde_vec is not None:
        scored = retriever.search(
            query=base_query,
            query_embedding=hyde_vec,
            expanded_query=base_query,
            top_k=settings.fusion_per_query_top_k,
        )
        ranking_ids = []
        for s in scored:
            cid = s.chunk.id
            ranking_ids.append(cid)
            id_to_chunk[cid] = s.chunk
        if ranking_ids:
            rankings.append(ranking_ids)

    fused_ids = rrf_fuse(rankings, k=settings.rrf_k, max_results=settings.fusion_max_candidates)
    candidate_chunks = [id_to_chunk[cid] for cid in fused_ids if cid in id_to_chunk]

    # Fall back to a single retrieval if fusion failed unexpectedly.
    if not candidate_chunks:
        scored = retriever.search(
            query=base_query,
            query_embedding=base_vec if base_vec is not None else q_embs[0],
            expanded_query=base_query,
            top_k=max(req.top_k, 1),
        )
        candidate_chunks = [s.chunk for s in scored]

    if settings.llm_rerank_enabled and candidate_chunks:
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
        except OpenRouterError as e:
            await session.log(f"[LOG] WARNING: rerank failed: {e}")
        else:
            id_to_chunk_all = {c.id: c for c in candidate_chunks}
            ordered: list = []
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

    # Final selection for answer context.
    retrieved_chunks = candidate_chunks[: req.top_k]
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
            model=settings.chat_model,
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
                model=settings.chat_model,
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
    cited_models = []
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

    await session.log("[LOG] Chat: done.")
    return ChatResponse(answer=answer, citations=citations_payload)


def _rewrite_local_citations_to_global(
    *, answer: str, local_citations: list[dict], global_map: dict[str, int]
) -> str:
    """
    Convert local [n] citations (index into local_citations) into stable global references.
    local_citations are dicts with at least {"id": "..."}.
    """
    import re

    def repl(m: re.Match[str]) -> str:
        raw = m.group(1)
        try:
            n = int(raw)
        except ValueError:
            return m.group(0)
        idx = n - 1
        if idx < 0 or idx >= len(local_citations):
            return m.group(0)
        cid = local_citations[idx].get("id")
        if not isinstance(cid, str):
            return m.group(0)
        g = global_map.get(cid)
        if g is None:
            return m.group(0)
        return f"[{g}]"

    return re.sub(r"\[(\d+)\]", repl, answer)


@app.get("/export/{session_id}")
async def export_markdown(
    session_id: str,
    settings: Settings = Depends(get_settings),
) -> Response:
    session = get_session(session_id=session_id, ttl_seconds=settings.session_ttl_seconds)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session")

    await session.log("[LOG] Export: generating markdown...")

    async with session.lock:
        turns = list(session.chat_history)
        refs = list(session.references)
        ref_map = dict(session.reference_ids)
        filename = session.filename or "document"

    # Build transcript. For assistant turns we rewrite local numbering to global numbering
    # so the Appendix indices match the citations users see in the exported markdown.
    lines: list[str] = []
    lines.append(f"# ERR Export — {filename}")
    lines.append("")
    lines.append("## Chat History")
    lines.append("")

    for t in turns:
        if t.role == "user":
            lines.append("### User")
            lines.append(t.content.strip())
            lines.append("")
            continue

        if t.role == "assistant":
            lines.append("### Assistant")
            local_citations = [c.model_dump() for c in t.citations]
            rewritten = _rewrite_local_citations_to_global(
                answer=t.content, local_citations=local_citations, global_map=ref_map
            )
            lines.append(rewritten.strip())
            lines.append("")
            continue

        # fallback
        lines.append(f"### {t.role}")
        lines.append(t.content.strip())
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Appendix — Referenced Chunks")
    lines.append("")

    if not refs:
        lines.append("_No references were used in this session._")
        lines.append("")
    else:
        for i, ch in enumerate(refs, start=1):
            lines.append(f"> **Reference [{i}]**")
            lines.append(">")
            for ln in ch.content.strip().splitlines():
                lines.append(f"> {ln}")
            lines.append("")

    md = "\n".join(lines).strip() + "\n"
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in filename)[:40]
    return Response(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="err_export_{safe_name}.md"'},
    )
