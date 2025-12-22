# Design Document: ERR Ablation Test Framework (Revised v2)

## 0. 关键约束与设计决策

### 0.1 必须遵守的约束

| 约束 | 原因 | 解决方案 |
|------|------|----------|
| **必须使用 `_ingest_one()` 路径** | `main.py` 的 `_ingest_file()` 每次生成随机 chunk_id，会导致 gold_hit 指标失真 | 复用 `system_eval_fast_vs_normal.py` 的 `_ingest_one()`，读取预生成的 `chunks/*.jsonl` |
| **MRL 消融仅限 Fast 模式** | `chat()` 只在 `fast_mode=True` 时使用 `search_dim` 参数 | 在配置验证时强制检查 |
| **完整 session flush** | 只清 `chat_history` 会导致 `references` 和 `latest_evaluation` 污染 | 复用 `flush_session_for_next_question()` 的完整清理逻辑 |
| **CLI 优先，无 Web UI** | 同进程执行会阻塞事件循环，Web UI 过度工程化 | YAML 配置 + CLI + 静态报告 |
| **指标计算复用现有逻辑** | 避免实现不一致 | 复用 `guardrails.py` 和 `_calc_gold_coverage()` |

### 0.2 Phase 1 不支持的功能

| 功能 | 原因 | Phase 2 工作 |
|------|------|-------------|
| RRF Fusion 开关 | 代码中无独立开关 | 添加 `rrf_enabled` 设置 |
| Hybrid Weights 调整 | 权重硬编码 0.8/0.2 | 暴露为 Settings 参数 |
| Normal 模式 MRL | `chat()` 不接受 `search_dim` | 修改函数签名 |
| 真实成本追踪 | OpenRouterClient 不返回 usage | 解析响应 usage 字段 |
| 统计显著性检验 | 需要确定检验方案 | 实现 paired t-test/bootstrap |

---

## 1. 架构

