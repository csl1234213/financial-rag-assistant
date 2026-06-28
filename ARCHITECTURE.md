Financial Research Assistant Architecture

Overview

Financial Research Assistant is a Retrieval-Augmented Generation (RAG) system designed for financial statement analysis.

The system allows users to upload one or more financial reports, automatically builds a knowledge base, retrieves the most relevant evidence, and generates structured research reports with evidence citations.

---

## V4 Production Architecture

```
Browser / Streamlit
        │
        ▼
   APIClient SDK
        │
        ▼
   REST API (FastAPI)
        │
        ▼
   Service Layer
        │
        ▼
   Agent Runtime
        │
        ▼
   Retriever
        │
        ▼
   LLM
```

---

High-Level Architecture

                    ┌──────────────────────┐
                    │    User Question     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Research Mode      │
                    │  Detection Module    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Retrieval Engine    │
                    │ Semantic Search      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Context Builder     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Prompt Builder      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │       LLM            │
                    └──────────┬───────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────┐
        │         Research Report Generator         │
        └──────────────┬────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
  Research Report             Evidence Panel



V3 Agent Runtime Architecture

                         UI
                          │
                          ▼
                  core_engine.py
                          │
                          ▼
                   AgentRuntime
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
         QueryPlanner ExecutionEngine ReasoningEngine
              │           │
              │           ▼
              │      HybridRetriever
              │
              ▼
         RuntimeContext
              │
              ▼
         ContextBuilder
              │
              ▼
         PromptBuilder
              │
              ▼
              LLM
              │
              ▼
         ReportBuilder

Pipeline:

User Query
    ↓
Intent Analyzer
    ↓
Query Planner
    ↓
Execution Plan
    ↓
Execution Engine
    ↓
Reasoning Engine
    ↓
Context Builder
    ↓
Prompt Builder
    ↓
LLM
    ↓
Report Builder

⸻

Knowledge Base Architecture

Upload PDF
      │
      ▼
Document Loader
      │
      ▼
Text Chunking
      │
      ▼
Embedding
      │
      ▼
Knowledge Base

Each uploaded PDF is automatically converted into semantic chunks and embedded into the local vector database.

⸻

Project Structure

financial-rag-assistant/
├── agent/
│   ├── agent_runtime.py
│   ├── execution_plan.py
│   ├── execution_result.py
│   ├── execution_engine.py
│   ├── query_planner.py
│   ├── reasoning_engine.py
│   ├── reasoning_models.py
│   ├── runtime_context.py
│   └── runtime_result.py
├── core/
│   ├── core_engine.py
│   ├── context_builder.py
│   ├── knowledge_manager.py
│   ├── report_builder.py
│   ├── research_analyzer.py
│   ├── citation_formatter.py
│   └── intent_analyzer.py
├── retrieval/
│   └── hybrid_retriever.py
├── llm/
│   └── provider.py
├── ui/
│   └── streamlit_app.py
├── pdfs/
└── uploads/

⸻

Module Responsibilities

core_engine.py

Coordinates the entire RAG workflow.

Responsibilities:

* Initialize embedding model
* Load knowledge base
* Execute retrieval
* Generate prompts
* Invoke LLM
* Generate research report

⸻

knowledge_manager.py

Responsible for knowledge source management.

Responsibilities:

* Load document list
* Document statistics
* Knowledge source management

⸻

context_builder.py

Builds the context sent to the LLM.

Responsibilities:

* Merge retrieved chunks
* Generate citations
* Build evidence preview

⸻

hybrid_retriever.py

Semantic retrieval engine.

Responsibilities:

* Encode user queries
* Vector similarity search
* Return Top-K evidence

⸻

report_builder.py

Formats model output into a structured research report.

Sections include:

* Summary
* Key Findings
* Risks
* Evidence Used



Agent Layer (V3)

agent_runtime.py

Unified lifecycle manager for one AI Agent execution.

Responsibilities:

* Intent analysis → Plan
* Execute via ExecutionEngine
* Collect evidence
* Build context & citations
* Reason via ReasoningEngine
* Return structured RuntimeResult



query_planner.py

Generates execution plans from user intent.

Responsibilities:

* Interpret intent analysis results
* Build structured ExecutionPlan
* Assign StepType to each task
* Define DAG dependencies (depends_on)



execution_plan.py

Core data structures for Agent workflow orchestration.

Exports:

