# Change: 全量修复 Fast/Normal Pipeline 性能问题并重构后端模块边界

## Why
当前后端在功能正确性上总体可用，但在“低延迟路径设计、检索热路径实现、可维护性分层、鲁棒性兜底”四个维度存在系统性偏差。问题已经影响：

1. Fast mode 的速度收益被固定开销和实现细节稀释。
2. Normal mode 的部分步骤存在可避免的远程调用与重复计算。
3. 检索与路由编排代码耦合在 `main.py`，后续迭代风险高。
4. 个别异常路径缺少 fail-safe，可能导致会话状态不一致。
5. 一些实现细节（JSON 提取正则、指令模板格式）存在可预防的健壮性瑕疵。

本变更目标是：在不改变 API 契约前提下，完成你列出的全部修复项，并将后端编排结构调整为可持续演进的模块化形态。

## Explicit Problem Inventory (必须全部覆盖)

| ID | 问题 | 来源 | 严重级别 |
|---|---|---|---|
| F02 | Normal mode 无条件语言对齐导致固定 LLM 延迟 | 你指定“修复第二个” | P1 |
| F04 | ingest chunking 异常缺少兜底，可能卡住 processing | 你指定“修复第四个” | P1 |
| F05 | HyDE 检索重复执行 BM25，造成无效 CPU 开销 | 你指定“修复第五个” | P2 |
| F06 | fast mode 使用偏大的固定 candidate_k，速度受损 | 你指定“修复第六个” | P2 |
| F08 | `_extract_json_text` 正则转义错误影响稳健性 | 你指定“修复第八个” | P3 |
| A01 | MRL fast 检索每次全量矩阵乘法，未利用 FAISS | 你新增问题 1 | P1 |
| A02 | fast embedding 聚合策略过于简单（mean） | 你新增问题 2 | P2 |
| A03 | fast mode 跳过 re-packing 与设计目标冲突 | 你新增问题 3 | P2 |
| A04 | BM25 使用 `rank_bm25` 纯 Python，扩展性受限 | 你新增问题（bm25s 建议） | P2 |
| A05 | BM25 英文分词依赖 spaCy，热路径偏重 | 你新增问题（轻量分词建议） | P2 |
| A06 | embedding query instruction 模板 `Query:` 缺少空格 | 你新增问题（格式瑕疵） | P3 |
| A07 | `main.py` 职责过载，模块边界不清晰 | 你新增问题（拆分建议） | P1 |

## What Changes

### 1) 后端架构重构（职责拆分）
- 将 `backend/app/main.py` 拆分为：
  - `backend/app/routes.py`：路由定义与依赖注入边界
  - `backend/app/chat_pipeline.py`：chat 编排与检索策略
  - `backend/app/ingestion_pipeline.py`：上传后 ingest 编排
- `main.py` 保留应用生命周期、CORS、中间件与路由挂载。
- 保持现有 API 路由与响应结构不变：`/upload`、`/chat`、`/evaluation`、`/api/logs/{session_id}`、`/export/{session_id}`。

### 2) 检索与性能修复（fast + normal）
- 语言对齐从“normal 必调”改为“仅跨语言时触发”，避免不必要的 LLM 请求。
- HyDE 查询改为向量优先检索，不重复跑同 query 的 BM25。
- 引入 fast mode 独立候选参数（`ERR_FAST_MODE_CANDIDATE_K`）替代单一硬编码。
- fast mode 的 query embedding 聚合从 simple mean 改为加权聚合（优先原始 query）。
- fast mode 允许执行 re-packing，与 normal mode 保持一致策略（默认 reverse）。

### 3) MRL 检索实现升级
- 在 retriever 中为 MRL 维度构建/缓存 FAISS `IndexFlatIP`，fast mode 检索不再依赖每次全量矩阵乘法。
- 保留维度截断后重新归一化逻辑，保证 MRL 语义正确性。

### 4) 词法检索与分词升级
- 将 BM25 后端从 `rank-bm25` 迁移到 `bm25s`。
- 英文分词从 spaCy 热路径迁移为轻量 tokenizer（正则+lower），保留中文 `jieba`。
- 维持单文档场景下的行为一致性，并为多文档扩展预留性能空间。

