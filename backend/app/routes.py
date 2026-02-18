from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from sse_starlette.sse import EventSourceResponse
from starlette.responses import Response

from .chat_pipeline import ChatRequest, ChatResponse, run_chat
from .config import Settings
from .deps import get_openrouter, get_settings
from .ingestion_pipeline import ingest_file
from .openrouter_client import OpenRouterClient
from .retrieval.evaluation import EvaluationRecord
from .session_store import get_or_create_session, get_session

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/upload")
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
        ingest_file(
            session_id=session_id,
            filename=file.filename or "upload",
            content=content,
            settings=settings,
            openrouter=openrouter,
        )
    )

    return {"session_id": session_id, "status": "processing"}


@router.get("/api/logs/{session_id}")
async def logs(
    session_id: str,
    settings: Settings = Depends(get_settings),
) -> EventSourceResponse:
    # Use get_or_create to handle race condition where SSE connects before upload completes
    session = get_or_create_session(session_id=session_id, ttl_seconds=settings.session_ttl_seconds)

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

    return EventSourceResponse(
        event_generator(),
        headers={
            # Be explicit about SSE no-buffer semantics (helps through proxies).
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Harmless for non-nginx proxies; critical if an nginx-like buffer is in the path.
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    settings: Settings = Depends(get_settings),
    openrouter: OpenRouterClient = Depends(get_openrouter),
) -> ChatResponse:
    return await run_chat(req=req, settings=settings, openrouter=openrouter)


@router.get("/evaluation", response_model=EvaluationRecord)
async def get_evaluation(
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
    settings: Settings = Depends(get_settings),
):
    session_id = (x_session_id or "").strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing X-Session-Id header.")
    session = get_session(session_id=session_id, ttl_seconds=settings.session_ttl_seconds)
    if session is None or session.latest_evaluation is None:
        raise HTTPException(status_code=404, detail="No evaluation record found for this session.")
    return session.latest_evaluation


@router.post("/clear/{session_id}")
async def clear_chat(
    session_id: str,
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    session = get_session(session_id=session_id, ttl_seconds=settings.session_ttl_seconds)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session")
    await session.clear_chat_data()
    return {"status": "cleared"}

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


@router.get("/export/{session_id}")
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
