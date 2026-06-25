Financial Research Assistant Architecture

Overview

Financial Research Assistant is a Retrieval-Augmented Generation (RAG) system designed for financial statement analysis.

The system allows users to upload one or more financial reports, automatically builds a knowledge base, retrieves the most relevant evidence, and generates structured research reports with evidence citations.

⸻

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
core/
│
├── core_engine.py
├── context_builder.py
├── knowledge_manager.py
├── report_builder.py
├── research_analyzer.py
└── citation_formatter.py
retrieval/
│
└── hybrid_retriever.py
ui/
│
└── streamlit_app.py
pdfs/
uploads/

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

Future Roadmap

V2.3

* Retrieval Pipeline Cleanup
* Better Ranking Strategy

V2.4

* Hybrid Search
* Financial Ratio Analysis

V3.0

* Real-time Web Search
* AI Agent Workflow
* Financial Research Copilot