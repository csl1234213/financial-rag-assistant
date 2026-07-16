# Financial Agent Runtime Assistant V7.3.1

[![CI](https://github.com/csl1234213/financial-rag-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/csl1234213/financial-rag-assistant/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen)](https://github.com/csl1234213/financial-rag-assistant)
[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-969%20passed-brightgreen)](https://github.com/csl1234213/financial-rag-assistant)

## AI-Powered Financial Agent Runtime for Multi-Document Research

---

## Project Overview

Financial Agent Runtime Assistant is a **production-grade AI Agent framework** designed for financial document analysis.

Unlike traditional RAG demos, this project implements a **full Agent Runtime architecture** with Intent Routing, Workflow Orchestration, Layered Execution, and Pluggable Runtime Capabilities.

### Core Capabilities

- **Direct Chat Workflow** — Non-research queries routed to direct LLM conversation
- **Financial RAG Workflow** — Evidence-backed research reports with citations
- **Intent Routing** — Automatic classification: Direct Chat / Single Company / Compare Companies / Global Research
- **Workflow Orchestration** — Strategy-driven execution: RAG / DirectLLM / Parallel / MultiStep / ToolCalling
- **LLM Provider Abstraction** — Factory pattern with pluggable providers (DeepSeek, Gemini)
- **Pluggable Runtime Capabilities** — Memory, Metrics, Reliability, Tracing, Tool Calling

---

## Capability Matrix

### Production

| Feature | Status | Description |
|---|---|---|
| Direct Chat | Production | Non-research queries routed to direct LLM conversation |
| Financial RAG Workflow | Production | Evidence-backed research reports with citations |
| DeepSeek Provider | Production | Primary LLM provider via ProviderFactory |
| Agent Runtime | Production | Full lifecycle: Intent → Planning → Workflow → Execution → Provider |

### Supported

| Feature | Status | Description |
|---|---|---|
| Gemini Provider | Supported | Registered in ProviderRegistry, 95-line implementation |

### Framework Ready (Plug-and-Play)

| Feature | Status | Description |
|---|---|---|
| Memory | Framework Ready | Retrieve + Store lifecycle hooks, injectable via `memory_engine` |
| Metrics | Framework Ready | `runtime_duration`, `workflow_duration`, `estimated_tokens`, injectable via `metric_engine` |
| Reliability | Framework Ready | Retry, Timeout, CircuitBreaker, HealthCheck, RateLimiter, Fallback |
| Tracing | Framework Ready | Console/File/Memory tracers with TraceRegistry |
| Tool Calling | Framework Ready | ToolEngine + ToolCallingStrategy + ToolCallingHandler |

---

## Architecture Overview

```mermaid
graph TD
    A[User] --> B[Intent Router]
    B -->|DIRECT_CHAT| C[Planner]
    B -->|SINGLE_COMPANY| C
    B -->|COMPARE_COMPANIES| C
    B -->|GLOBAL_RESEARCH| C
    C --> D[Strategy Execution Engine]
    D -->|RAG| E[Workflow Layer]
    D -->|DirectLLM| E
    D -->|Parallel| E
    D -->|MultiStep| E
    D -->|ToolCalling| E
    E --> F[Step Execution Engine]
    F --> G[Provider Layer]
    G --> H[Response]

    F -.-> I[Metrics]
    F -.-> J[Reliability]
    F -.-> K[Memory]
    F -.-> L[Tracing]
    F -.-> M[Tool Calling]
```

### Pipeline Flow

```
                          User
                           │
                           ▼
                    Intent Router
                    (DIRECT_CHAT / SINGLE_COMPANY / COMPARE / GLOBAL)
                           │
                           ▼
                         Planner
                    (TaskAnalyzer + ComplexityAnalyzer)
                           │
                           ▼
                    Strategy Execution Engine
                    (RAG / DirectLLM / Parallel / MultiStep / ToolCalling)
                           │
                           ▼
                      Workflow Layer
                    (WorkflowEngine + WorkflowExecutor)
                           │
                           ▼
                    Step Execution Engine
                    (Handler dispatch + dependency resolution)
                           │
                           ▼
                      Provider Layer
                    (ProviderFactory + ProviderRegistry)
                           │
                           ▼
                        Response
```

### Execution Layer Design

The project uses a **dual-engine execution architecture**:

| Layer | Engine | Responsibility |
|---|---|---|
| Strategy Layer | `agent/execution/execution_engine.py` | **How to execute?** Selects strategy (RAG / DirectLLM / Parallel / MultiStep) |
| Step Layer | `agent/execution_engine.py` | **Execute each step.** Dispatches to registered handlers |

This design separates strategic decision-making from step-level execution, enabling independent evolution of both layers.

---

## Tech Stack

| Category | Technology |
|---|---|
| Language | Python 3.11 |
| API Framework | FastAPI |
| Vector Database | ChromaDB |
| LLM Provider | DeepSeek (primary), Gemini (supported) |
| Agent Runtime | Custom Agent Runtime Framework |
| Testing | pytest (969 tests, 85%+ coverage) |
| UI | Streamlit |

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/csl1234213/financial-rag-assistant.git
cd financial-rag-assistant

# 2. One-command start
./scripts/start.sh

# 3. Open in browser
#    UI:  http://localhost:8501
#    API: http://localhost:8000/docs
```

**Prerequisites:** Docker Desktop (or Docker Engine + Docker Compose)

On first run, the script will:
- Auto-create `.env` from `.env.example` (you'll be prompted to set your `DEEPSEEK_API_KEY`)
- Build and start all containers
- Wait for the API to become healthy
- Print access URLs

**Windows (PowerShell):**
```powershell
.\scripts\start.ps1
```

**Development mode (hot-reload):**
```bash
./scripts/start.sh dev
```

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/chat` | POST | Financial research chat |
| `/api/v1/knowledge` | GET | Knowledge base overview |
| `/api/v1/knowledge/statistics` | GET | Document & chunk statistics |
| `/api/v1/upload` | POST | Upload PDF + auto-refresh |
| `/api/v1/refresh` | POST | Rebuild knowledge base |
| `/api/v1/health` | GET | System health check |

---

## Project Structure

```
financial-rag-assistant/
├── agent/
│   ├── agent_runtime.py          # Unified lifecycle manager
│   ├── execution_engine.py       # Step Execution Engine (handler dispatch)
│   ├── execution_plan.py         # PlanStep / ExecutionPlan structures
│   ├── execution_result.py       # Step execution result
│   ├── query_planner.py          # Intent → ExecutionPlan
│   ├── reasoning_engine.py       # Evidence → Facts / Risks / Opportunities
│   ├── reasoning_models.py       # Evidence + ReasoningResult
│   ├── runtime_context.py        # Runtime state
│   ├── runtime_result.py         # Unified output
│   ├── runtime_state.py          # Reliability state tracking
│   ├── execution/                # Strategy Execution Engine
│   │   ├── execution_engine.py   # Strategy selection (RAG/DirectLLM/Parallel)
│   │   ├── execution_context.py
│   │   ├── execution_result.py
│   │   └── strategies/           # RAG, DirectLLM, Parallel, MultiStep, ToolCalling
│   ├── workflow/                 # Workflow Engine + Executor
│   ├── planning/                 # TaskAnalyzer, ComplexityAnalyzer, Routing
│   ├── memory/                   # Memory Engine (Framework Ready)
│   ├── metrics/                  # Metrics Engine (Framework Ready)
│   ├── reliability/              # Reliability Engine (Framework Ready)
│   ├── tracing/                  # Tracing Engine (Framework Ready)
│   └── tools/                    # Tool Engine (Framework Ready)
├── core/
│   ├── core_engine.py            # Main entry point (run_rag)
│   ├── intent_analyzer.py        # Intent classification
│   ├── context_builder.py        # Evidence → structured context
│   ├── knowledge_manager.py      # Knowledge source management
│   ├── report_builder.py         # Structured research report
│   └── citation_formatter.py     # Citation formatting
├── llm/
│   ├── provider.py               # Bridge adapter (ProviderFactory + call_llm)
│   ├── adapters/                 # Provider implementations
│   │   ├── deepseek_provider.py  # DeepSeek (Production)
│   │   ├── gemini_provider.py    # Gemini (Supported)
│   │   ├── azure_provider.py     # Azure (Reserved)
│   │   └── claude_provider.py    # Claude (Reserved)
│   ├── factory/                  # ProviderFactory
│   └── router/                   # ModelRouter
├── retrieval/
│   └── hybrid_retriever.py       # Semantic search + ranking
├── api/
│   ├── main.py                   # FastAPI entry point
│   ├── routers/                  # API route handlers
│   ├── services/                 # Business logic layer
│   └── schemas/                  # Pydantic request/response models
├── config/                       # Centralized configuration
├── tests/
│   ├── test_intent_analyzer.py
│   ├── planning/                 # Intent router regression matrix
│   └── e2e/                      # End-to-end tests
└── docs/                         # Architecture & deployment docs
```

---

## System Evolution

```
V1    → PDF QA Prototype
V2    → Multi-document RAG
V2.1  → Router Experiment (removed)
V2.2  → Stable Architecture
V3.0  → Agent Runtime Edition
V4.0  → Production Architecture
V7.3.1 → Agent Runtime Framework
```

---

## Key Engineering Highlights

### 1. Agent Runtime Architecture

Unlike traditional RAG pipelines, this project implements a full Agent Runtime with:
- **Query Planning** — Structured execution plans with DAG dependencies
- **Dual Execution Engine** — Strategy selection + Step dispatch
- **Runtime Context** — Unified state management for one Agent execution
- **Structured Reasoning** — Facts / Risks / Opportunities extraction
- **Explainable Evidence Pipeline** — Every output traceable to source documents

### 2. LLM Provider Abstraction

Factory pattern with pluggable providers:
- `ProviderFactory.create(config)` → `ProviderRegistry.get(name)` → `BaseProvider.chat()`
- DeepSeek (Production) and Gemini (Supported) providers
- Clean separation between SDK calls and business logic

### 3. Pluggable Runtime Capabilities

Memory, Metrics, Reliability, Tracing, and Tool Calling are **fully implemented** and **ready to activate** by injecting engine instances into `AgentRuntime`. The runtime gracefully degrades when engines are not provided.

### 4. Evidence-Based Output

Every answer must be traceable to source documents. The system provides:
- Answer
- Evidence
- Source documents
- Reasoning trace

---

## Demo Showcase

### Direct Chat

```
Request: POST /api/v1/chat
Body: {"question": "What is AI?", "stream": false}
```

Response:
```json
{
  "workflow": {"type": "direct_chat"},
  "execution": {"use_retrieval": false},
  "routing": {"provider": "deepseek", "model": "deepseek-chat"},
  "report": "Artificial Intelligence (AI) is..."
}
```

> No retrieval, no citations — direct LLM conversation.

---

### Financial RAG Research

```
Request: POST /api/v1/chat
Body: {"question": "Analyze Tesla revenue growth", "stream": false}
```

Response:
```json
{
  "workflow": {"type": "rag"},
  "execution": {"use_retrieval": true},
  "citations": [
    {"document": "tesla_2024_annual.pdf", "chunk": "Revenue increased 19%..."},
    {"document": "tesla_2024_annual.pdf", "chunk": "Automotive revenue..."}
  ],
  "report": "# Research Report\n\n## Summary\n..."
}
```

> Evidence-backed research with citations and source documents.

---

### Swagger API

FastAPI auto-generated API documentation at `/docs`:

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/chat` | POST | Financial research chat |
| `/api/v1/knowledge` | GET | Knowledge base overview |
| `/api/v1/upload` | POST | Upload PDF documents |
| `/api/v1/health` | GET | System health check (`APP_VERSION: "7.3.1"`) |

> Full demo script: [docs/demo/demo.md](docs/demo/demo.md)

---

## Design Philosophy

> Simplicity improves reliability more than complexity improves intelligence.

> Built not to answer questions, but to support financial reasoning.