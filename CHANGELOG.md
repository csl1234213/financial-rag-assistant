# Changelog

All notable changes to Financial Research Copilot.

---

## V3.0.0 — Agent Runtime Edition (2026-06-27)

### Added

- **Agent Runtime** (`agent/agent_runtime.py`) — Unified lifecycle manager for AI Agent execution
- **Query Planner** (`agent/query_planner.py`) — Intent → structured ExecutionPlan with DAG dependencies
- **Execution Plan** (`agent/execution_plan.py`) — StepType / StepStatus / PlanStep / ExecutionPlan data structures
- **Execution Engine** (`agent/execution_engine.py`) — Handler-based dispatch with dependency resolution
- **Reasoning Engine** (`agent/reasoning_engine.py`) — Structured analysis: Facts / Risks / Opportunities extraction
- **Reasoning Models** (`agent/reasoning_models.py`) — Evidence + ReasoningResult dataclasses
- **Execution Result** (`agent/execution_result.py`) — Unified step output container
- **Runtime Context** (`agent/runtime_context.py`) — Replaces ad-hoc shared_context dict
- **Runtime Result** (`agent/runtime_result.py`) — Replaces long return tuple from run_rag()
- **Intent Analyzer** (`core/intent_analyzer.py`) — Question intent detection + company extraction
- **Research Mode** (`research_mode.py`) — detect_research_mode() for prompt routing
- **Evidence-based retrieval** — `HybridRetriever.retrieve_evidence()` returns `List[Evidence]`

### Refactored

- **Core Engine** (`core/core_engine.py`) — Thinned from 50-line pipeline to `runtime.run()` call
- **Context Builder** (`core/context_builder.py`) — Added `build_context_from_evidence()` for Evidence[]
- **Report Builder** (`core/report_builder.py`) — Accepts optional `ReasoningResult` for Facts / Risks / Opportunities sections
- **Agent directory** (`agent/`) — All Agent logic extracted from core/ into dedicated module

### Improved

- **Modular Architecture** — Clear layer separation: agent / core / retrieval / llm / ui
- **Extensible Runtime** — Handler registration pattern, StepType enum, parameters/metadata on PlanStep
- **Workflow Orchestration** — DAG dependency resolution via `depends_on` field
- **Structured Output** — ReasoningResult replaces raw LLM analysis for explainability

---

## V2.2 — Stable

- Knowledge Manager
- Context Builder
- Cleaner Core Engine
- Dynamic Knowledge Base
- Chunk Statistics
- Cleaner Project Architecture

---

## V2.1 — Router Experiment (removed)

- Document Router (experimental, later removed for simplicity)

---

## V2 — Multi-Document RAG

- Multi-PDF Retrieval
- Evidence Panel
- Research Report

---

## V1 — PDF QA Prototype

- Single PDF QA
- Basic semantic search
- LLM answer generation