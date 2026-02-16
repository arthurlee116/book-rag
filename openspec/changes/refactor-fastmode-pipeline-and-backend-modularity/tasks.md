## 1. Proposal Validation
- [ ] 1.1 Run `openspec validate refactor-fastmode-pipeline-and-backend-modularity --strict --no-interactive`

## 2. Backend Modularization (A07)
- [ ] 2.1 Create `backend/app/routes.py` and move HTTP route handlers from `main.py`
- [ ] 2.2 Create `backend/app/chat_pipeline.py` and move chat orchestration + helper functions
- [ ] 2.3 Create `backend/app/ingestion_pipeline.py` and move ingest orchestration logic
- [ ] 2.4 Keep `backend/app/main.py` as app lifecycle + CORS + route mount
- [ ] 2.5 Preserve existing API contracts and route paths

## 3. Retrieval Pipeline Performance Fixes (F02/F05/F06/A01/A02/A03)
- [ ] 3.1 Implement conditional language alignment: skip translation when query/doc language already aligned
- [ ] 3.2 Add vector-only retrieval mode and use it for HyDE branch to avoid repeated BM25
- [ ] 3.3 Add fast-mode candidate_k override config and pass it into retriever search
- [ ] 3.4 Replace fast-mode simple mean with weighted embedding aggregation prioritizing original query
- [ ] 3.5 Enable fast mode re-packing (follow configured strategy)
- [ ] 3.6 Build/cache MRL FAISS indexes and use FAISS for MRL search path

## 4. Robustness Fixes (F04/F08/A06)
- [ ] 4.1 Add chunking fail-safe in ingestion pipeline with explicit error status/logging
- [ ] 4.2 Fix JSON extraction regex escaping in OpenRouter client
- [ ] 4.3 Update embedding instruction template default to `Query: {query}` format

## 5. Indexing & Tokenization Upgrade (A04/A05)
- [ ] 5.1 Replace `rank-bm25` usage with `bm25s`
- [ ] 5.2 Introduce lightweight English tokenizer for BM25 path
- [ ] 5.3 Keep Chinese tokenizer path via jieba
- [ ] 5.4 Update Python dependencies/constraints accordingly

## 6. Tests & Validation
- [ ] 6.1 Update unit tests affected by module split (`main.py` helper imports / AST checks)
- [ ] 6.2 Add tests for conditional language alignment behavior
- [ ] 6.3 Add tests for HyDE vector-only retrieval path
- [ ] 6.4 Add tests for fast candidate_k override and fast re-pack behavior
- [ ] 6.5 Add tests for MRL FAISS index cache path
- [ ] 6.6 Run `python -m unittest discover -s backend/tests -p "test_*.py"`
- [ ] 6.7 Run `openspec validate refactor-fastmode-pipeline-and-backend-modularity --strict --no-interactive`

## 7. Delivery: Commit, Push, Deploy, Monitor
- [ ] 7.1 Commit with Conventional Commit message
- [ ] 7.2 Push changes to `main`
- [ ] 7.3 Deploy to production server (`docker compose -f docker-compose.prod.yml up -d --build`)
- [ ] 7.4 Verify health endpoints and service logs
- [ ] 7.5 Monitor post-deploy status for regressions and confirm rollout success
