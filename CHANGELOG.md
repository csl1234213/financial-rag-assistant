# Changelog

All notable changes to Financial Agent Runtime Assistant.

---

## v7.3.1 — Agent Runtime Framework

**Released: 2026-07-15**

### Added

- **Direct Chat Workflow** — Non-research queries routed to direct LLM conversation
- **Intent Router Stabilization** — `DIRECT_CHAT` intent classification with research signal detection
- **E2E Regression Tests** — `tests/e2e/` covering DirectChat, RAG, and Provider workflows
- **Intent Router Regression Matrix** — `tests/planning/test_intent_router_regression.py` (31 cases)
- **Agent Runtime Layers** — Tracing, Metrics, Reliability, Memory, Tools (Framework Ready)

### Improved

- **Provider Abstraction** — Removed legacy `llm/deepseek.py` (0 references), centralized in `ProviderFactory`
- **Repository Structure** — Removed `agent/researcher.py` (empty), `api/api_server.py` (legacy entry)
- **Documentation** — README and ARCHITECTURE updated to reflect V7.3.1 Agent Runtime Framework
- **Execution Layer** — Clarified dual-engine design with docstrings for Strategy vs Step engines

### Validation

- **969 tests passed** (0 failures)
- **85%+ coverage**
- FastAPI health check returns `APP_VERSION=7.3.1`

---

## Previous Releases

### V4.0.0-alpha — Production Architecture (2026-06-27)

- FastAPI (`api/app.py`) — Production HTTP server with Swagger UI
- REST API — `/api/v1/chat`, `/api/v1/knowledge`, `/api/v1/knowledge/statistics`, `/api/v1/upload`, `/api/v1/refresh`, `/api/v1/health`
- Chat Service (`api/services/chat_service.py`) — Business logic layer
- API Client SDK (`client/api_client.py`) — `APIClient` with unified timeout and error handling
- Streamlit now communicates via HTTP instead of direct Python function calls
- Version Management — All `/api/v1` prefix centralized

### V3.0.0 — Agent Runtime Edition (2026-06-27)

- Agent Runtime (`agent/agent_runtime.py`) — Unified lifecycle manager
- Query Planner (`agent/query_planner.py`) — Intent → structured ExecutionPlan
- Execution Plan (`agent/execution_plan.py`) — StepType / StepStatus / PlanStep / ExecutionPlan
- Execution Engine (`agent/execution_engine.py`) — Handler-based dispatch with dependency resolution
- Reasoning Engine (`agent/reasoning_engine.py`) — Structured analysis: Facts / Risks / Opportunities
- Runtime Context (`agent/runtime_context.py`) — Replaces ad-hoc shared_context dict
- Runtime Result (`agent/runtime_result.py`) — Replaces long return tuple from run_rag()
- Intent Analyzer (`core/intent_analyzer.py`) — Question intent detection + company extraction

### V2.2 — Stable

- Knowledge Manager, Context Builder, Cleaner Core Engine, Dynamic Knowledge Base

### V2.1 — Router Experiment (removed)

- Document Router (experimental, later removed for simplicity)

### V2 — Multi-Document RAG

- Multi-PDF Retrieval, Evidence Panel, Research Report

### V1 — PDF QA Prototype

- Single PDF QA, Basic semantic search, LLM answer generation