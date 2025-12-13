# ERR — Retrieval Quality Upgrade Tasks (Qwen3-Embedding + Multi-Query/HyDE/RRF + LLM Rerank)

目标（你的偏好）：**更少假阴性（宁愿多答一点）**。核心策略：**Recall-first** → **稳健融合** → **轻量 rerank** → 最终仍保持 **Strict RAG + citations**。

本文件用于你测试/验收，以及后续迭代（方案 C）时作为 checklist。

---

## 0) What’s Implemented (So Far)

已实现（backend `/chat`）：

- Multi-Query：对齐到文档语言后生成多个 query 变体
- HyDE：生成一段“假想文档段落”仅用于检索（不用于回答）
- Query drift filtering：用 embedding cosine 相似度过滤明显跑偏的 query 变体（保守过滤、偏 recall）
- RRF（Reciprocal Rank Fusion）：把多路检索结果做鲁棒融合
- LLM yes/no judge rerank：用现有 `OPENROUTER_CHAT_MODEL` 对候选 chunk 做排序（不强过滤，偏 recall）

Strict RAG 保持不变：

- 回答必须来自 CONTEXT
- 需要合法 `[n]` 引用，否则后端会重试一次，仍失败才 fallback

---

## 1) Configuration (Env Vars)

在 `backend/.env.example` 已列出全部参数。你可以做 A/B 消融时按下面开关组合。

### Embedding Query Formatting (Qwen3 instruction-aware)
- `ERR_EMBEDDING_QUERY_USE_INSTRUCTION=true`
- `ERR_EMBEDDING_QUERY_INCLUDE_RAW=true`
- `ERR_EMBEDDING_QUERY_INSTRUCTION_TEMPLATE="Instruct: {task}\nQuery:{query}"`
- `ERR_EMBEDDING_QUERY_TASK="Given a question, retrieve relevant passages from the document that explicitly contain the answer."`

### Multi-Query + HyDE + Drift Filter + RRF
- `ERR_QUERY_FUSION_ENABLED=true`
- `ERR_QUERY_VARIANTS_COUNT=6`
- `ERR_QUERY_VARIANTS_MAX=8`
- `ERR_HYDE_ENABLED=true`
- `ERR_HYDE_MAX_WORDS=140`
- `ERR_DRIFT_FILTER_ENABLED=true`
- `ERR_DRIFT_SIM_THRESHOLD=0.25`
- `ERR_HYDE_DRIFT_SIM_THRESHOLD=0.15`
- `ERR_RRF_K=60`
- `ERR_FUSION_PER_QUERY_TOP_K=50`
- `ERR_FUSION_MAX_CANDIDATES=120`

### LLM Rerank (yes/no judge using Gemini)
- `ERR_LLM_RERANK_ENABLED=true`
- `ERR_LLM_RERANK_MODEL=`（留空表示用 `OPENROUTER_CHAT_MODEL`）
- `ERR_LLM_RERANK_CANDIDATE_POOL=30`
- `ERR_LLM_RERANK_MAX_CHARS=900`

---

## 2) How To Evaluate (Recommended Protocol)

你的目标是“减少 The document does not mention this 的假阴性”，所以建议你用 **两类问题集** 测：

### 2.1 Answerable Set（文档里明确提到）
- 选 30～50 个问题，答案在文档里有明确句子/段落能引用
- 覆盖类型：
  - factual（谁/什么/哪里/什么时候）
  - causality（为什么/因果）
  - procedural（怎么做/步骤）
  - quote-like（某一句话/某个描述）

### 2.2 Unanswerable Set（文档里确实没有）
- 选 15～30 个问题，确保文档不含答案（避免主观争议）

### 2.3 Metrics（你手工也能做）
建议你每个问题记录：
- `Answer?`：是否给出非 fallback 的答案
- `Citations valid?`：引用是否在范围内、点击是否对应语义正确 chunk
- `False refusal`：文档可答但却返回 fallback（你最关心）
- `False answer`：文档不可答但却硬答（次关心，但仍要观察趋势）

如果你愿意更系统（后续可做自动化评估）：
- Recall@K：答案 chunk 是否在 topK 检索候选中（需要我们把检索 debug 输出做成可选开关）
- Faithfulness：回答内容是否能被引用 chunk 覆盖（方案 C 会更强）

---

## 3) Ablation Checklist (快速定位收益来自哪)

建议你用同一批问题集跑多轮，按下面顺序开关做消融：

1. **Baseline**：`ERR_QUERY_FUSION_ENABLED=false` + `ERR_LLM_RERANK_ENABLED=false`
2. **+ Multi-Query only**：`ERR_QUERY_FUSION_ENABLED=true`、`ERR_HYDE_ENABLED=false`、`ERR_LLM_RERANK_ENABLED=false`
3. **+ HyDE**：`ERR_HYDE_ENABLED=true`（其余同上）
4. **Drift filter off**：`ERR_DRIFT_FILTER_ENABLED=false`（看是否召回更高但噪声更大）
5. **+ LLM rerank**：`ERR_LLM_RERANK_ENABLED=true`（看“引用更稳定/答案更靠近证据”是否改善）

对你偏好（宁愿多答一点）：
- 如果你仍觉得假阴性偏高：提高 `ERR_QUERY_VARIANTS_COUNT` 或 `ERR_FUSION_PER_QUERY_TOP_K`
- 如果你开始出现“明显硬答/错引”：打开 drift filter（或提高阈值），并把 rerank pool 调大但 `top_k` 不变

---

## 4) Observability (What To Look For In Logs)

后端会写一些关键日志（SSE / 控制台都能看到）：
- `Chat: generating query variants`
- `Chat: generating HyDE passage`
- `Chat: fusion queries=X hyde=on/off`
- `Chat: retrieval (multi-query + RRF fusion)`
- `Chat: LLM rerank pool=...`
- `Guardrails triggered... -> retrying once`

你如果需要更深的可观测性（下一轮可以加）：
- 输出每个 query 变体的 drift similarity
- 输出 RRF top20 chunk ids + snippet
- 输出 rerank 前后 topK 变化

---

## 5) Next Step (After You Validate): Scheme C

当你确认 A/B 跑通并测完后，我会按“方案 C”继续做：

- Answerability first：先让模型做 **可答性判定 + 证据抽取（必须是原文子串）**
- Evidence-grounded generation：只在证据通过校验时生成最终回答
- 自动化评估：把 False refusal / False answer / citation faithfulness 做成可复现的测试集