### 5) 鲁棒性与配置契约修复
- ingest chunking 增加异常兜底，确保失败状态可观测且可终止。
- 修复 OpenRouter JSON code-fence 清理正则。
- 指令模板默认值改为 `"Instruct: {task}\nQuery: {query}"`。
- 更新 `.env.example` 与配置说明，新增 fast candidate_k 等参数。

## Detailed Solution Mapping (问题 -> 修复策略)

- F02 -> 在 chat pipeline 增加“语言一致跳过对齐”判定逻辑，并将跳过记录入 evaluation steps。
- F04 -> `chunker.chunk(...)` 包裹 try/except，写入 `ingest_status=error` + `ingest_error` + 日志。
- F05 -> retriever `search()` 增加关闭 BM25 分支能力，HyDE job 使用 vector-only。
- F06 -> `HybridRetriever.search()` 支持 `candidate_k_override`；fast mode 从新配置读取。
- F08 -> 正则从 `\\s` 修复为 `\s`。
- A01 -> retriever 新增 MRL FAISS index 缓存并在 fast path 使用。
- A02 -> fast mode embedding 改用 `_weighted_embedding_mean`，并保证原始 query 位于高权重位置。
- A03 -> fast mode 参与 re-pack strategy，不再固定跳过。
- A04 -> 替换 `rank-bm25` 为 `bm25s` 并更新依赖与索引构建逻辑。
- A05 -> 英文 tokenizer 使用轻量实现，移除 BM25 热路径对 spaCy 的依赖。
- A06 -> 更新默认 instruction template 空格。
- A07 -> 完成 `main.py` -> `routes/chat_pipeline/ingestion_pipeline` 解耦。

## Scope Boundaries

### In Scope
- 后端 Python 检索与编排路径。
- 配置、依赖、单元测试、文档契约的同步更新。
- 部署与上线验证（在可用凭据/网络前提下）。

### Out of Scope
- 新增业务接口或改变前端 API 协议。
- 改变“会话内存态 + TTL”的隐私模型。
- 替换 OpenRouter 供应商。

## Risks & Mitigations
- 风险：BM25 库迁移可能改变边界排序。
  - 缓解：补充检索结果稳定性测试，保持 top-k 行为一致性阈值。
- 风险：模块拆分可能引入循环依赖。
  - 缓解：通过清晰的依赖方向（routes -> pipeline -> primitives）与回归测试保障。
- 风险：fast mode 重排可能影响少量旧结果排序。
  - 缓解：通过配置保留策略控制，默认与 normal 一致。

## Validation Plan
- Backend unit tests 全量通过。
- OpenSpec strict validation 通过。
- 本地关键路径验证：上传、chat(normal/fast)、export、evaluation。
- 部署后健康检查：`/health`、前端首页、`/backend/health`。
- 监控上线后日志与可用性状态，确认无回滚信号。

## Assumptions
1. 你当前消息视为“proposal 已批准并授权立即实施”，无需等待二次确认。
2. 允许新增依赖（`bm25s` 等）并更新锁定约束。
3. 允许对后端模块进行重构，只要 API 契约不破坏。
4. 部署凭据（SSH/GitHub）在本机环境中可直接使用；若受限，则采用同等可执行替代并记录。

## Impact

### Affected Specs
- `retrieval-pipeline`
- `ingestion-resilience`
- `indexing-performance`
- `backend-modularization`
- `config-contract`

### Affected Code (expected)
- `backend/app/main.py`
- `backend/app/routes.py` (new)
- `backend/app/chat_pipeline.py` (new)
- `backend/app/ingestion_pipeline.py` (new)
- `backend/app/retrieval/hybrid_retriever.py`
- `backend/app/openrouter_client.py`
- `backend/app/config.py`
- `backend/.env.example`
- `backend/requirements.txt`
- `backend/constraints.txt`
- `backend/tests/*`
- `README.md`, `README.zh-CN.md`（必要时）
