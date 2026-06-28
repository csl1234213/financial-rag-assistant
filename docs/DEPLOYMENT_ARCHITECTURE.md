# V4.3 Deployment Architecture

## 1. System Overview

```
                    Internet / Browser
                            │
                            ▼
                   Streamlit Frontend
                   (financial-ui :8501)
                            │
                       HTTP / REST
                            │
                            ▼
                    FastAPI Backend
                   (financial-api :8000)
                            │
         ┌──────────────────┴──────────────────┐
         ▼                                     ▼
    Chroma Vector Store                Upload Storage
    (financial-chroma)                (financial-uploads)
         │
         ▼
    Persistent Volume
```

---

## 2. Container Architecture

### 2.1 Container Map

| Container | Image | Port | Volume | Purpose |
|-----------|-------|------|--------|---------|
| `financial-ui` | `Dockerfile.ui` | `8501` | `financial_uploads` (ro) | Streamlit dashboard |
| `financial-api` | `Dockerfile.api` | `8000` | `financial_uploads` (rw), `financial_chroma` (rw) | FastAPI + Agent Runtime |
| `financial-chroma` | — | — | `financial_chroma` | Persistent vector store |

### 2.2 Container Responsibilities

**financial-ui (Streamlit)**

- Renders the research dashboard
- Calls `financial-api` via HTTP (no direct Chroma access)
- Shows uploaded PDFs from shared `financial_uploads` volume
- URL: `http://financial-ui:8501`

**financial-api (FastAPI)**

- Receives all REST requests
- Runs Agent Runtime: Planner → Retriever → Reasoning → Report
- Manages ChromaDB via `EmbeddingStore` interface
- Handles PDF upload + refresh
- URL: `http://financial-api:8000`

**Chroma Vector Store**

- Phase 1: Embedded Chroma (PersistentClient) inside `financial-api`
- Phase 2: Can be promoted to standalone Chroma Server without API changes
- Data persisted on `financial_chroma` volume

---

## 3. Volume Design

| Volume | Mount (API) | Mount (UI) | Purpose |
|--------|------------|------------|---------|
| `financial_uploads` | `/app/storage/uploads` (rw) | `/app/storage/uploads` (ro) | PDF files, temp data |
| `financial_chroma` | `/app/chroma_db` (rw) | — | Vector embeddings, metadata, collections |

```yaml
volumes:
  financial_uploads:
    driver: local
  financial_chroma:
    driver: local
```

Key property: deleting containers does not delete data.

---

## 4. Network Design

```yaml
networks:
  financial_network:
    driver: bridge
```

All containers join `financial_network`. Service discovery works via container names:

| Service | Internal URL |
|---------|-------------|
| API | `http://financial-api:8000` |
| UI | `http://financial-ui:8501` |

Future services (Redis, Nginx) join the same network.

---

## 5. Environment Variables

### 5.1 `.env.example`

```bash
# ========== App ==========
APP_ENV=development
APP_VERSION=4.3.0
LOG_LEVEL=INFO

# ========== API ==========
API_HOST=0.0.0.0
API_PORT=8000

# ========== UI ==========
UI_PORT=8501
API_BASE=http://financial-api:8000

# ========== Storage ==========
CHROMA_PATH=/app/chroma_db
UPLOAD_DIR=/app/storage/uploads
PDF_DIR=/app/storage/pdfs

# ========== LLM ==========
DEEPSEEK_API_KEY=sk-xxx
LLM_MODEL=deepseek-chat

# ========== Redis (future) ==========
# REDIS_HOST=financial-redis
# REDIS_PORT=6379
```

### 5.2 Hardcoded Paths → Environment (Migration Plan)

| Before | After |
|--------|-------|
| `"./chroma_db"` | `os.environ.get("CHROMA_PATH", "./chroma_db")` |
| `"http://localhost:8000"` | `os.environ.get("API_BASE", "http://localhost:8000")` |
| `"storage/uploads"` | `os.environ.get("UPLOAD_DIR", "storage/uploads")` |
| `"pdfs/"` | `os.environ.get("PDF_DIR", "pdfs")` |

---

## 6. Health Check Design

### 6.1 Current

```json
{
  "status": "ok",
  "version": "4.0.0",
  "api": "ok",
  "documents": 18
}
```

### 6.2 Target (V4.3)

```json
{
  "status": "healthy",
  "version": "4.3.0",
  "api": "healthy",
  "vector_store": "healthy",
  "documents": 18,
  "collections": 4,
  "uptime": "2h 34m",
  "environment": "development"
}
```

### 6.3 Docker Healthcheck

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

---

## 7. Directory Structure

```
project-root/
│
├── docker/
│   ├── Dockerfile.api          # FastAPI backend
│   ├── Dockerfile.ui           # Streamlit frontend
│   ├── Dockerfile.dev          # Combined dev image
│   └── README.md
│
├── deploy/
│   ├── docker-compose.dev.yml  # Development (hot-reload)
│   ├── docker-compose.prod.yml # Production (optimized)
│   └── .env.example
│
├── config/
│   ├── settings.py             # Unified settings (env → config)
│   ├── app.py                  # App-level config
│   ├── storage.py              # Storage paths config
│   └── api.py                  # API-specific config
│
├── docs/
│   └── DEPLOYMENT_ARCHITECTURE.md
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── tests/
│   ├── conftest.py
│   ├── integration/
│   └── ... (unit tests)
│
├── core/          # Business logic
├── agent/         # Agent runtime
├── retrieval/     # Retrieval layer
├── storage/       # EmbeddingStore interface
├── api/           # FastAPI app
├── ui/            # Streamlit app
├── llm/           # LLM provider
│
├── .env
├── .env.example
├── requirements.txt
└── pyproject.toml
```

---

## 8. Deployment Modes

### 8.1 Development (`docker-compose.dev.yml`)

- Hot-reload enabled (volume mounts)
- Chroma embedded mode
- Streamlit dev mode
- Debug logging

```bash
docker compose -f deploy/docker-compose.dev.yml up
```

### 8.2 Production (`docker-compose.prod.yml`)

- No hot-reload
- Multi-stage builds
- Chroma persistent volume
- Health checks enabled
- Restart policy: always

```bash
docker compose -f deploy/docker-compose.prod.yml up -d
```

---

## 9. Future Architecture (V4.4+)

```
                    Browser
                       │
                       ▼
                     Nginx (:80 / :443)
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
     financial-ui              financial-api
     (:8501)                   (:8000)
                                  │
                     ┌────────────┴────────────┐
                     ▼                         ▼
               financial-redis           financial-chroma
               (cache / queue)           (vector store)
```

Additions:
- **Nginx**: reverse proxy, TLS termination, static file serving
- **Redis**: query cache, session store, async task queue
- **Chroma Server**: standalone Chroma (no API change needed — `EmbeddingStore` abstraction)

---

## 10. Phase 1 Deliverables Checklist

- [x] Container architecture diagram
- [x] Network design (financial_network)
- [x] Volume design (financial_uploads, financial_chroma)
- [x] Environment variables (.env.example)
- [x] Health check upgrade plan
- [x] Docker directory structure
- [x] Dev vs Prod deployment modes
- [x] Future architecture roadmap