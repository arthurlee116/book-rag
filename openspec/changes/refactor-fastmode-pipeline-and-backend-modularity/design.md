## Context
本次变更同时触及架构边界、检索热路径与依赖栈：
- 架构：`main.py` 过度集中导致维护成本高。
- 性能：fast mode 的 MRL 检索与候选策略存在可优化空间。
- 检索策略：HyDE 分支重复词法检索、normal mode 固定语言对齐造成额外开销。
- 依赖：`rank-bm25` 与 spaCy 英文分词组合在大规模语料扩展时性价比较低。

## Goals / Non-Goals

### Goals
- 完成你指定的全部修复项并保持 API 契约稳定。
- 将后端编排逻辑拆分为更清晰的模块边界。
- 让 fast mode 更贴近“低延迟优先”的真实目标。
- 提高 ingest 与 LLM 输出解析的故障可恢复性。
- 建立可回归验证的测试覆盖。

### Non-Goals
- 不新增业务功能。
- 不改变前端交互协议。
- 不引入数据库持久化。

## Decisions

### Decision 1: 模块拆分策略
- `routes.py` 负责 HTTP 层与依赖注入。
- `chat_pipeline.py` 负责纯业务编排（检索、重排、上下文组装、回答生成）。
- `ingestion_pipeline.py` 负责上传后的解析/分块/建索引。
- `main.py` 仅保留 app 生命周期和路由注册。

**Rationale**
- 降低单文件认知负担。
- 便于独立测试 pipeline。
- 减少未来功能扩展的耦合风险。

### Decision 2: MRL 搜索改为 FAISS 路径
- 在 retriever 内新增 MRL 维度 FAISS index 缓存。
- fast mode 使用 `IndexFlatIP` + 截断后归一化向量。

**Rationale**
- 保留 MRL 正确性前提下，提高大文档检索吞吐。
- 避免每次请求全量矩阵乘法。

### Decision 3: HyDE 检索改为 vector-only
- HyDE 分支关闭 BM25 计算，仅作为向量召回增强。

**Rationale**
- HyDE 本质是 dense retrieval recall 扩展。
- 避免同 query 的重复词法检索开销。

### Decision 4: fast mode 聚合与重排
- fast mode query embedding 采用加权聚合（非简单平均），原始 query 权重更高。
- fast mode 执行 re-pack（默认 reverse），因为其开销近似 O(n) 且非常低。

**Rationale**
- 平衡跨语言/翻译变体带来的语义偏移。
- 提升模型对关键片段位置关注的一致性。

### Decision 5: BM25 后端迁移与英文轻量分词
- 使用 `bm25s` 替代 `rank-bm25`。
- 英文分词改为轻量正则 tokenizer，不再依赖 spaCy 热路径。
- 中文继续 `jieba`。

**Rationale**
- 性能可扩展性更好。
- 减少热路径 CPU 与初始化成本。

### Decision 6: 语言对齐触发条件
- 改为“仅跨语言或配置强制时触发”。

**Rationale**
- 避免 normal mode 的固定 LLM 成本。
- 对同语言 query 保持低延迟。

## Alternatives Considered
1. 保持 `main.py` 不拆分，仅提取少量 helper。
- 否决：无法根治职责耦合和测试困难。

2. MRL 保持 numpy 乘法，仅调整 candidate_k。
- 否决：大文档下吞吐增长受限。

3. 继续使用 `rank-bm25` + spaCy。
- 否决：扩展时性能与资源开销不理想。

## Risks / Trade-offs
- bm25 实现迁移后，边界排序可能微小变化。
  - Mitigation: 增加行为回归测试，控制 top-k 输出稳定性。
- 模块拆分引入导入路径变更。
  - Mitigation: 保持 API 层行为稳定并更新测试导入。
- fast mode 结果排序会因 re-pack 变化。
  - Mitigation: 通过配置可控并记录变更说明。

## Migration Plan
1. 先落地 OpenSpec 文档并校验。
2. 新建 pipeline 模块并迁移逻辑（保持行为等价）。
3. 实施性能改造（MRL FAISS、HyDE vector-only、candidate_k override、conditional align）。
4. 迁移 BM25 + tokenizer，更新依赖。
5. 补齐测试与验证。
6. 提交、推送、部署并监控。

## Rollback Plan
- 若上线出现异常：
  1. 回滚到变更前 commit。
  2. 恢复旧依赖版本（`rank-bm25` 路径）。
  3. 重启生产容器并校验 `/backend/health`。

## Open Questions
- 无阻塞性 open question。按当前约束直接落地实现。
