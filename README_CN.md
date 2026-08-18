# Financial RAG Assistant

**生产级 AI 金融研究助手**

AI 驱动的金融研究助手，通过 Agentic RAG、混合检索和带引用的生成能力，帮助金融分析师分析文档。上传财报 PDF，提出研究问题，获取带源引用的答案 — 一站式平台。

[![CI](https://github.com/csl1234213/financial-rag-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/csl1234213/financial-rag-assistant/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-24-2496ED)](https://www.docker.com/)
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen)](https://github.com/csl1234213/financial-rag-assistant)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 产品概述

### 解决什么问题

金融分析师花费数小时阅读季度财报、10-K 年报和盈利电话会议记录，从中提取关键洞察。传统关键词搜索无法理解上下文，通用 LLM 聊天工具在没有源文档支撑的情况下容易产生幻觉。

Financial RAG Assistant 通过以下方式解决这些问题：

- **Agentic RAG** — AI Agent 规划研究工作流、检索相关证据、生成带引用的答案
- **混合检索** — 结合语义理解与关键词匹配，实现精准文档搜索
- **带引用的生成** — 每一条声明都可追溯到源文档，附带相似度分数
- **多租户隔离** — 团队和组织的安全数据分离

### 目标用户

- **金融分析师** — 研究公司、比较业绩、分析趋势
- **投资团队** — 带租户隔离的共享知识工作空间
- **AI 工程师** — 生产级 RAG 系统的参考架构

### 核心价值

> 将非结构化的金融文档转化为可查询的研究助手 — 提供可信任的证据。

---

## 演示工作流

1. **注册** 账号 → 自动创建租户工作空间
2. **上传** 财报 PDF → 后台 Worker 自动处理文档
3. **提问** 金融问题 → Agent 规划研究工作流
4. **获取** 带引用的答案 → 每条声明可追溯到源文档

```
注册 → 上传 PDF → Worker 处理 → 提问 → 带引用的答案
```

---

## 功能特性

### 🤖 AI 研究 Agent

智能 Agent 理解金融查询并执行多步骤研究工作流。

- **意图分析器** — 自动分类查询：直接对话 / 单公司分析 / 公司对比 / 全局研究
- **查询规划器** — 生成带依赖解析的结构化执行计划
- **Agent Runtime** — 全生命周期编排：意图 → 规划 → 工作流 → 执行
- **多策略执行** — RAG、直接 LLM、并行、多步骤、工具调用等策略

### 📚 知识工作空间

上传、索引和管理金融文档，完整的文档生命周期。

- **PDF 上传** — 拖拽上传财报，自动处理
- **文档索引** — 使用 sentence-transformers 自动分块和嵌入
- **分块浏览器** — 浏览和检查文档分块及其元数据
- **向量存储** — 持久化 ChromaDB 向量数据库，支持混合搜索

### 🔎 检索调试台

交互式工具调试和分析检索质量。

- **混合搜索** — 语义 + 关键词检索，可配置权重
- **相似度评分** — 每个检索到的分块透明展示相关性分数
- **检索调试** — 检查查询嵌入、搜索结果和排名

### 📑 引用系统

每项研究输出都可追溯到源文档。

- **证据追踪** — 每条声明链接到特定文档分块
- **源引用** — 完整来源标注，包含文档名和页面上下文
- **置信度分数** — 每个引用基于相似度的置信度

---

## 生产特性

| 特性 | 实现 |
|---------|---------------|
| **多租户安全** | JWT 认证 + 租户隔离（数据、向量、任务） |
| **异步任务处理** | Redis Streams + Worker Pool（水平扩展、自动重试、心跳检测） |
| **向量搜索** | ChromaDB + 混合检索（语义 + 关键词） |
| **AI 生成** | LLM Provider 抽象层（DeepSeek / Gemini / Claude） |
| **Agent Runtime** | 意图分析器 → 查询规划器 → 策略引擎 → 工作流执行器 |
| **部署** | Docker Compose（5 个服务：frontend, backend, worker, redis, chromadb） |
| **CI/CD** | GitHub Actions（lint, type check, test, build） |
| **API 文档** | 自动生成 OpenAPI（Swagger UI） |

---

## 系统架构

```
                    ┌─────────────────┐
                    │      用户       │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  React 前端      │  (Vite + TypeScript + Nginx)
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  FastAPI 网关    │  (REST API + JWT 认证)
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Agent Runtime   │
                    ├─────────────────┤
                    │ 意图分析器       │
                    │ 查询规划器       │
                    │ 策略引擎         │
                    │ 工作流执行器     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ 混合检索器       │  (语义 + 关键词)
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
            ┌──────────────┐  ┌──────────────┐
            │  ChromaDB     │  │  LLM Provider │
            │  (向量数据库)  │  │  (DeepSeek)   │
            └──────────────┘  └──────────────┘
```

### 异步任务管道

```
PDF 上传
    │
    ▼
任务数据库 (SQLite)
    │
    ▼
Redis Streams (消息队列)
    │
    ▼
Worker Pool (水平扩展)
    │
    ▼
文档处理 → 嵌入 → 向量存储 (ChromaDB)
```

### 基础设施

```
┌──────────────────────────────────────────────────────┐
│                    Docker Compose                     │
├──────────┬──────────┬──────────┬──────────┬──────────┤
│ 前端     │ 后端     │ Worker   │ ChromaDB │  Redis   │
│ (Nginx)  │(FastAPI) │  (x N)   │ (向量库) │ (队列)   │
│ :3000    │ :8000    │          │ :8001    │ :6379    │
└──────────┴──────────┴──────────┴──────────┴──────────┘
```

---

## 支持的 LLM 提供商

| 提供商 | 状态 | 说明 |
|----------|--------|-------------|
| DeepSeek | 生产环境 | 通过 ProviderFactory 作为主提供商 |
| Gemini | 已支持 | 已在 ProviderRegistry 注册 |
| Claude | 已预留 | Provider 适配器已就绪 |

---

## 演示

### 截图

| 聊天界面 | 知识工作空间 |
|:---:|:---:|
| ![Chat](docs/demo/screenshots/docker-startup.png) | ![Knowledge](docs/demo/screenshots/health-api.png) |

| 检索调试台 | Swagger API |
|:---:|:---:|
| ![Retrieval](docs/demo/screenshots/streamlit-rag.png) | ![Swagger](docs/demo/screenshots/swagger-rag.png) |

### API 演示

**直接对话** — 非研究类查询路由到直接 LLM 对话：

```json
// POST /api/v1/chat
{ "question": "什么是 AI？", "stream": false }

// 响应
{
  "workflow": { "type": "direct_chat" },
  "reasoning": { "intent": "DIRECT_CHAT", "evidence_count": 0 },
  "execution": { "strategy": "direct_llm", "use_retrieval": false },
  "report": "人工智能（AI）是..."
}
```

**金融 RAG 研究** — 带证据和引用的研究：

```json
// POST /api/v1/chat
{ "question": "分析特斯拉的收入增长", "stream": false }

// 响应
{
  "workflow": { "type": "rag" },
  "reasoning": { "intent": "SINGLE_COMPANY", "companies": ["特斯拉"], "evidence_count": 4 },
  "execution": { "strategy": "rag", "use_retrieval": true },
  "citations": [
    { "source": "Tesla_Q2_2025.pdf", "similarity": 0.97, "preview": "总收入..." },
    { "source": "Tesla_Q2_2025.pdf", "similarity": 0.92, "preview": "汽车业务收入..." }
  ],
  "report": "# 研究报告\n\n## 摘要\n..."
}
```

---

## 快速开始

### 前置条件

- Docker >= 24
- Docker Compose >= 2

### 一行命令启动

```bash
# 1. 克隆仓库
git clone https://github.com/csl1234213/financial-rag-assistant.git
cd financial-rag-assistant

# 2. 配置（设置你的 DEEPSEEK_API_KEY）
cp .env.example .env

# 3. 启动
docker compose up -d
```

### 访问地址

| 服务 | URL |
|---------|-----|
| 前端 | http://localhost:3000 |
| API 文档 (Swagger) | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/api/v1/health |

> 首次运行自动初始化演示知识库，包含金融 PDF（特斯拉、NVIDIA、苹果）。后续运行跳过初始化（幂等）。数据持久化在 Docker 命名卷中。

---

## 配置

所有配置通过 `.env` 文件管理。复制 `.env.example` 并填入你的值。

| 变量 | 说明 | 默认值 |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM 提供商：`deepseek`、`gemini`、`claude` | `deepseek` |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | *(必填)* |
| `LLM_MODEL` | 所选提供商的模型名称 | `deepseek-v4-flash` |
| `CHROMA_HOST` | ChromaDB 服务主机名 | `chromadb` |
| `CHROMA_PORT` | ChromaDB 服务端口 | `8000` |
| `DATABASE_URL` | SQLite 数据库路径 | `sqlite:///./data/financial_rag.db` |
| `VITE_API_BASE_URL` | 前端 API 基础 URL | `/api` |
| `VITE_ENABLE_MOCK` | 启用 mock API 响应 | `false` |

完整可配置选项列表请参见 [`.env.example`](.env.example)。

---

## 开发

### 后端 (FastAPI)

```bash
pip install -r requirements.txt
uvicorn api.app:app --reload --port 8000
```

### 前端 (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

### 测试

```bash
pytest
```

### CI/CD

GitHub Actions 在每次 push 和 PR 时运行：
- 代码检查（flake8, ruff）
- 类型检查（mypy）
- 测试套件（pytest）
- 前端构建（npm run build）

---

## 路线图

- [x] Agent Runtime — 意图路由、规划、执行
- [x] 混合检索 — 语义 + 关键词搜索
- [x] 引用系统 — 证据追踪与源标注
- [x] 知识工作空间 — PDF 上传、索引、分块管理
- [x] React 前端 — 聊天、知识库、检索页面
- [x] Docker 部署 — 一行命令生产启动
- [x] 多用户认证 — JWT + 租户隔离
- [x] 异步任务管道 — Redis Streams + Worker Pool
- [ ] 云部署（AWS/GCP）
- [ ] 金融数据 API 集成（SEC EDGAR, Yahoo Finance）
- [ ] 流式聊天响应

---

## 系统演进

```
V1     → PDF 问答原型
V2     → 多文档 RAG
V2.2   → 稳定架构
V3.0   → Agent Runtime 版
V4.0   → 生产架构
V7.3.1 → Agent Runtime 框架
V7.3.2 → Docker 生产打包
V7.3.3 → 演示知识库初始化
V8.1.0 → 多租户 + 异步任务管道
V8.2.0 → Financial AI Copilot 发布对齐
```

---

## 核心工程亮点

### Agent Runtime 架构

完整的 Agent Runtime，包含查询规划、双执行引擎（策略分发 + 步骤分发）、运行时上下文、结构化推理（事实 / 风险 / 机遇）、可解释证据管道。

### LLM Provider 抽象层

工厂模式：`ProviderFactory.create(config)` → `ProviderRegistry.get(name)` → `BaseProvider.chat()`。SDK 调用与业务逻辑清晰分离。DeepSeek（生产）、Gemini（已支持）、Claude（已预留）。

### 可插拔运行时能力

Memory、Metrics、Reliability、Tracing、Tool Calling 已完整实现，注入引擎实例即可激活。未提供引擎时 Runtime 优雅降级。

### 基于证据的输出

每条答案可追溯到源文档：答案 → 证据 → 源文档 → 推理链路。

### 多租户数据隔离

基于 JWT 的认证，自动绑定租户。文档、向量嵌入和任务均按租户隔离。完整隔离性已通过 E2E 测试套件验证。

### 异步任务处理

Redis Streams 消息队列，支持 Consumer Group 和 Worker Pool。支持水平扩展、自动重试、心跳监控和过期任务恢复。

---

## 文档

| 文档 | 说明 |
|----------|-------------|
| [系统架构](docs/ARCHITECTURE.md) | 详细架构、多租户安全、异步任务系统 |
| [系统设计（面试）](docs/interview/SYSTEM_DESIGN.md) | 为什么用 RAG、为什么用 Redis Streams、扩展策略 |
| [技术决策](docs/interview/TECH_DECISIONS.md) | 为什么选 FastAPI、React、ChromaDB、Redis Streams |
| [面试 FAQ](docs/interview/FAQ.md) | 常见面试问题与答案 |
| [部署架构](docs/DEPLOYMENT_ARCHITECTURE.md) | Docker、网络和生产部署 |
| [演示脚本](docs/demo/demo-script.md) | 所有功能的逐步操作指南 |

---

## License

MIT — 详见 [LICENSE](LICENSE)。
