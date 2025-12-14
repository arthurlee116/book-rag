<p align="center">
  <img src="https://img.shields.io/badge/隐私-优先-green?style=for-the-badge" alt="隐私优先"/>
  <img src="https://img.shields.io/badge/RAG-混合检索-blue?style=for-the-badge" alt="混合 RAG"/>
  <img src="https://img.shields.io/badge/嵌入模型-Qwen3--8B-purple?style=for-the-badge" alt="Qwen3 嵌入"/>
</p>

<h1 align="center">📚 ERR — 临时 RAG 阅读器</h1>

<p align="center">
  <strong>隐私优先的文档问答系统，采用最先进的混合检索技术</strong>
</p>

<p align="center">
  上传文档 → 提出问题 → 获取带引用的答案<br/>
  <em>所有数据仅存于内存，不做任何持久化存储，您的数据完全属于您。</em>
</p>

<p align="center">
  <a href="README.md">English</a> | <strong>简体中文</strong>
</p>

---

## ✨ 功能特性

| 特性 | 描述 |
|------|------|
| 🔒 **隐私优先** | 所有处理均在内存中完成，支持 TTL 自动清理，无数据库，无持久化 |
| 🎯 **混合检索** | 结合 FAISS 向量搜索 + BM25 关键词匹配，实现更高召回率 |
| 🧠 **Qwen3-Embedding-8B** | MTEB 多语言排行榜第一的嵌入模型，支持 MRL（俄罗斯套娃表示学习） |
| 📝 **严格引用** | 每个答案都包含 `[1][2]` 格式的引用，链接到原文段落 |
| ⚡ **快速模式** | 可在准确性（完整流水线）和速度（MRL 1024 维搜索）之间切换 |
| 🌍 **100+ 语言** | 继承 Qwen3 的全面多语言支持 |
| 📄 **多格式支持** | 支持 `.txt`、`.md`、`.docx`、`.epub`、`.mobi` |

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                       前端 (Next.js 16)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │   上传   │  │   对话   │  │   日志   │  │    引用查看器    │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘ │
└───────┼─────────────┼─────────────┼─────────────────┼───────────┘
        │             │             │                 │
        ▼             ▼             ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                       后端 (FastAPI)                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   会话存储 (内存)                            ││
│  │  • 文本块 + 嵌入向量    • FAISS 索引    • BM25 索引         ││
│  │  • 对话历史             • TTL 清理                          ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│  ┌───────────────────────────┼───────────────────────────────┐  │
│  │                    检索流水线                              │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────────┐  │  │
│  │  │  HyDE   │→ │  多查询  │→ │  混合   │→ │  LLM 重排序  │  │  │
│  │  │         │  │   扩展   │  │  搜索   │  │   (可选)     │  │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └──────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   OpenRouter API    │
                    │  • 嵌入向量生成      │
                    │  • 对话补全          │
                    └─────────────────────┘
```

## 🚀 快速开始

### 环境要求

- **Git** — 版本控制工具
- **Python 3.11+** — 后端运行时
- **Node.js 20.9+** — 前端运行时（Next.js 16 要求）
- **OpenRouter API Key** — [点此获取](https://openrouter.ai/keys)

<details>
<summary>📥 <strong>新手？点击查看安装指南</strong></summary>

#### Git

| 平台 | 下载链接 |
|------|----------|
| Windows | [Git for Windows (64位)](https://github.com/git-for-windows/git/releases/download/v2.52.0.windows.1/Git-2.52.0-64-bit.exe) |
| macOS | 系统自带，或运行 `xcode-select --install` |
| Linux | `sudo apt install git` (Debian/Ubuntu) 或 `sudo dnf install git` (Fedora) |

📖 [Git 官方安装指南](https://git-scm.com/book/zh/v2/起步-安装-Git)

#### Python

| 平台 | 下载链接 |
|------|----------|
| Windows | [Python 3.13 (64位)](https://www.python.org/ftp/python/3.13.1/python-3.13.1-amd64.exe) |
| macOS | [Python 3.13 (.pkg)](https://www.python.org/ftp/python/3.13.1/python-3.13.1-macos11.pkg) |
| Linux | `sudo apt install python3.11` 或使用 [pyenv](https://github.com/pyenv/pyenv) |

📖 [Python 下载页面](https://www.python.org/downloads/)

> **提示：** Windows 安装时请勾选 "Add Python to PATH"。

#### Node.js

| 平台 | 下载链接 |
|------|----------|
| 全平台 | [Node.js 24 LTS 下载](https://nodejs.org/zh-cn/download) |

📖 推荐使用版本管理器：[nvm](https://github.com/nvm-sh/nvm) (macOS/Linux) 或 [nvm-windows](https://github.com/coreybutler/nvm-windows)

```bash
# 使用 nvm（安装后）
nvm install 24
nvm use 24
```

#### 验证安装

```bash
git --version    # 应显示 git version 2.x+
python --version # 应显示 Python 3.11+
node --version   # 应显示 v20.9.0+
npm --version    # 应显示 10.x+
```

</details>

### 方式一：Docker（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/book-rag.git
cd book-rag

# 2. 配置 API 密钥
cp backend/.env.example backend/.env
# 编辑 backend/.env，设置 OPENROUTER_API_KEY=你的密钥

# 3. 启动服务
docker compose up --build

# 4. 打开 http://localhost:3000
```

### 方式二：手动安装

**后端：**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# 编辑 .env，设置 OPENROUTER_API_KEY

