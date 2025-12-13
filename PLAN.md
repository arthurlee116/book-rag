# Ephemeral RAG Reader (ERR) — Build Plan (Detailed Checklist)

目标：实现一个 **privacy-first / session-based / in-memory** 的文档问答 Web App（Next.js 16 + FastAPI），具备 **Advanced Hybrid Search (FAISS + BM25)**，并且 **Strict RAG（禁止外部知识）**。

> 规则：按步骤实现；每完成一项就把对应的 `[ ]` 改为 `[x]`。
> 一定要用 Nextjs 16 App Router + FastAPI。

---

## 0) Repo / DX 基础

- [x] 约定目录结构（推荐）
  - [x] `backend/`：FastAPI + RAG 逻辑（仅内存，不落库）
  - [x] `frontend/`：Next.js 16 App Router + Tailwind + Zustand
  - [x] `OpenRouter Files/`：OpenRouter 官方文档（已存在）
- [x] 定义环境变量（后续会写到 `backend/.env.example` & `frontend/.env.example`）
  - [x] `OPENROUTER_API_KEY`
  - [x] `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`
  - [x] `OPENROUTER_HTTP_REFERER=http://localhost:3000`
  - [x] `OPENROUTER_X_TITLE=ERR-App`
- [x] 明确“Ephemeral”策略
  - [x] `sessions: dict[session_id] -> {retriever, chunks, chat_history, logs, expires_at, ...}`
  - [x] Session TTL（例如 30min inactivity / 2h hard TTL）
  - [x] Single file per session：新上传覆盖旧文件（释放旧索引内存）

---

## 1) Backend Setup（requirements / scaffolding）

- [x] 创建 `backend/requirements.txt`
  - [x] 必需：`fastapi`, `uvicorn`, `pydantic`
  - [x] 上传：`python-multipart`
  - [x] HTTP：`httpx`（调用 OpenRouter）
  - [x] NLP：`jieba`, `spacy`
  - [x] Keyword：`rank_bm25`
  - [x] Vector：`faiss-cpu`, `numpy`
  - [x] 可选增强：`tenacity`（重试）、`sse-starlette`（SSE）
- [x] 创建 FastAPI 基础目录结构（最少）
  - [x] `backend/app/__init__.py`
  - [x] `backend/app/models/`（Pydantic models）
  - [x] `backend/app/retrieval/`（HybridRetriever）
  - [x] `backend/app/ingestion/`（FileParser + Chunker）

---

## 2) Ingestion Logic（Chunker + FileParser）

### 2.1 Chunk 数据结构（严格固定）
- [x] 实现 `ChunkModel`（必须字段）
  - [x] `id: str`
  - [x] `content: str`
  - [x] `rich_content: str`
  - [x] `prev_content: str | None`
  - [x] `next_content: str | None`
  - [x] `metadata: dict`

### 2.2 FileParser（按格式解析，尽量保留章节结构）
- [x] 支持扩展名：`.epub`, `.mobi`, `.docx`, `.txt`, `.md`
- [x] 解析原则
  - [x] 提取纯文本为主，忽略图片
  - [x] 尽量保留 `Chapter/Heading` 结构到 `metadata`（例如 `chapter_title`, `chapter_index`）
  - [x] 输出：按“段落”或“章节段落”组成的文本单元列表
- [x] 对 `.md` / `.txt`：按空行分段
- [x] 对 `.docx`：按 paragraph 分段（python-docx）
- [x] 对 `.epub` / `.mobi`：用 ebooklib 提取 HTML->text（保留 basic tags 作为 rich_content 线索）

### 2.3 Chunker（段落分块 + prev/next 冗余）
- [x] 以“段落”为基本单元，目标每 chunk ~500 tokens（近似即可）
  - [x] 简化策略：字符/词数阈值近似 token 数（后续可改成 tiktoken）
- [x] 生成 chunk 列表后，再补齐冗余字段
  - [x] 第 i 个 chunk：
    - [x] `prev_content = chunks[i-1].content`（i>0）
    - [x] `next_content = chunks[i+1].content`（i<last）

