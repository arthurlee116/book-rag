# CLAUDE.md — ERR (Ephemeral RAG Reader)

本文件为 AI 编程助手提供项目上下文。读者对本项目一无所知，请据此理解。

## 项目概述

ERR（Ephemeral RAG Reader）是一个隐私优先的文档问答应用，采用混合检索（Hybrid RAG）架构。用户上传文档后可提问并获得带引用的回答。所有处理均在内存中完成，无数据库、无持久化，会话自动过期清理。

- 线上地址：https://bookembed.net
- 全栈单仓库：后端 FastAPI (Python 3.12) + 前端 React 18 (TypeScript 5)
- 代码为英文，文档中英双语

## 技术栈

### 后端 (`/backend/`)
- FastAPI + Uvicorn（开发模式自动重载）
- `faiss-cpu` — 向量相似度搜索（FAISS）
- `bm25s` — BM25 关键词检索
- `spacy` + `jieba` — NLP 分词（英文/中文）
- `ebooklib` + `python-docx` + `beautifulsoup4` — 文档解析（.txt, .md, .docx, .epub, .mobi）
- `httpx` + `tenacity` — HTTP 客户端（带重试）
- `sse-starlette` — Server-Sent Events 实时日志流
- `sentence-transformers` + `torch` — 本地语义分块（可选）
- 外部 API：OpenRouter（嵌入模型 + 聊天模型）

### 前端 (`/frontend/`)
- React 18 + TypeScript 5 + Vite 8
- Ant Design 5（UI 组件库）
- Zustand 5（状态管理）
- Less（CSS 预处理器）
- ESLint 9 + typescript-eslint

### DevOps
- Docker + Docker Compose（开发 & 生产）
- Caddy（生产环境反向代理，自动 HTTPS）
- GitHub Actions（推送 main 分支自动部署）
- 服务器：腾讯云（香港），Ubuntu 24.04

## 项目结构

```
book-rag/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口，lifespan 管理，CORS，会话清理循环
│   │   ├── config.py               # Settings 类（40+ 配置项），自定义 .env 加载器
│   │   ├── routes.py               # API 端点：/upload, /chat, /api/logs, /evaluation, /export
│   │   ├── deps.py                 # FastAPI 依赖注入（settings, openrouter）
│   │   ├── openrouter_client.py    # OpenRouter API 封装（嵌入、聊天、翻译、多查询、HyDE、重排序）
│   │   ├── session_store.py        # 内存会话管理 + TTL 自动过期
│   │   ├── chat_pipeline.py        # RAG 聊天编排（查询扩展、检索、上下文构建、回答生成）
│   │   ├── ingestion_pipeline.py   # 文档摄入流水线（解析→分块→嵌入→建索引）
│   │   ├── guardrails.py           # 引用强制执行（必须包含 [n] 引用）
│   │   ├── repacking.py            # 上下文重排策略（reverse/forward）
│   │   ├── ingestion/
│   │   │   ├── file_parser.py      # 文件解析：.txt, .md, .docx, .epub, .mobi
│   │   │   └── chunker.py          # 基于 token 的分块（512 token，50 overlap），可选语义分块
│   │   ├── models/
│   │   │   └── chunk.py            # ChunkModel（Pydantic）
│   │   └── retrieval/
│   │       ├── hybrid_retriever.py # FAISS + BM25 混合检索，MRL 快速模式
│   │       ├── fusion.py           # RRF（Reciprocal Rank Fusion）
│   │       └── evaluation.py       # 检索评估指标记录
│   ├── tests/                      # 13 个单元测试文件（unittest 框架）
│   ├── requirements.txt            # 直接依赖
│   ├── constraints.txt             # 锁定版本
│   ├── Dockerfile                  # Python 3.12-slim
│   └── .env.example                # 配置模板（40+ 选项）
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # 主应用（响应式布局，懒加载面板）
│   │   ├── main.tsx                # 入口
│   │   ├── theme.ts                # Ant Design 暗色主题
│   │   ├── index.less              # 全局样式
│   │   ├── components/
│   │   │   ├── HeroSection.tsx     # 落地页
│   │   │   ├── UploadPanel.tsx     # 文件上传（拖拽）
│   │   │   ├── ChatPanel.tsx       # 聊天界面
│   │   │   ├── DocumentPanel.tsx   # 文档/分块查看器
│   │   │   ├── TerminalWindow.tsx  # 日志流显示（SSE）
│   │   │   └── EvaluationPanel.tsx # 检索评估可视化
│   │   └── lib/
│   │       ├── store.ts            # Zustand 全局状态
│   │       └── types.ts            # TypeScript 类型定义
│   ├── vite.config.ts              # Vite 配置（代理 /backend → 后端）
│   ├── tsconfig.json               # strict: true, @/ 别名
│   ├── eslint.config.js            # ESLint 9 flat config
│   ├── Dockerfile                  # 开发用
│   └── Dockerfile.prod             # 多阶段生产构建（serve 静态文件）
├── docker-compose.yml              # 开发编排
├── docker-compose.prod.yml         # 生产编排
└── .github/workflows/deploy.yml    # CI/CD 流水线
```

