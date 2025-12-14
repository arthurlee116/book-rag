# Copilot instructions (ERR — Ephemeral RAG Reader)

## Big picture (don’t break the privacy model)
- ERR is **ephemeral by design**: ingestion artifacts + chat state live **only in-memory** per session and are TTL-cleaned. Do not add persistence (DB/files) unless explicitly requested.
- Boundary: **Next.js frontend** calls **FastAPI backend** over HTTP using `NEXT_PUBLIC_BACKEND_URL` (see `frontend/lib/store.ts`). Don’t share runtime code across the boundary.

## Core request flow & where to look
- Upload: `POST /upload` (FastAPI in `backend/app/main.py`) → parse (`backend/app/ingestion/file_parser.py`) → chunk (`backend/app/ingestion/chunker.py`) → embeddings via OpenRouter (`backend/app/openrouter_client.py`) → build in-memory FAISS+BM25 (`backend/app/retrieval/hybrid_retriever.py`).
- Logs: ingestion progress is streamed via **SSE** `GET /api/logs/{session_id}` (see `backend/app/main.py`) and displayed in the UI.
- Chat: `POST /chat` runs retrieval pipeline (normal vs fast mode) then generates a **strict RAG** answer and post-validates with guardrails (`backend/app/guardrails.py`).

## Session semantics (important for correctness)
- Sessions are keyed by `X-Session-Id` header; backend creates one if missing (see `upload()` in `backend/app/main.py`).
- Session state (chunks, retriever, chat history, log buffer, locks) is in `backend/app/session_store.py`.
- Keep session operations concurrency-safe: most mutations are under `async with session.lock:`.

## Retrieval pipeline conventions
- Normal mode uses multi-query + optional HyDE + RRF fusion + optional LLM rerank; fast mode uses MRL truncation and skips expensive steps (see `chat()` in `backend/app/main.py`).
- Hybrid retrieval is **cosine via normalized inner product** (FAISS) + BM25 with per-query MinMax normalization; fusion is `final=0.8*vector+0.2*bm25` (see `HybridRetriever` in `backend/app/retrieval/hybrid_retriever.py`).
- Embedding inputs are often **instruction-aware** via `ERR_EMBEDDING_QUERY_INSTRUCTION_TEMPLATE` (see `_build_embedding_query_inputs()` in `backend/app/main.py` and settings in `backend/app/config.py`).

## Guardrails & citations (API contract)
- Allowed fallback is exactly: `The document does not mention this.` (`STRICT_NO_MENTION` in `backend/app/guardrails.py`).
- Any non-fallback answer must include stacked citations like `[1][2]`, where indices refer to the numbered context blocks built in `_build_context_blocks()` (`backend/app/main.py`).
- The `/chat` response must return `citations` aligned to that same `[1..K]` numbering.

## Export endpoint & stable references (markdown transcript)
- Export: `GET /export/{session_id}` returns a downloadable Markdown transcript (`text/markdown`) with a `Content-Disposition` attachment filename (see `export_markdown()` in `backend/app/main.py`).
- Why export needs extra logic: during chat, citations like `[1]..[K]` are **local indices into the current turn’s retrieved context blocks** (built by `_build_context_blocks()`), not stable identifiers.
- To make exports readable, assistant citations are rewritten from **local** numbering to **stable global reference numbers**:
	- Global numbering is assigned by first use of a chunk across the entire session.
	- The mapping is `chunk.id -> global_reference_number` and is stored on the session as:
		- `SessionState.reference_ids: dict[str, int]`
		- `SessionState.references: list[ChunkModel]`
		- (see `backend/app/session_store.py`, method `SessionState.register_references()`).
- Where the mapping gets populated:
	- After the model answers, `chat()` extracts the citation numbers from the final answer (`_extract_citation_numbers()` → `guardrails.extract_citation_numbers`).
	- The cited numbers select the corresponding chunks from `retrieved_chunks`.
	- Those cited chunks are registered into the session’s global references via `session.register_references(cited_models)`.
- How rewriting works in export:
	- For each assistant turn, export takes the per-turn citation payload (`local_citations = [c.model_dump() for c in t.citations]`).
	- `_rewrite_local_citations_to_global(answer, local_citations, global_map)` replaces occurrences of `[(\d+)]`:
		- It treats the number as **1-based index** into `local_citations`.
		- It looks up `local_citations[idx]["id"]` → then maps that chunk id through `global_map` (the session’s `reference_ids`).
		- It rewrites the bracket to the global number, e.g. local `[2]` might become global `[7]`.