### 1.1 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLI Tool (Python)                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  ablation_runner.py    - 主入口，读取 YAML 配置，执行实验                      │
│  ablation_config.py    - 配置加载、验证、变体生成                              │
│  ablation_report.py    - 生成 Markdown/LaTeX/CSV 报告和 matplotlib 图表       │
└────────────┬────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    复用现有代码（不修改）                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  system_eval_fast_vs_normal.py:                                              │
│  ├─ _ingest_one()              # 带缓存的文档摄入（必须使用此路径）             │
│  ├─ flush_session_for_next_question()  # 完整 session 清理                   │
│  ├─ try_load_cached_embeddings()       # 加载缓存的 embeddings               │
│  ├─ embed_chunks_and_cache()           # 生成并缓存 embeddings               │
│  ├─ load_chunks_manifest()             # 加载 chunks manifest               │
│  ├─ load_chunks_jsonl()                # 加载预生成的 chunks                 │
│  └─ _calc_gold_coverage()              # 计算 gold 覆盖指标                  │
│                                                                              │
│  backend/app/main.py:                                                        │
│  ├─ chat()                     # RAG pipeline（直接调用，不走 HTTP）          │
│  └─ ChatRequest                # 请求模型                                    │
│                                                                              │
│  backend/app/config.py:                                                      │
│  └─ Settings                   # 所有可配置参数                               │
│                                                                              │
│  backend/app/guardrails.py:                                                  │
│  ├─ extract_citation_numbers() # 提取引用编号                                │
│  ├─ enforce_strict_rag_answer()# 验证引用格式                                │
│  └─ STRICT_NO_MENTION          # "文档未提及" 常量                           │
│                                                                              │
│  backend/app/session_store.py:                                               │
│  ├─ get_session()              # 获取 session                                │
│  └─ get_or_create_session()    # 创建 session                                │
└─────────────────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         文件 I/O                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  输入:                                                                       │
│  ├─ Research Files/rag_eval/experiments/experiments.yaml  # 实验配置         │
│  ├─ Research Files/rag_eval/questions/*.jsonl             # 题库             │
│  ├─ Research Files/rag_eval/chunks/*.jsonl                # 预生成 chunks    │
│  ├─ Research Files/rag_eval/chunks/manifest.json          # chunks 清单      │
│  └─ Research Files/rag_eval/embeddings/*.npy              # 缓存 embeddings  │
│                                                                              │
│  输出:                                                                       │
│  ├─ Research Files/rag_eval/experiments/{name}.jsonl      # 逐题结果         │
│  ├─ Research Files/rag_eval/experiments/{name}.json       # 汇总结果         │
│  ├─ Research Files/rag_eval/experiments/{name}.md         # Markdown 报告    │
│  └─ Research Files/rag_eval/experiments/{name}/charts/    # 图表             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 数据流

```
experiments.yaml
       │
       ▼
┌──────────────┐
│ 加载配置     │
│ 验证参数     │
│ 生成变体     │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌─────────────────────────────────┐
│ 加载题目     │────▶│ questions_clean_allow_meta_100  │
│ (按顺序取N条)│     │ .jsonl                          │
└──────┬───────┘     └─────────────────────────────────┘
       │
       ▼
┌──────────────┐     ┌─────────────────────────────────┐
│ 加载已完成   │────▶│ {experiment}.jsonl (如果存在)   │
│ 的 keys      │     │ 用于 resume                     │
└──────┬───────┘     └─────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│ For each source document:                            │
│   _ingest_one() ─────▶ 读取 chunks/*.jsonl           │
│                        加载/生成 embeddings 缓存      │
│                        构建 retriever                │
└──────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│ For each variant:                                    │
│   For each question:                                 │
│     1. flush_session_for_next_question()             │
│     2. clone Settings with variant params            │
│     3. chat(req, settings, openrouter)               │
│     4. 从 session.latest_evaluation 获取指标         │
│     5. 计算 gold_coverage                            │
│     6. 追加写入 JSONL                                │
│     7. 打印进度日志                                  │
└──────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│ 计算汇总指标 │
│ 生成报告     │
│ 生成图表     │
└──────────────┘
```

---

## 2. 配置文件格式

### 2.1 experiments.yaml

```yaml
# Research Files/rag_eval/experiments/experiments.yaml

defaults:
  questions_path: "Research Files/rag_eval/questions/questions_clean_allow_meta_100.jsonl"
  corpus_dir: "Research Files/rag_eval/corpus"
  chunks_manifest: "Research Files/rag_eval/chunks/manifest.json"
  embedding_cache_dir: "Research Files/rag_eval/embeddings"
  top_k: 10

experiments:
  # MRL 维度消融（仅 Fast 模式）
  - name: "mrl_dimension_ablation"
    description: "Compare MRL dimensions in Fast mode"
    baseline: "fast"  # 必须是 fast，因为 Normal 不支持 search_dim
    ablation_variable: "mrl_dimension"
    variants:
      - { dim: 128, name: "fast_dim_128" }
      - { dim: 256, name: "fast_dim_256" }
      - { dim: 512, name: "fast_dim_512" }
      - { dim: 1024, name: "fast_dim_1024" }
      - { dim: 2048, name: "fast_dim_2048" }
    include_normal_baseline: true  # 同时跑 Normal 作为对照
    question_limit: 100

  # Drift Filter 消融（Normal 模式）
  - name: "drift_filter_ablation"
    description: "Test effect of drift filter"
    baseline: "normal"
    ablation_variable: "drift_filter"
    variants:
      - { drift_filter_enabled: true, name: "drift_on" }
      - { drift_filter_enabled: false, name: "drift_off" }
    question_limit: 50

  # HyDE 消融（Normal 模式）
  - name: "hyde_ablation"
    description: "Test effect of HyDE"
    baseline: "normal"
    ablation_variable: "hyde"
    variants:
      - { hyde_enabled: true, name: "hyde_on" }
      - { hyde_enabled: false, name: "hyde_off" }
    question_limit: 50

  # Multi-Query 消融（Normal 模式）
  - name: "multi_query_ablation"
    description: "Test effect of multi-query expansion"
    baseline: "normal"
    ablation_variable: "multi_query"
    variants:
      - { query_fusion_enabled: true, name: "multiquery_on" }
      - { query_fusion_enabled: false, name: "multiquery_off" }
    question_limit: 50

  # LLM Rerank 消融（Normal 模式）
  - name: "llm_rerank_ablation"
    description: "Test effect of LLM reranking"
    baseline: "normal"
    ablation_variable: "llm_rerank"
    variants:
      - { llm_rerank_enabled: true, name: "rerank_on" }
      - { llm_rerank_enabled: false, name: "rerank_off" }
    question_limit: 50

  # Repack 策略消融（Normal 模式）
  - name: "repack_strategy_ablation"
    description: "Test effect of context repacking"
    baseline: "normal"
    ablation_variable: "repack_strategy"
    variants:
      - { repack_strategy: "reverse", name: "repack_reverse" }
      - { repack_strategy: "forward", name: "repack_forward" }
      - { repack_strategy: "none", name: "repack_none" }
    question_limit: 50
```

---

## 3. 数据模型

### 3.1 配置模型

```python
# ablation_config.py

from pydantic import BaseModel, field_validator
from typing import Optional, Any
from enum import Enum

class AblationVariable(str, Enum):
    MRL_DIMENSION = "mrl_dimension"
    DRIFT_FILTER = "drift_filter"
    MULTI_QUERY = "multi_query"
    HYDE = "hyde"
    LLM_RERANK = "llm_rerank"
    REPACK_STRATEGY = "repack_strategy"

class VariantConfig(BaseModel):
    """单个变体的配置"""
    name: str
    
    # 可覆盖的 Settings 参数
    dim: Optional[int] = None  # embedding_dim_fast_mode
    drift_filter_enabled: Optional[bool] = None
    query_fusion_enabled: Optional[bool] = None
    hyde_enabled: Optional[bool] = None
    llm_rerank_enabled: Optional[bool] = None
    repack_strategy: Optional[str] = None

class ExperimentConfig(BaseModel):
    """实验配置"""
    name: str
    description: str
    baseline: str  # "normal" or "fast"
    ablation_variable: AblationVariable
    variants: list[VariantConfig]
    include_normal_baseline: bool = False
    question_limit: int = 0  # 0 = all
    
    @field_validator('baseline')
    @classmethod
    def validate_baseline_for_mrl(cls, v, info):
        # MRL 消融必须使用 fast baseline
        if info.data.get('ablation_variable') == AblationVariable.MRL_DIMENSION:
            if v != 'fast':
                raise ValueError("MRL dimension ablation requires baseline='fast' (Normal mode does not support search_dim)")
        return v

class ExperimentDefaults(BaseModel):
    """默认配置"""
    questions_path: str
    corpus_dir: str
    chunks_manifest: str
    embedding_cache_dir: str
    top_k: int = 10
```

### 3.2 结果模型

```python
class QuestionResult(BaseModel):
    """单题结果（与现有 system_eval 格式兼容）"""
    key: str  # "{question_id}::{config}::topk={top_k}"
    question_id: str
    source: str
    config: str  # variant name
    fast_mode: bool
    dim: Optional[int] = None
    top_k: int
    question: str
    
    # 响应
    answer: Optional[str] = None
    citation_numbers: list[int] = []
    citation_range_ok: bool = False
    
    # Gold coverage（使用 _calc_gold_coverage 的定义）
    retrieved_chunk_ids: list[str] = []
    cited_chunk_ids: list[str] = []
    gold_chunk_ids: list[str] = []
    gold_metrics: dict[str, Any] = {}
    # gold_metrics 包含:
    # - gold_count: int
    # - retrieved_count: int
    # - gold_hit_any: bool
    # - gold_hit_all: bool
    # - gold_coverage: float
    # - gold_hit_ids: list[str]
    # - gold_miss_ids: list[str]
    
    # 详细评估（来自 session.latest_evaluation）
    evaluation: Optional[dict] = None
    
    # 时间和错误
    elapsed_s: float = 0.0
    error: Optional[str] = None
    ts: float = 0.0

class VariantMetrics(BaseModel):
    """变体汇总指标"""
    variant_name: str
    n: int
    
    # 质量指标
    cite_ok_rate: float
    gold_hit_any_rate: float
    gold_hit_all_rate: float
    avg_gold_coverage: float
    
    # 时间指标
    avg_latency_s: float
    p50_latency_s: float
    p95_latency_s: float

class ExperimentSummary(BaseModel):
    """实验汇总结果（用于可复现性）"""
    experiment_name: str
    description: str
    
    # 可复现性元数据
    questions_path: str
    limit: int
    top_k: int
    baseline: str
    ablation_variable: str
    variants: list[dict]
    
    # 时间
    started_at: str
    completed_at: Optional[str] = None
    
    # 统计
    total_questions: int
    completed_questions: int
    
    # 汇总指标
    variant_metrics: dict[str, VariantMetrics]
```

---

## 4. 核心实现

### 4.1 Session Flush（完整清理）

```python
# 必须复用 system_eval_fast_vs_normal.py 的完整清理逻辑

async def flush_session_for_next_question(session_id: str, settings: Settings) -> None:
    """
    完整清理 session 状态，确保题目之间互不干扰。
    
    必须清理:
    - chat_history: 避免历史对话影响
    - reference_ids: 避免引用编号累积
    - references: 避免引用列表累积
    - latest_evaluation: 避免评估记录污染
    """
    session = get_session(session_id=session_id, ttl_seconds=settings.session_ttl_seconds)
    if session is None:
        raise RuntimeError("session missing")
    async with session.lock:
        session.chat_history = []
        session.reference_ids = {}
        session.references = []
        session.latest_evaluation = None
```

### 4.2 Settings 克隆

```python
def clone_settings_for_variant(base: Settings, variant: VariantConfig, fast_mode: bool) -> Settings:
    """
    为变体创建 Settings 副本。
    
    注意: dim 参数只在 fast_mode=True 时生效！
    """
    updates = {}
    
    if variant.dim is not None:
        if not fast_mode:
            raise ValueError(f"dim={variant.dim} specified but fast_mode=False; MRL only works in Fast mode")
        updates["embedding_dim_fast_mode"] = variant.dim
        
    if variant.drift_filter_enabled is not None:
        updates["drift_filter_enabled"] = variant.drift_filter_enabled
        
    if variant.query_fusion_enabled is not None:
        updates["query_fusion_enabled"] = variant.query_fusion_enabled
        
    if variant.hyde_enabled is not None:
        updates["hyde_enabled"] = variant.hyde_enabled
        
    if variant.llm_rerank_enabled is not None:
        updates["llm_rerank_enabled"] = variant.llm_rerank_enabled
        
    if variant.repack_strategy is not None:
        updates["repack_strategy"] = variant.repack_strategy
    
    if hasattr(base, "model_copy"):
        return base.model_copy(update=updates)
    elif hasattr(base, "copy"):
        return base.copy(update=updates)
    else:
        # Fallback: 手动创建
        from backend.app.config import load_settings
        new_settings = load_settings()
        for k, v in updates.items():
            setattr(new_settings, k, v)
        return new_settings
```

### 4.3 指标计算

```python
def compute_cite_ok(answer: str, citations: list[dict]) -> bool:
    """
    使用 guardrails.py 的逻辑判断引用是否正确。
    """
    from backend.app.guardrails import STRICT_NO_MENTION, extract_citation_numbers
    
    if answer.strip() == STRICT_NO_MENTION:
        return True
    
    cited_nums = extract_citation_numbers(answer)
    if not cited_nums:
        return False
    
    if any(n < 1 or n > len(citations) for n in cited_nums):
        return False
    
    return True


def compute_gold_coverage(gold_ids: list[str], retrieved_ids: list[str]) -> dict:
    """
    复用 system_eval_fast_vs_normal.py 的 _calc_gold_coverage 定义。
    """
    gold_set = set(gold_ids)
    ret_set = set(retrieved_ids)
    inter = gold_set & ret_set
    
    return {
        "gold_count": len(gold_ids),
        "retrieved_count": len(retrieved_ids),
        "gold_hit_any": bool(inter),
        "gold_hit_all": bool(gold_set) and gold_set.issubset(ret_set),
        "gold_coverage": (len(inter) / len(gold_set)) if gold_set else 0.0,
        "gold_hit_ids": sorted(inter),
        "gold_miss_ids": sorted(gold_set - ret_set),
    }


def compute_variant_metrics(results: list[QuestionResult]) -> VariantMetrics:
    """计算变体的汇总指标"""
    import numpy as np
    
    n = len(results)
    if n == 0:
        return VariantMetrics(
            variant_name="",
            n=0,
            cite_ok_rate=0.0,
            gold_hit_any_rate=0.0,
            gold_hit_all_rate=0.0,
            avg_gold_coverage=0.0,
            avg_latency_s=0.0,
            p50_latency_s=0.0,
            p95_latency_s=0.0,
        )
    
    cite_ok_count = sum(1 for r in results if r.citation_range_ok)
    gold_hit_any_count = sum(1 for r in results if r.gold_metrics.get("gold_hit_any", False))
    gold_hit_all_count = sum(1 for r in results if r.gold_metrics.get("gold_hit_all", False))
    gold_coverages = [r.gold_metrics.get("gold_coverage", 0.0) for r in results]
    latencies = [r.elapsed_s for r in results if r.error is None]
    
    return VariantMetrics(
        variant_name=results[0].config,
        n=n,
        cite_ok_rate=cite_ok_count / n,
        gold_hit_any_rate=gold_hit_any_count / n,
        gold_hit_all_rate=gold_hit_all_count / n,
        avg_gold_coverage=sum(gold_coverages) / n,
        avg_latency_s=np.mean(latencies) if latencies else 0.0,
        p50_latency_s=float(np.percentile(latencies, 50)) if latencies else 0.0,
        p95_latency_s=float(np.percentile(latencies, 95)) if latencies else 0.0,
    )
```

---

## 5. CLI 接口

### 5.1 命令行参数

```bash
# 运行单个实验
python ablation_runner.py \
  --experiment mrl_dimension_ablation \
  --config experiments.yaml

# 限制题目数量（快速测试）
python ablation_runner.py \
  --experiment drift_filter_ablation \
  --limit 10

# 运行所有实验
python ablation_runner.py \
  --all \
  --config experiments.yaml

# 生成报告（从已有结果）
python ablation_report.py \
  --input experiments/mrl_dimension_ablation.jsonl \
  --output-md experiments/mrl_dimension_ablation.md \
  --output-charts experiments/mrl_dimension_ablation/charts/
```

### 5.2 进度日志格式

```
[ablation] Loading experiment: mrl_dimension_ablation
[ablation] Questions: 100, Variants: 6 (5 fast + 1 normal baseline)
[ablation] Resuming from 45 completed results

[ablation] Ingesting source=中华人民共和国民法典_20200528.docx
[ablation] Ingest OK (using cached embeddings)

[ablation] 46/600 config=fast_dim_128 id=q_001 elapsed=4.32s cite_ok=True gold_any=True ETA~45.2m
[ablation] 47/600 config=fast_dim_128 id=q_002 elapsed=4.15s cite_ok=True gold_any=True ETA~44.8m
...
[ablation] 600/600 config=normal id=q_100 elapsed=14.21s cite_ok=True gold_any=True

[ablation] DONE experiment=mrl_dimension_ablation elapsed=52.3m
[ablation] Results: experiments/mrl_dimension_ablation.jsonl
[ablation] Summary: experiments/mrl_dimension_ablation.json
[ablation] Report: experiments/mrl_dimension_ablation.md
```

---

## 6. 测试策略

### 6.1 测试框架

使用 `unittest`，与后端测试保持一致。

### 6.2 运行测试命令

```bash
# 运行所有消融框架测试
Research\ Files/rag_eval/.venv/bin/python -m unittest discover \
  -s Research\ Files/rag_eval/tests \
  -p "test_ablation_*.py"

# 运行单个测试文件
Research\ Files/rag_eval/.venv/bin/python -m unittest \
  Research\ Files/rag_eval/tests/test_ablation_config.py
```

### 6.3 测试用例

```python
# test_ablation_config.py
class TestAblationConfig(unittest.TestCase):
    def test_load_yaml_config(self):
        """测试 YAML 配置加载"""
        
    def test_mrl_requires_fast_baseline(self):
        """测试 MRL 消融必须使用 fast baseline"""
        
    def test_variant_generation(self):
        """测试变体生成"""
        
    def test_settings_clone(self):
        """测试 Settings 克隆"""

# test_ablation_runner.py
class TestAblationRunner(unittest.TestCase):
    def test_run_small_experiment(self):
        """测试小规模实验（5 题，2 变体）"""
        
    def test_resume_from_jsonl(self):
        """测试从 JSONL 恢复"""
        
    def test_session_flush(self):
        """测试 session 完整清理"""
        
    def test_metrics_extraction(self):
        """测试从 session.latest_evaluation 提取指标"""

# test_ablation_report.py
class TestAblationReport(unittest.TestCase):
    def test_markdown_generation(self):
        """测试 Markdown 报告生成"""
        
    def test_latex_table_generation(self):
        """测试 LaTeX 表格生成"""
        
    def test_chart_generation(self):
        """测试 matplotlib 图表生成"""
```

---

## 7. 文件结构

```
Research Files/rag_eval/
├── scripts/
│   ├── ablation_runner.py      # 主入口 CLI
│   ├── ablation_config.py      # 配置加载和验证
│   ├── ablation_report.py      # 报告生成
│   └── system_eval_fast_vs_normal.py  # 现有脚本（复用其核心逻辑）
├── tests/
│   ├── test_ablation_config.py
│   ├── test_ablation_runner.py
│   └── test_ablation_report.py
├── experiments/
│   ├── experiments.yaml        # 实验配置文件
│   ├── mrl_dimension_ablation.jsonl
│   ├── mrl_dimension_ablation.json
│   ├── mrl_dimension_ablation.md
│   └── mrl_dimension_ablation/
│       └── charts/
│           ├── cite_ok_bar.png
│           └── latency_line.png
├── embeddings/                 # 现有缓存目录
├── chunks/                     # 现有 chunks 目录
└── questions/                  # 现有题库目录
```

---

## 8. 安全与隐私

### 8.1 输出文件内容

实验输出文件包含：
- 完整问题文本
- 系统生成的回答
- 引用的 chunk 文本

### 8.2 使用限制

- **仅面向 `Research Files/rag_eval` 的研究语料**
- 输出文件不应提交到公开仓库
- `.gitignore` 已排除 `experiments/*.jsonl`

### 8.3 Phase 2 扩展

如需支持用户文档：
- 添加脱敏开关（移除 chunk 文本）
- 添加访问控制