## 构建与运行

### 开发环境（Docker，推荐）

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env 设置 OPENROUTER_API_KEY

docker compose up --build
# 前端：http://localhost:3000
# 后端：http://localhost:8000
```

### 开发环境（手动）

```bash
# 后端
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -c constraints.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install --legacy-peer-deps
npm run dev
```

### 生产部署

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

**重要**：后端必须使用 `UVICORN_WORKERS=1`，因为会话和摄入状态存储在内存中。多 worker 会导致内存分裂，破坏会话流程。

## 测试

### 后端单元测试

```bash
# 从仓库根目录
python -m unittest discover -s backend/tests -p "test_*.py"

# 或从 backend 目录
cd backend && python -m unittest discover -s tests -p "test_*.py"
```

测试使用 Python `unittest` 框架，覆盖：分块、配置一致性、嵌入衰减、评估、引用护栏、混合检索、摄入流水线、OpenRouter JSON 提取、重试策略、重排策略、检索模块导入。

### 前端检查

```bash
cd frontend
npm run lint                  # ESLint
npm run build                 # TypeScript 编译 + Vite 构建
npm run test:code-splitting   # 验证代码分割
npm run bench:tbt             # Lighthouse 性能基准
```

### CI/CD

GitHub Actions（`.github/workflows/deploy.yml`）在推送 main 分支时：
1. 前端 lint + build
2. 后端单元测试
3. SSH 部署到生产服务器
4. 健康检查

所需 Secrets：`DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`

## 代码风格

### Python（后端）
- 所有文件顶部使用 `from __future__ import annotations`
- 完整类型注解（函数参数、返回值）
- 导入分组：标准库 → 第三方 → 本地模块
- I/O 操作使用 `async`/`await`
- CPU 密集操作使用 `loop.run_in_executor`
- 异常处理使用 `# noqa: BLE001` 标记宽泛捕获

### TypeScript（前端）
- 严格模式（`strict: true`）
- `@/` 别名用于 src 相对导入
- 函数式组件
- Zustand 管理全局状态，React hooks 管理局部状态
- Less 用于全局样式，内联样式用于动态值
- 未使用变量/参数会报错（`noUnusedLocals`, `noUnusedParameters`）
- 未使用参数以 `_` 前缀命名（`argsIgnorePattern: "^_"`）

## 核心架构决策

### 内存架构
- 无数据库，所有会话数据存储在 Python 进程内存中（`SESSIONS` 全局字典）
- 会话 TTL 默认 30 分钟，后台每 30 秒清理过期会话
- 进程重启清除所有数据
- 单 worker 部署

