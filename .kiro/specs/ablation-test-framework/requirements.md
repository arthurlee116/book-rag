# Requirements Document (Revised v2)

## Introduction

ERR Ablation Test Framework 是一个 **CLI 工具**，用于系统性地评估 ERR RAG Pipeline 中各个技术组件的效果。该框架通过 YAML 配置文件定义实验，输出 JSONL 逐题结果和 Markdown 报告，支持断点续跑。

**定位**: 仅面向 `Research Files/rag_eval` 目录下的研究语料，不支持用户上传文档。

---

## Glossary

- **Ablation_Study**: 消融实验，通过逐个开关某个技术组件来评估其贡献
- **Experiment_Config**: 实验配置，定义要测试的参数组合（YAML 格式）
- **Variant**: 变体，单个实验中的一种参数配置
- **Baseline**: 基线配置，用于对比的参考配置（Normal 或 Fast）
- **Pipeline_Component**: Pipeline 组件，可独立开关的技术点
- **Metrics**: 评测指标，包括质量指标和效率指标
- **JSONL**: JSON Lines 格式，每行一个 JSON 对象，天然支持追加写入和 resume

---

## 安全与隐私声明

**重要**: 实验输出文件（JSONL、Markdown 报告）会包含：
- 完整的问题文本
- 系统生成的回答
- 引用的 chunk 文本内容

这些内容可能包含敏感信息（如法律条文细节）。因此：

1. **本工具仅面向 `Research Files/rag_eval` 的研究语料**
2. 不支持用户上传任意文档运行实验
3. 输出文件不应提交到公开仓库（已在 .gitignore 中排除）
4. **Phase 2**: 如需支持用户文档，需添加脱敏开关

---

## Phase 1 可用的消融变量

以下变量在 Phase 1 可以进行消融实验：

| 变量 | 可用模式 | 说明 |
|------|----------|------|
| MRL Dimension | **仅 Fast 模式** | `chat()` 只在 `fast_mode=True` 时使用 `search_dim` |
| Drift Filter | Normal 模式 | `drift_filter_enabled` 开关 |
| Multi-Query Expansion | Normal 模式 | `query_fusion_enabled` 开关 |
| HyDE | Normal 模式 | `hyde_enabled` 开关 |
| LLM Rerank | Normal 模式 | `llm_rerank_enabled` 开关 |
| Repack Strategy | Normal 模式 | `repack_strategy`: reverse/forward/none |

## Phase 2 待实现的消融变量

以下变量当前代码不支持独立开关，需要先修改核心代码：

| 变量 | 原因 | Phase 2 工作 |
|------|------|-------------|
| RRF Fusion (on/off) | 无独立开关，融合逻辑硬编码 | 添加 `rrf_enabled` 设置 |
| Hybrid Weights | 权重硬编码为 0.8/0.2 | 暴露为 Settings 参数 |
| MRL in Normal Mode | `chat()` Normal 模式不接受 `search_dim` | 修改 `chat()` 函数签名 |

---

## 核心指标定义（精确规范）

### 质量指标

#### cite_ok (引用正确性)
- **定义**: 回答中的引用是否符合格式要求且在有效范围内
- **计算方法**: 复用 `backend/app/guardrails.py` 的 `extract_citation_numbers()` 和 `enforce_strict_rag_answer()` 逻辑
- **判定规则**:
  - 如果回答是 `STRICT_NO_MENTION`（"文档未提及"），则 `cite_ok = True`
  - 否则，必须存在至少一个引用 `[n]`，且所有 `n` 在 `[1, len(citations)]` 范围内
- **值**: `True` / `False`

#### gold_hit_any (命中任意 gold chunk)
- **定义**: 检索返回的 top_k chunks 中是否包含至少一个 gold chunk
- **计算方法**: `bool(set(gold_chunk_ids) & set(retrieved_chunk_ids))`
- **数据来源**:
  - `gold_chunk_ids`: 题目 `bundle[].chunk_id`
  - `retrieved_chunk_ids`: `resp.citations[].id`
- **值**: `True` / `False`

#### gold_hit_all (命中所有 gold chunks)
- **定义**: 检索返回的 top_k chunks 是否包含所有 gold chunks
- **计算方法**: `set(gold_chunk_ids).issubset(set(retrieved_chunk_ids))`
- **值**: `True` / `False`

#### gold_coverage (gold chunk 覆盖率)
- **定义**: gold chunks 被检索命中的比例
- **计算方法**: `len(set(gold_chunk_ids) & set(retrieved_chunk_ids)) / len(gold_chunk_ids)` (如果 gold 为空则为 0.0)
- **值**: `0.0` - `1.0`

### 效率指标

#### elapsed_s (单题延迟)
- **定义**: 单次 `chat()` 调用的 wall time
- **计算方法**: `time.time()` 差值
- **单位**: 秒

#### 延迟百分位统计
- **p50_latency_s**: 中位数延迟
- **p95_latency_s**: 95 百分位延迟
- **计算方法**: `numpy.percentile(latencies, [50, 95])`