---

## 3) Search Logic（HybridRetriever：FAISS + BM25 + Fusion）

### 3.1 Index 构建（in-memory）
- [x] 输入：`chunks: list[ChunkModel]`
- [x] Vector index
  - [x] embedding model：`qwen/qwen3-embedding-8b`（维度 2048）
  - [x] FAISS：`IndexFlatIP`（需要 L2 normalize → cosine similarity）
  - [x] 存储：`doc_embeddings (float32, normalized)` + `faiss_index`
- [x] BM25 index
  - [x] corpus tokenization（按 doc language 选择）
    - [x] 中文：`jieba.lcut`
    - [x] 英文：`spacy` tokenizer（必要时 fallback）
  - [x] `BM25Okapi(tokenized_corpus)`

### 3.2 Retrieval（并行检索 + normalization + fusion）
- [x] 向量检索（权重 0.8）
  - [x] query embedding（同模型，同维度 2048）
  - [x] FAISS top-N（候选集 N >= top_k）
  - [x] vector score 归一到 [0,1]（cosine [-1,1] → [0,1]）
- [x] BM25 检索（权重 0.2）
  - [x] 对 expanded_query 分词
  - [x] 获取 top-N 候选
  - [x] 对该 query 的 top-N BM25 scores 做 MinMax → [0,1]
- [x] 融合
  - [x] `Final = 0.8 * Vector + 0.2 * BM25_norm`
  - [x] union 候选集后 rerank，返回 top_k

---

## 4) API Routes（FastAPI）

### 4.1 Session & Memory Store
- [x] `SESSIONS: dict[str, SessionState]`（进程内）
- [x] Session TTL 清理协程/后台任务
- [x] 单文件模式：上传新文件覆盖旧 retriever/chunks/chat_history

### 4.2 `/upload`（后台任务 + SSE logs）
- [x] `POST /upload` 接收文件（multipart）
- [x] 启动 background task
  - [x] parse → chunk → embed batches → build indexes
  - [x] 逐步写 log 到 session 的 log buffer（用于 SSE）
- [x] SSE endpoint：`GET /api/logs/{session_id}`
  - [x] event 格式：`data: [LOG] ...\n\n`

### 4.3 `/chat`（Strict RAG + citations）
- [x] Phase 1：Query Expansion（gemini-2.5-flash, temp=0）
  - [x] system prompt（翻译引擎，仅输出翻译后的 query string）
- [x] Phase 2：HybridRetriever 并行检索
- [x] Phase 3：构造上下文（chunks content + ids）
- [x] Phase 4：生成回答（Strict RAG）
  - [x] 如果文档不包含答案：必须输出 **The document does not mention this.**
  - [x] citations：`[1][2]` stacked
- [x] Token limit：超限直接 `400 Session limit reached. Please export and refresh.`

---

## 5) Frontend（Next.js 16 + Tailwind + Zustand）

### 5.1 App 结构
- [x] `frontend/app/` routes（App Router）
- [x] Zustand store：session_id / upload status / chat history / citations / right panel state

### 5.2 Upload + “Terminal Loader”
- [x] 上传后打开 Terminal Window
- [x] 前端订阅 SSE：`/api/logs/{session_id}`
- [x] 逐行追加：`> Building Inverted Index...`

### 5.3 Split View（Desktop First）
- [x] Left 60%：Chat
- [x] Right 40%：Document Viewer（默认隐藏）
- [x] 引用按钮 `[1]` 可点击 → 打开右侧面板
- [x] Island View 渲染：
  - [x] `prev_content`（灰）
  - [x] `content`（高亮/加粗）
  - [x] `next_content`（灰）

---

## 6) Export（Markdown）
- [x] 导出 chat history（用户/AI）
- [x] Appendix：按引用编号输出 chunk 原文

---

## 7) Quality / Guardrails
- [x] 严格 RAG 规则单元测试 / 最小 smoke test
- [x] “不可用时错误提示”统一（OpenRouter error schema）
- [x] 日志：每个阶段都必须有可见 SSE log