### 混合检索流水线（Normal 模式）
1. **语言对齐** — 检测文档语言，必要时翻译查询
2. **HyDE** — 生成假设性回答用于查询扩展
3. **多查询扩展** — 生成 6-8 个查询变体
4. **漂移过滤** — 过滤与原始查询偏离过大的变体
5. **混合搜索** — FAISS（向量）+ BM25（关键词）并行检索
6. **RRF 融合** — Reciprocal Rank Fusion 合并结果
7. **LLM 重排序** — 使用 LLM 做 yes/no 相关性判断（可选）
8. **上下文重排** — 反转顺序（最相关的放在末尾，靠近查询）

### Fast 模式 vs Normal 模式
- Fast 模式：MRL 1024 维嵌入，跳过部分流水线步骤，更低延迟
- Normal 模式：完整 4096 维嵌入，完整流水线，更高精度
- 前端 UI 开关控制

### 引用强制
- 每个回答必须包含 `[1][2]` 格式的引用
- 引用编号必须在有效范围内（1..context_size）
- 无法引用时返回固定回复："The document does not mention this."

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/upload` | POST | 上传文档（multipart/form-data），通过 `X-Session-Id` 头传递会话 ID |
| `/api/logs/{session_id}` | GET | SSE 实时日志流 |
| `/chat` | POST | RAG 问答（JSON body: `session_id`, `question`, `top_k`, `fast_mode`） |
| `/evaluation` | GET | 获取检索评估指标（`X-Session-Id` 头） |
| `/export/{session_id}` | GET | 导出聊天记录为 Markdown（含引用附录） |

## 配置

所有后端配置通过环境变量设置，`config.py` 中有自定义 `.env` 加载器（无第三方依赖）。

**必需**：
```bash
OPENROUTER_API_KEY=your_key_here
```

**环境变量前缀规则**：
- `OPENROUTER_*` — OpenRouter API 相关（模型、密钥、URL）
- `ERR_*` — 应用配置（分块、检索、会话、快速模式等）

完整配置项见 `backend/.env.example`（40+ 选项）。

## 安全注意事项

- API 密钥存储在 `.env` 文件中（已在 `.gitignore` 中排除）
- 开发环境 CORS 限制为 `localhost:3000`
- 会话 ID 为 UUID v4，通过 `X-Session-Id` 请求头传递
- 无文档持久化，所有数据仅在内存中处理
- 生产环境通过 Caddy 自动 HTTPS（Let's Encrypt）

## 常见开发任务

### 添加新端点
1. 在 `backend/app/routes.py` 添加路由
2. 如需新数据模型，在 `backend/app/models/` 添加
3. 在 `backend/tests/` 添加测试
4. 前端通过 store 或组件调用

### 添加新前端组件
1. 在 `frontend/src/components/` 创建组件
2. 如需代码分割，在 `App.tsx` 中使用 `React.lazy` 导入
3. 使用 Zustand store 管理跨组件共享状态

### 修改配置项
1. 在 `backend/app/config.py` 的 `Settings` 类添加字段
2. 在 `load_settings()` 中添加环境变量加载逻辑
3. 更新 `backend/.env.example`
4. 在 `test_config_defaults_consistency.py` 添加测试

## 外部依赖

- **OpenRouter**：所有 LLM/嵌入操作必需，需有效 API Key
- **Hugging Face**：语义分块启用时下载 sentence-transformer 模型（可选）
- **PyPI 镜像**：Docker 构建默认使用清华镜像（`pypi.tuna.tsinghua.edu.cn`），适配中国网络环境
- **Docker 镜像**：默认使用 DaoCloud 镜像（`docker.m.daocloud.io`）

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| `OPENROUTER_API_KEY is not set` | 从 `.env.example` 创建 `backend/.env` 并填入 API Key |
| 端口被占用 | 修改 `--port` 参数或更新 `VITE_BACKEND_URL` |
| FAISS 导入错误 | 确保安装了 `libgomp1`（Dockerfile 中已包含） |
| 前端无法连接后端 | 检查 `VITE_BACKEND_URL` 和 CORS 设置 |
| 刷新后会话丢失 | 预期行为——会话仅存储在内存中 |