- Export appendix: the file ends with “Appendix — Referenced Chunks”, listing `SessionState.references` in global order so citations match what users see.
- If you change anything about citation formatting (regex), context numbering, or what gets stored in `ChatTurn.citations`, you must review:
	- `backend/app/guardrails.py` citation extraction
	- `backend/app/main.py` `_build_context_blocks()`, `citations_payload`, and `_rewrite_local_citations_to_global()`
	- session reference tracking in `backend/app/session_store.py`

## Configuration & external dependencies
- Backend env is loaded from `backend/.env` by default, or `ENV_FILE=/path/to/.env` (see `load_settings()` in `backend/app/config.py`).
- Required: `OPENROUTER_API_KEY` (OpenRouter client fails fast otherwise; see `OpenRouterClient.__init__`).
- Optional toggles (read from env): `ERR_QUERY_FUSION_ENABLED`, `ERR_HYDE_ENABLED`, `ERR_LLM_RERANK_ENABLED`, `ERR_REPACK_STRATEGY`, `ERR_EMBEDDING_DIM_FAST_MODE`, etc. (see `backend/app/config.py`).

### Retrieval dependency expectations (runtime requirements)
Hybrid retrieval is implemented in `backend/app/retrieval/hybrid_retriever.py` and expects these libraries to be importable at runtime:
- `faiss-cpu` (**required**): used for vector search (`faiss.IndexFlatIP`) when building the index. If missing, `HybridRetriever.build()` raises a `RuntimeError` mentioning `faiss-cpu` and includes the captured `_FAISS_IMPORT_ERROR`.
- `rank-bm25` (**required**): used for BM25 (`from rank_bm25 import BM25Okapi`). If missing, import will fail at module import time.
- `spacy` (**required for English tokenization**): used when document language is detected as English (`Language="en"`). Note: this project uses `spacy.blank("en")`, so you do *not* need a separate downloadable model package just to tokenize.
- `jieba` (**required for Chinese tokenization**): used when document language is detected as Chinese (`Language="zh"`).

Language detection is a small heuristic in `detect_dominant_language()` (same file): if CJK characters are meaningfully present, the document is treated as `zh`, otherwise `en`. This choice affects BM25 tokenization and the stored `session.doc_language`.

### Where dependency failures surface
- Ingestion path (`POST /upload` background task `_ingest_file()`): failures typically show up when calling `retriever.build(...)` (FAISS/BM25 creation). The session is marked `ingest_status="error"` and the error is streamed to the UI via SSE logs.
- Chat path (`POST /chat`): if ingestion never reached `ready`, the endpoint responds `400` with `No active document. Upload and wait until Ready.`

## Developer workflows (repo defaults)
- Backend: install `backend/requirements.txt`, run `uvicorn backend.app.main:app --reload --port 8000`, tests via `python -m unittest discover -s backend/tests -p "test_*.py"`.
- Frontend: `npm install`, `npm run dev`, lint via `npm run lint`.

### Docker workflow (also supported)
- `docker compose up --build` runs frontend+backend together (see repo `README.md` and `docker-compose.yml`).
- When debugging backend issues under Docker, SSE logs (`GET /api/logs/{session_id}`) are usually the fastest visibility path because ingestion runs in a background task.

## Practical change guidance
- If you change request/response shapes or headers, update the frontend callers (e.g., upload sets `X-Session-Id` in `frontend/components/UploadPanel.tsx`) and add/update backend unit tests in `backend/tests/`.
- Avoid logging raw document text or user queries to disk; SSE logs are fine but keep them high-level.

### “Sharp edges” that commonly break features
- Citation numbering is *not* chunk IDs; it’s position in the per-turn `retrieved_chunks`. Keep this invariant unless you also update guardrails + export rewriting.
- `HybridRetriever.search()` supports MRL truncation via `search_dim` (fast mode). If you change embedding dimensions (`OPENROUTER_EMBEDDING_DIM`, `ERR_EMBEDDING_DIM_FAST_MODE`), ensure:
	- chunk embeddings are built with the same `embedding_dim` detected during ingestion, and
	- `search_dim` is `0 < search_dim < embedding_dim` (otherwise it falls back to full-dim behavior).