---

## 可复现性约束

### 题目子集选择规则
- **固定规则**: 按文件顺序取前 N 条（`questions[:limit]`）
- **不使用随机抽样**（避免 seed 管理复杂性）

### 结果文件 Header
每个实验的 JSON 汇总文件必须包含以下元数据：

```json
{
  "experiment_name": "mrl_dimension_ablation",
  "questions_path": "Research Files/rag_eval/questions/questions_clean_allow_meta_100.jsonl",
  "limit": 100,
  "top_k": 10,
  "variants": [...],
  "started_at": "2025-12-21T10:00:00Z",
  "completed_at": "2025-12-21T12:30:00Z"
}
```

### 重跑对齐
- 相同的 `questions_path` + `limit` + `top_k` + `variant settings` 应产生可比较的结果
- 由于 LLM 非确定性，质量指标可能有小幅波动，但应在统计误差范围内

---

## Requirements

### Requirement 1: Pipeline 组件配置管理

**User Story:** As a researcher, I want to configure which pipeline components to enable/disable, so that I can run controlled ablation experiments.

#### Acceptance Criteria

1. THE System SHALL support toggling the following pipeline components independently (Phase 1):
   - MRL Dimension (128/256/512/1024/2048) - **仅 Fast 模式**
   - Query Drift Filtering (on/off)
   - Multi-Query Expansion (on/off)
   - HyDE (on/off)
   - LLM Rerank (on/off)
   - Context Repacking (reverse/forward/none)

2. WHEN a user creates an experiment config, THE System SHALL validate that:
   - MRL 维度消融只能在 `baseline: fast` 下进行
   - 所有引用的参数名与 `backend/app/config.py` 的 Settings 一致

3. THE System SHALL provide preset configurations in `experiments.yaml` for common ablation types.

4. WHEN saving experiment results, THE System SHALL persist完整配置到 JSON header 以保证可复现。

### Requirement 2: 单变量对比实验

**User Story:** As a researcher, I want to run experiments that change only one variable at a time, so that I can isolate the effect of each component.

#### Acceptance Criteria

1. WHEN a user defines a single-variable experiment, THE System SHALL automatically generate all configuration variants by toggling only that variable against the baseline.

2. THE System SHALL support the following single-variable experiment types (Phase 1):
   - MRL Dimension comparison (5 variants: 128/256/512/1024/2048) - **仅 Fast 模式**
   - Drift Filter ablation (2 variants: on/off)
   - Multi-Query ablation (2 variants: on/off)
   - HyDE ablation (2 variants: on/off)
   - LLM Rerank ablation (2 variants: on/off)
   - Repacking strategy comparison (3 variants: reverse/forward/none)

3. WHEN running a single-variable experiment, THE System SHALL ensure all other parameters remain constant across variants.

4. THE System SHALL support including Normal baseline as a reference point when running Fast mode experiments.

### Requirement 3: 实验执行与进度追踪

**User Story:** As a researcher, I want to run experiments and see progress, so that I can monitor long-running evaluations.

#### Acceptance Criteria

1. WHEN an experiment starts, THE System SHALL print to stdout:
   - 实验名称和配置摘要
   - 总题目数和变体数
   - 预计运行时间（基于历史数据，可选）

2. THE System SHALL output progress via stdout logs (not SSE), format:
   ```
   [ablation] {done}/{total} config={variant} id={qid} elapsed={s:.2f}s cite_ok={bool} gold_any={bool} ETA~{min:.1f}m
   ```

3. WHEN a question evaluation completes, THE System SHALL immediately append the result to `{experiment}.jsonl` (天然支持 resume).

4. IF an experiment is interrupted (Ctrl+C or error), THE System SHALL:
   - 已写入 JSONL 的结果自动保留
   - 下次运行时通过 key 去重跳过已完成的题目

5. THE System SHALL support configurable question limits:
   - `--limit 20`: 快速验证
   - `--limit 50`: 标准测试
   - `--limit 0` 或不指定: 全部题目

### Requirement 4: 成本预估 (Phase 2 - 可选)

**User Story:** As a researcher, I want to estimate the cost before running an experiment, so that I can budget my API usage.

#### Acceptance Criteria (Phase 2)

**注意**: 当前 `OpenRouterClient` 不返回 `usage` 字段，无法获取真实 token 消耗。Phase 1 仅提供静态粗估。

1. THE System MAY display a rough cost estimate based on:
   - 题目数 × 变体数 × 用户可配置的平均 tokens/call
   - 用户可配置的模型价格

2. THE System SHALL NOT claim cost estimates are accurate (仅供参考).

3. **Phase 2**: 解析 OpenRouter 响应中的 `usage` 字段，提供真实成本追踪。

### Requirement 5: 结果存储与管理

**User Story:** As a researcher, I want to save and manage experiment results, so that I can compare across multiple runs.

#### Acceptance Criteria

