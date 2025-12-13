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

    # Embed chunks in batches.
    await session.log("[LOG] Building vector embeddings (batched)...")
    batch_size = 32
    embeddings_list: list[list[float]] = []
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
        embeddings_list.extend(embs.tolist())

    embeddings = embeddings_list
    await session.log("[LOG] Building FAISS + BM25 indexes in memory...")

    retriever = HybridRetriever(
        embedding_dim=settings.embedding_dim,
        vector_weight=0.8,
        bm25_weight=0.2,
        candidate_k=50,
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

    await session.log("[LOG] Chat: embedding query...")
    try:
        q_embs = await openrouter.embeddings(model=settings.embedding_model, inputs=[user_query])
    except OpenRouterError as e:
        raise HTTPException(status_code=502, detail=f"OpenRouter embedding error: {e}") from e

    if q_embs.shape[0] != 1:
        raise HTTPException(status_code=500, detail="Unexpected embedding response shape")

    await session.log("[LOG] Chat: hybrid retrieval (FAISS + BM25)...")
    scored = retriever.search(
        query=user_query,
        query_embedding=q_embs[0],
        expanded_query=expanded_query,
        top_k=req.top_k,
    )

    retrieved_chunks = [s.chunk for s in scored]
    context_blocks = [f"[{i}] {ch.content}" for i, ch in enumerate(retrieved_chunks, start=1)]
    context_text = "\n\n".join(context_blocks)

    system_prompt = (
        "You are a strict RAG QA engine.\n"
        "Rules:\n"
        "1) You MUST answer using ONLY the provided document excerpts in CONTEXT.\n"
        '2) If the answer is not explicitly stated in CONTEXT, reply exactly: "The document does not mention this."\n'
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
    # - if citations are invalid, force strict fallback
    gr = enforce_strict_rag_answer(
        answer=answer,
        context_size=len(retrieved_chunks),
        require_citations=True,
    )
    if not gr.ok:
        await session.log(f"[LOG] Guardrails triggered: {gr.reason} -> forcing fallback")
        answer = STRICT_NO_MENTION
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
