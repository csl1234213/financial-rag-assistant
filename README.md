# Financial Research Assistant

A production-oriented Financial RAG Assistant for financial statement analysis.

---

## Features

### Knowledge Base

- Dynamic PDF Upload
- Multi-PDF Knowledge Base
- Knowledge Source Manager
- Automatic Knowledge Refresh

### Retrieval

- Semantic Search
- Multi-document Retrieval
- Context Builder
- Evidence Extraction

### Research

- Research Report Generation
- Evidence Panel
- Citation Support
- Compare Mode

---

## System Architecture


                Upload PDF
                     │
                     ▼
          Knowledge Manager
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
              Vector Search
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


---

## Project Structure


financial-rag-assistant/

core/
│
├── core_engine.py
├── knowledge_manager.py
├── context_builder.py
├── report_builder.py
├── citation_formatter.py
└── research_analyzer.py

retrieval/
│
└── hybrid_retriever.py

ui/
│
└── streamlit_app.py

pdfs/

uploads/

README.md


---

## Current Capabilities

- Upload financial reports
- Build knowledge base automatically
- Retrieve relevant evidence
- Generate research reports
- Compare multiple companies
- Display citations
- Multi-PDF retrieval

---

## Technology Stack

Python

Streamlit

Sentence Transformers

PyTorch

RAG

OpenAI Compatible API

---

## Roadmap

### V2.2 Stable

- Dynamic Knowledge Base
- Knowledge Manager
- Evidence Panel
- Research Report
- Context Builder
- Multi-PDF Retrieval

### V2.3

- Retrieval Pipeline Cleanup
- Hybrid Search
- Better Ranking

### V2.4

- Financial Ratio Analysis
- Company Profile
- Timeline View

### V3.0

- Web Search
- Real-time News
- AI Agent Workflow

---

## Screenshots

Home

Upload PDF

Knowledge Base

Research Report

Evidence Panel

---

## License

MIT License