1. WHEN a question evaluation completes, THE System SHALL append to `{experiment}.jsonl`:
   ```json
   {
     "key": "{question_id}::{variant_name}::topk={top_k}",
     "question_id": "...",
     "source": "...",
     "config": "variant_name",
     "fast_mode": true/false,
     "dim": 1024,
     "top_k": 10,
     "question": "...",
     "answer": "...",
     "citation_numbers": [1, 2],
     "citation_range_ok": true,
     "retrieved_chunk_ids": ["...", "..."],
     "gold_chunk_ids": ["...", "..."],
     "gold_metrics": {...},
     "evaluation": {...},
     "elapsed_s": 4.52,
     "ts": 1703145600.0
   }
   ```

2. THE System SHALL store all experiment results in `Research Files/rag_eval/experiments/` directory.

3. WHEN an experiment completes, THE System SHALL generate a summary JSON file containing:
   - 实验元数据（用于可复现性）
   - 每个变体的汇总指标

4. THE System SHALL support listing past experiments by scanning the experiments directory.

### Requirement 6: 报告生成 - 表格

**User Story:** As a researcher, I want to generate publication-ready tables, so that I can include them in my paper.

#### Acceptance Criteria

1. THE System SHALL generate Markdown tables comparing metrics across configuration variants, including:
   - 质量指标: cite_ok_rate, gold_hit_any_rate, gold_hit_all_rate, avg_gold_coverage
   - 效率指标: avg_latency_s, p50_latency_s, p95_latency_s

2. THE System SHALL highlight the best and worst values in each metric column (using bold/italic).

3. THE System SHALL support exporting tables in multiple formats:
   - Markdown (默认)
   - LaTeX (for academic papers)
   - CSV (for further analysis)

4. **Phase 2**: 统计显著性标记（需要先确定检验方案：paired t-test / bootstrap / McNemar）

### Requirement 7: 报告生成 - 图表

**User Story:** As a researcher, I want to generate publication-ready charts, so that I can visualize experiment results.

#### Acceptance Criteria

1. THE System SHALL generate the following chart types using **matplotlib**:
   - Bar chart: comparing a single metric across configurations
   - Line chart: showing metric trends (e.g., MRL dimension vs accuracy)
   - Scatter plot: latency vs accuracy tradeoff

2. THE System SHALL support exporting charts as:
   - PNG (默认, 300 DPI)
   - SVG (vector format for papers)
   - PDF (for direct inclusion in LaTeX)

3. WHEN exporting charts, THE System SHALL apply a clean style with:
   - Clear axis labels and legends
   - Consistent color scheme
   - Appropriate font sizes for print

### Requirement 8: 与现有评测脚本的集成

**User Story:** As a developer, I want the new framework to reuse existing evaluation logic, so that results are consistent with previous experiments.

#### Acceptance Criteria

1. THE System SHALL reuse the existing backend `chat()` function for running queries (直接进程内调用，不走 HTTP).

2. THE System **MUST** use `system_eval_fast_vs_normal.py` 的 `_ingest_one()` 路径进行文档摄入:
   - 读取 `chunks/*.jsonl` 预生成的 chunks
   - 使用 `embeddings/` 目录的缓存
   - **不调用 `main.py` 的 `_ingest_file()`**（会导致 chunk_id 不稳定）

3. THE System SHALL store results in a format compatible with existing scripts (`summarize_results.py`).

4. WHEN running experiments, THE System SHALL perform complete session flush between questions:
   ```python
   session.chat_history = []
   session.reference_ids = {}
   session.references = []
   session.latest_evaluation = None
   ```
   (参考 `system_eval_fast_vs_normal.py` 的 `flush_session_for_next_question()`)

### Requirement 9: 错误处理与恢复

**User Story:** As a researcher, I want the system to handle errors gracefully, so that I don't lose progress on long experiments.

#### Acceptance Criteria

1. IF an API call fails, THE System SHALL retry up to 3 times with exponential backoff before marking the question as failed.

2. IF a question evaluation fails, THE System SHALL:
   - 记录错误到 JSONL（`"error": "..."`）
   - 继续下一题

3. THE System SHALL support resume by:
   - 读取已有 JSONL 文件
   - 提取所有已完成的 `key`
   - 跳过已完成的 (question_id, variant) 组合

4. IF the system detects API key issues (invalid/rate-limited), THE System SHALL:
   - 打印明确的错误信息
   - 建议用户检查 `OPENROUTER_API_KEY`

---

## Phase 2 Requirements (Web UI - 暂不实现)

以下需求移至 Phase 2，待 CLI 工具稳定后考虑：

- **Requirement 10**: Web UI - 实验配置页面
- **Requirement 11**: Web UI - 进度监控页面 (SSE)
- **Requirement 12**: Web UI - 结果查看页面 (ECharts)
- **Requirement 13**: 统计显著性检验
- **Requirement 14**: 真实成本追踪 (需要 OpenRouter usage 解析)
- **Requirement 15**: 用户文档支持 (需要脱敏机制)
