from __future__ import annotations

import asyncio

from .config import Settings
from .ingestion.chunker import Chunker
from .ingestion.file_parser import FileParser
from .openrouter_client import OpenRouterClient
from .retrieval.hybrid_retriever import HybridRetriever
from .session_store import get_session


async def ingest_file(
    *,
    session_id: str,
    filename: str,
    content: bytes,
    settings: Settings,
    openrouter: OpenRouterClient,
    ingest_generation: int | None = None,
) -> None:
    session = get_session(session_id=session_id, ttl_seconds=settings.session_ttl_seconds)
    if session is None:
        return

    async with session.lock:
        if ingest_generation is not None and ingest_generation != session.ingest_generation:
            return
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
    loop = asyncio.get_running_loop()
    try:
        blocks = await loop.run_in_executor(None, lambda: parser.parse(filename=filename, content=content))
    except Exception as e:  # noqa: BLE001
        async with session.lock:
            if ingest_generation is not None and ingest_generation != session.ingest_generation:
                return
            session.ingest_status = "error"
            session.ingest_error = str(e)
        await session.log(f"[LOG] ERROR parsing: {e}")
        return

    await session.log(f"[LOG] Extracted {len(blocks)} blocks")
    await session.log(
        "[LOG] Chunking into "
        f"~{settings.chunk_target_tokens}-token chunks "
        f"(overlap={settings.chunk_overlap_tokens}, "
        f"semantic={settings.semantic_chunking_enabled}, "
        f"threshold={settings.semantic_chunking_threshold})..."
    )

    chunker = Chunker(
        target_tokens=settings.chunk_target_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
        semantic_enabled=settings.semantic_chunking_enabled,
        semantic_threshold=settings.semantic_chunking_threshold,
        semantic_max_sentences=settings.semantic_chunking_max_sentences,
    )

    try:
        chunks = await loop.run_in_executor(None, lambda: chunker.chunk(blocks=blocks))
    except Exception as e:  # noqa: BLE001
        async with session.lock:
            if ingest_generation is not None and ingest_generation != session.ingest_generation:
                return
            session.ingest_status = "error"
            session.ingest_error = str(e)
        await session.log(f"[LOG] ERROR chunking: {e}")
        return

    await session.log(f"[LOG] Created {len(chunks)} chunks")
    if not chunks:
        async with session.lock:
            if ingest_generation is not None and ingest_generation != session.ingest_generation:
                return
            session.ingest_status = "error"
            session.ingest_error = "No chunks created from document"
        await session.log("[LOG] ERROR: No chunks created from document")
        return

    # Embed chunks in bounded concurrent batches and write directly into a
    # contiguous float32 matrix to avoid large transient Python lists.
    await session.log("[LOG] Building vector embeddings (batched)...")
    import numpy as np

    batch_size = 32
    max_inflight_batches = 8
    detected_embedding_dim: int | None = None
    embeddings_matrix: np.ndarray | None = None
    total_batches = (len(chunks) + batch_size - 1) // batch_size
    semaphore = asyncio.Semaphore(max_inflight_batches)

    async def _process_batch(b_idx: int):
        async with semaphore:
            start = b_idx * batch_size
            end = min(len(chunks), (b_idx + 1) * batch_size)
            await session.log(f"[LOG] Embedding batch {b_idx + 1}/{total_batches} ({start}-{end})...")
            texts = [c.content for c in chunks[start:end]]
            try:
                embs = await openrouter.embeddings(model=settings.embedding_model, inputs=texts)
            except Exception as e:  # noqa: BLE001
                return b_idx, start, None, str(e)

            if embs.ndim != 2 or embs.shape[0] != len(texts):
                return b_idx, start, None, f"Unexpected embeddings shape: {tuple(embs.shape)}"

            return b_idx, start, embs, None

    # NOTE on concurrency safety: asyncio.as_completed yields results out of
    # order, but writes to embeddings_matrix[start:end] are safe because each
    # batch owns a non-overlapping slice.  The shared `detected_embedding_dim`
    # and `embeddings_matrix` variables are only mutated inside `await` points
    # in the single-threaded asyncio event loop, so no lock is needed.
    tasks = [asyncio.create_task(_process_batch(b_idx)) for b_idx in range(total_batches)]
    try:
        for completed in asyncio.as_completed(tasks):
            b_idx, start, embs, err = await completed
            if err:
                pending = [t for t in tasks if not t.done()]
                for pending_task in pending:
                    pending_task.cancel()
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)
                async with session.lock:
                    if ingest_generation is not None and ingest_generation != session.ingest_generation:
                        return
                    session.ingest_status = "error"
                    session.ingest_error = err
                await session.log(f"[LOG] ERROR embedding batch {b_idx + 1}: {err}")
                return

            batch_dim = int(embs.shape[1])
            if detected_embedding_dim is None:
                detected_embedding_dim = batch_dim
                embeddings_matrix = np.empty((len(chunks), detected_embedding_dim), dtype=np.float32)
                await session.log(f"[LOG] Detected embedding dim: {detected_embedding_dim}")
            elif batch_dim != detected_embedding_dim:
                async with session.lock:
                    if ingest_generation is not None and ingest_generation != session.ingest_generation:
                        return
                    session.ingest_status = "error"
                    session.ingest_error = (
                        f"Inconsistent embedding dim across batches: expected {detected_embedding_dim}, got {batch_dim}"
                    )
                await session.log(
                    "[LOG] ERROR embedding: Inconsistent embedding dim across batches "
                    f"(expected {detected_embedding_dim}, got {batch_dim})"
                )
                return

            assert embeddings_matrix is not None
            end = start + embs.shape[0]
            embeddings_matrix[start:end, :] = embs
    finally:
        pending = [t for t in tasks if not t.done()]
        for pending_task in pending:
            pending_task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    await session.log("[LOG] Building FAISS + BM25 indexes in memory...")

    if detected_embedding_dim is None or embeddings_matrix is None:
        async with session.lock:
            if ingest_generation is not None and ingest_generation != session.ingest_generation:
                return
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
        candidate_k=max(1, int(settings.retriever_candidate_k)),
    )
    try:
        await loop.run_in_executor(
            None,
            lambda: retriever.build(chunks=chunks, embeddings=embeddings_matrix),
        )
    except Exception as e:  # noqa: BLE001
        async with session.lock:
            if ingest_generation is not None and ingest_generation != session.ingest_generation:
                return
            session.ingest_status = "error"
            session.ingest_error = str(e)
        await session.log(f"[LOG] ERROR building indexes: {e}")
        return

    fast_dim = int(settings.embedding_dim_fast_mode)
    if 0 < fast_dim < detected_embedding_dim:
        await session.log(f"[LOG] Pre-warming fast-mode MRL index (dim={fast_dim})...")
        try:
            await loop.run_in_executor(None, lambda: retriever.warmup_mrl(fast_dim))
        except Exception as e:  # noqa: BLE001
            await session.log(f"[LOG] WARNING: MRL pre-warm failed ({e}); continuing.")

    stale = False
    async with session.lock:
        if ingest_generation is not None and ingest_generation != session.ingest_generation:
            stale = True
        else:
            session.chunks = chunks
            session.retriever = retriever
            session.doc_language = retriever.doc_language
            session.ingest_status = "ready"
    if stale:
        await session.log("[LOG] Stale ingestion task finished; discarded.")
        return

    await session.log("[LOG] Ready.")