* StepType — Enum (RETRIEVE / COMPARE / SYNTHESIS / TOOL_CALL / REASONING)
* StepStatus — Enum (PENDING / RUNNING / COMPLETED / FAILED / SKIPPED)
* PlanStep — One executable task with status, result, and tool_name
* ExecutionPlan — Full execution plan with tasks and metadata



execution_engine.py

Dispatches PlanStep to registered handlers.

Responsibilities:

* Register handlers per StepType
* Resolve depends_on dependencies
* Execute ready steps
* Track step status (PENDING → RUNNING → COMPLETED / FAILED)



reasoning_engine.py

Structured analysis of execution results.

Responsibilities:

* Aggregate execution outputs
* Convert outputs into structured Evidence
* Extract facts, risks, and opportunities
* Produce ReasoningResult



runtime_context.py / runtime_result.py

Unified runtime state and output.

RuntimeContext replaces ad-hoc shared_context dict.
RuntimeResult replaces the long return tuple from run_rag().

⸻

Data Flow

Upload PDF
      │
      ▼
Knowledge Base
      │
      ▼
User Question
      │
      ▼
Embedding Search
      │
      ▼
Top-K Chunks
      │
      ▼
Context Builder
      │
      ▼
Prompt Builder
      │
      ▼
LLM
      │
      ▼
Research Report
      │
      ▼
Evidence Panel

⸻

Design Principles

The project follows several engineering principles:

* Single Responsibility Principle
* Modular Architecture
* Separation of Retrieval and Generation
* Evidence-first Response
* Extensible Knowledge Source Management

⸻

Version Evolution

V1

* Single PDF QA

⸻

V2

* Multi-PDF Retrieval
* Evidence Panel
* Research Report

⸻

V2.2 Stable

* Knowledge Manager
* Context Builder
* Cleaner Core Engine
* Dynamic Knowledge Base
* Chunk Statistics
* Cleaner Project Architecture

⸻

V3.0.0 Agent Runtime Edition

* Agent Runtime (AgentRuntime)
* Query Planner (QueryPlanner)
* Execution Plan (ExecutionPlan + PlanStep)
* Execution Engine (ExecutionEngine)
* Runtime Context (RuntimeContext)
* Runtime Result (RuntimeResult)
* Structured Reasoning Engine (ReasoningEngine)
* Evidence-based output (Evidence + ReasoningResult)
* Handler registration pattern (StepType dispatch)
* DAG dependency resolution (depends_on)



Future Roadmap

V3.1 — Agent Capabilities

* Tool Registry (Yahoo Finance / SEC API / Web Search)
* ExecutionContext (upgrade from shared_context dict)
* Scheduler + Ready Queue (topological execution)

V3.2 — Agent Intelligence

* Reflection + Self-Correction
* Agent Memory
* Conversation State



V4 Roadmap — Productionization

Phase 1: Service Layer

* FastAPI application (`api/`)
* RESTful endpoints: `/api/v1/chat`, `/api/v1/knowledge`, `/api/v1/health`
* Request/Response schemas (`api/schemas/`)
* Streamlit, Web, and mobile reuse the same backend

Phase 2: Storage Layer

* ChromaDB — persistent vector storage
* Chunks, metadata, and embeddings persisted
* No re-embedding on restart
* Multi-user shared knowledge base
* Incremental document updates

Phase 3: Database Layer

* PostgreSQL — structured data
* Document Registry, Upload History, User Sessions, Query History, Feedback
* Separation of concerns: PostgreSQL (structured) + ChromaDB (vectors)

Phase 4: Cache Layer

* Redis — embedding, retrieval results, planner results, session cache
* Repeated queries served from cache
* Significant performance improvement for repeated analyses

Phase 5: Containerization

* Dockerfile + docker-compose.yml
* One-command startup: `docker compose up`
* Services: FastAPI + ChromaDB + PostgreSQL + Redis

Phase 6: Testing

* `tests/` directory with pytest
* Unit tests: Planner, Runtime, Retriever, Reasoner, API
* Coverage targets via pytest-cov

Phase 7: CI/CD

* GitHub Actions pipeline
* Lint → Unit Test → Coverage → Docker Build
* Executes on every push

Phase 8: Deployment

* FastAPI: Render / Railway / Fly.io
* PostgreSQL: Supabase / Railway
* Redis: Upstash
* ChromaDB: local persistent or cloud instance
* Streamlit: standalone deployment
* Future: AWS / Azure / GCP