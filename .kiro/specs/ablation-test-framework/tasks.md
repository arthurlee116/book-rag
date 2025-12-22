# Implementation Tasks: ERR Ablation Test Framework

## Overview

实现一个 CLI 工具，用于对 ERR 系统的各个检索组件进行消融实验，评估不同配置对检索质量的影响。

## Notes

- 每完成一个主要任务，需更新 `Research Files/preparationProgress.md`
- MRL 消融必须使用 `baseline: fast`（Normal 模式不支持 `search_dim`）
- 必须复用 `system_eval_fast_vs_normal.py` 的摄入逻辑以保证 chunk_id 一致性
- 输出文件包含敏感内容，不应提交到公开仓库

## Tasks

- [x] 1. 创建配置模块
  - [x] 1.1 创建 `Research Files/rag_eval/scripts/ablation_config.py`
    - 实现 `AblationVariable` 枚举（mrl_dimension, drift_filter, multi_query, hyde, llm_rerank, repack_strategy）
    - 实现 `VariantConfig` 模型
    - 实现 `ExperimentConfig` 模型（含 MRL 必须使用 fast baseline 的验证）
    - 实现 `QuestionResult`、`VariantMetrics`、`ExperimentSummary` 模型
    - _Requirements: 1.1, 1.2, 1.3, 5.1_
  - [x] 1.2 实现 YAML 配置加载
    - 实现 `load_experiment_config(yaml_path, experiment_name)` 函数
    - 实现配置验证和默认值合并
    - _Requirements: 1.4_
  - [x] 1.3 创建预设配置文件 `Research Files/rag_eval/experiments/experiments.yaml`
    - 添加 MRL 维度消融预设（baseline: fast，variants: 128/256/512/1024/2048）
    - 添加 Drift Filter、HyDE、Multi-Query、LLM Rerank、Repack 策略消融预设
    - _Requirements: 1.3, 2.1, 2.2_

- [x] 2. 实现核心运行器
  - [x] 2.1 创建 `Research Files/rag_eval/scripts/ablation_runner.py` 基础结构
    - 实现 `AblationRunner.__init__(config, settings, client)`
    - 实现 `_load_questions(path, limit)` 方法（固定顺序取前 N 条）
    - 实现 `_generate_variants()` 和 `_load_existing_keys(jsonl_path)` 方法
    - _Requirements: 2.1, 2.3, 2.4, 3.5_
  - [x] 2.2 复用现有摄入逻辑
    - 复用 `system_eval_fast_vs_normal.py` 的 `_ingest_one()` 路径
    - 复用 `try_load_cached_embeddings()`、`embed_chunks_and_cache()` 等函数
    - _Requirements: 8.2_
  - [x] 2.3 实现 Settings 克隆
    - 实现 `_clone_settings_for_variant(base, variant, fast_mode)` 方法
    - 支持覆盖 embedding_dim_fast_mode、drift_filter_enabled 等参数
    - _Requirements: 1.1, 2.4_
  - [x] 2.4 实现完整 Session Flush
    - 实现 `flush_session_for_next_question(session_id, settings)` 方法
    - 必须清理 chat_history、reference_ids、references、latest_evaluation 四个字段
    - _Requirements: 8.4_
  - [x] 2.5 实现实验执行循环
    - 实现 `run()` 异步方法
    - 对每个变体、每个题目执行：flush → clone settings → chat() → 获取 metrics → 写入 JSONL
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 8.1_
  - [x] 2.6 实现指标计算
    - 复用 `_calc_gold_coverage()` 函数
    - 实现 `compute_cite_ok()` 和 `compute_variant_metrics()` 方法
    - 计算 p50/p95 延迟
    - _Requirements: 6.1_

- [x] 3. 实现 CLI 入口
  - [x] 3.1 创建 argparse CLI
    - 在 `ablation_runner.py` 添加 `main()` 函数
    - 支持 --config、--experiment、--all、--limit、--resume、--out-dir 参数
    - _Requirements: 3.5_
  - [x] 3.2 实现进度日志
    - 每题完成后打印进度信息
    - 实验开始时打印配置摘要，完成后打印汇总
    - _Requirements: 3.1, 3.2, 3.3_

- [x] 4. 实现报告生成
  - [x] 4.1 创建 `Research Files/rag_eval/scripts/ablation_report.py`
    - 实现 `ReportGenerator` 类
  - [x] 4.2 实现 Markdown 报告
    - 实现 `generate_markdown(jsonl_path, output_path)` 方法
    - 包含实验概述、配置说明、汇总表格、详细指标
    - _Requirements: 6.1, 6.2_
  - [x] 4.3 实现 LaTeX 表格和 CSV 导出
    - 实现 `generate_latex_table()` 和 `generate_csv()` 方法
    - _Requirements: 6.3_
  - [x] 4.4 实现图表生成
    - 使用 matplotlib 实现 `generate_charts(jsonl_path, output_dir)` 方法
    - 支持柱状图、折线图、散点图，导出 PNG/SVG/PDF
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 5. 实现成本预估
  - [x] 5.1 创建静态成本估算器
    - 在 `ablation_config.py` 添加 `CostEstimator` 类
    - 定义平均 tokens/call 和模型价格常量
  - [x] 5.2 实现预估逻辑
    - 实现 `estimate(config)` 方法
    - 基于题目数 × 变体数 × 平均 tokens/call × 价格计算
    - 明确标注"仅供参考"
    - _Requirements: 4.1, 4.2_

- [x] 6. 实现错误处理
  - [x] 6.1 API 调用重试
    - 实现指数退避重试（最多 3 次）
    - _Requirements: 9.1_
  - [x] 6.2 单题失败处理
    - 捕获异常，记录错误到 JSONL，继续下一题
    - _Requirements: 9.2_
  - [x] 6.3 Resume 机制
    - 读取已有 JSONL，跳过已完成的组合
    - _Requirements: 9.3_
  - [x] 6.4 API Key 检测
    - 检测无效/限流的 API Key，打印明确错误信息
    - _Requirements: 9.4_

- [x] 7. 测试
  - [x] 7.1 单元测试 - 配置模块
    - 创建 `Research Files/rag_eval/tests/test_ablation_config.py`
    - 测试 YAML 加载、MRL 验证、变体生成、Settings 克隆
  - [x] 7.2 单元测试 - 运行器
    - 创建 `Research Files/rag_eval/tests/test_ablation_runner.py`
    - 测试 session flush、指标计算、resume 功能
  - [x] 7.3 单元测试 - 报告
    - 创建 `Research Files/rag_eval/tests/test_ablation_report.py`
    - 测试 Markdown、LaTeX、图表生成

- [x] 8. Checkpoint - 运行完整测试
  - 运行所有测试确保通过
  - 如有问题，询问用户

- [x] 9. 文档更新
  - [x] 9.1 更新 README
    - 在 `Research Files/rag_eval/README.md` 添加消融实验部分
    - 文档化 CLI 用法和 YAML 配置格式
  - [x] 9.2 更新进度文档
    - 更新 `Research Files/preparationProgress.md`
    - 标记完成的待办事项