uvicorn backend.app.main:app --reload --port 8000
```

**前端：**
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

打开 [http://localhost:3000](http://localhost:3000) 🎉

## 📖 工作原理

### 1. 文档处理

上传文档时：

1. **解析** — 从 `.txt`、`.md`、`.docx`、`.epub` 或 `.mobi` 中提取文本块
2. **分块** — 切分为约 512 token 的块，保留 50 token 重叠以保持上下文连贯
3. **嵌入** — 通过 OpenRouter 使用 Qwen3-Embedding-8B 生成 4096 维向量
4. **索引** — 在内存中构建 FAISS（向量）+ BM25（关键词）索引

### 2. 查询处理（标准模式）

```
用户查询
    │
    ├─→ 语言对齐（必要时翻译查询）
    │
    ├─→ 查询扩展
    │   ├─→ 生成 6 个查询变体（多查询）
    │   └─→ 生成假设性段落（HyDE）
    │
    ├─→ 嵌入所有变体（指令感知）
    │
    ├─→ 混合搜索（每个变体）
    │   ├─→ FAISS：按向量相似度取前 50
    │   └─→ BM25：按关键词匹配取前 50
    │
    ├─→ RRF 融合（合并所有排名）
    │
    ├─→ LLM 重排序（判断相关性）
    │
    ├─→ 重新打包（反向排序以优化注意力）
    │
    └─→ 生成答案（带引用）
```

### 3. 快速模式

开启"快速模式"以获得更快响应：

| 特性 | 标准模式 | 快速模式 |
|------|----------|----------|
| 搜索维度 | 4096 | 1024 (MRL) |
| 查询扩展 | ✅ 多查询 + HyDE | ❌ |
| LLM 重排序 | ✅ | ❌ |
| 重新打包 | ✅ 反向 | ❌ |
| 嵌入聚合 | 加权 | 简单平均 |

## ⚙️ 配置说明

所有配置项位于 `backend/.env`，主要选项：

```bash
# 模型配置
# 简单任务（翻译、HyDE、问答）- 使用轻量/快速模型
OPENROUTER_CHAT_MODEL_SIMPLE=google/gemini-2.5-flash-lite-preview-09-2025
# 复杂任务（多查询扩展、LLM 重排序）- 使用更强模型
OPENROUTER_CHAT_MODEL_COMPLEX=google/gemini-2.5-flash-preview-09-2025
OPENROUTER_EMBEDDING_MODEL=qwen/qwen3-embedding-8b

# 检索流水线
ERR_QUERY_FUSION_ENABLED=true      # 多查询扩展
ERR_HYDE_ENABLED=true              # 假设性文档嵌入
ERR_LLM_RERANK_ENABLED=true        # LLM 重排序
ERR_REPACK_STRATEGY=reverse        # 将最佳块放在查询附近

# 性能配置
ERR_EMBEDDING_DIM_FAST_MODE=1024   # 快速模式的 MRL 维度
ERR_SESSION_TTL_SECONDS=1800       # 会话超时（30 分钟）
```

> **注意：** `OPENROUTER_CHAT_MODEL` 已弃用。请使用 `OPENROUTER_CHAT_MODEL_SIMPLE` 和 `OPENROUTER_CHAT_MODEL_COMPLEX`。

完整配置请参阅 [`backend/.env.example`](backend/.env.example)。

## 🧪 测试

```bash
# 后端单元测试
cd backend
python -m unittest discover -s tests -p "test_*.py"

# 前端代码检查
cd frontend
npm run lint
```

## 📁 项目结构

```
book-rag/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 应用、路由、编排
│   │   ├── config.py            # 配置与环境变量加载
│   │   ├── openrouter_client.py # OpenRouter API 封装
│   │   ├── session_store.py     # 内存会话管理
│   │   ├── guardrails.py        # 引用强制执行
│   │   ├── ingestion/
│   │   │   ├── file_parser.py   # 文档解析
│   │   │   └── chunker.py       # 文本分块（带重叠）
│   │   └── retrieval/
│   │       └── hybrid_retriever.py  # FAISS + BM25 混合搜索
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/                     # Next.js App Router
│   ├── components/
│   │   ├── UploadPanel.tsx      # 文件上传界面
│   │   ├── ChatPanel.tsx        # 对话界面
│   │   └── TerminalWindow.tsx   # 处理日志
│   └── lib/
│       ├── store.ts             # Zustand 状态管理
│       └── types.ts             # TypeScript 类型定义
├── docker-compose.yml           # 开发环境
└── docker-compose.prod.yml      # 生产环境配置
```

## 🔬 技术亮点

### Qwen3-Embedding-8B

采用 **MTEB 多语言排行榜第一** 的模型（截至 2025 年 6 月得分 70.58）：

- **4096 维**（完整）或 **1024 维**（MRL 快速模式）
- **指令感知** — 查询使用任务特定提示，准确率提升 1-5%
- **100+ 语言**，包括代码
- **32K 上下文**，支持长文档

### 混合检索

结合两种方法的优势：

- **FAISS（稠密）** — 基于余弦距离的语义相似度
- **BM25（稀疏）** — 精确词项的关键词匹配
- **RRF 融合** — 倒数排名融合合并排名结果

### 隐私设计

- **无数据库** — 所有数据仅存于内存
- **TTL 清理** — 会话 30 分钟后自动过期
- **不记录内容** — 文档文本永不写入磁盘

## 🤝 参与贡献

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feat/amazing-feature`)
3. 使用 [约定式提交](https://www.conventionalcommits.org/zh-hans/) 提交代码 (`git commit -m 'feat: 添加新功能'`)
4. 推送并创建 PR

## 📄 许可证

[Apache 2.0](LICENSE)

---

<p align="center">
  使用 FastAPI、Next.js 和 Qwen3-Embedding 用 ❤️ 构建
</p>
