# Architecture — Financial RAG Assistant

## High-Level Architecture

Financial RAG Assistant is a production-ready AI research copilot with a layered architecture designed for financial document analysis. The system operates as a **Docker Compose multi-service application** with 5 containerized services.

```
                    ┌──────────────────────────────┐
                    │           USER                │
                    │    (Browser / API Client)     │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │       REACT FRONTEND          │
                    │    Vite + TypeScript + Nginx  │
                    │          Port :3000           │
                    └──────────────┬───────────────┘
                                   │ HTTP REST + JWT
                                   ▼
                    ┌──────────────────────────────┐
                    │       FASTAPI BACKEND          │
                    │    REST API Gateway            │
                    │    Port :8000                  │
                    ├──────────────────────────────┤
                    │  ┌──────────────────────────┐ │
                    │  │     AUTH LAYER            │ │
                    │  │  JWT + bcrypt password    │ │
                    │  │  Tenant context injection │ │
                    │  └──────────┬───────────────┘ │
                    │             │                  │
                    │  ┌──────────▼───────────────┐ │
                    │  │     AGENT RUNTIME         │ │
                    │  │  ┌─────────────────────┐ │ │
                    │  │  │ Intent Analyzer     │ │ │
                    │  │  │  → Direct Chat      │ │ │
                    │  │  │  → Single Company   │ │ │
                    │  │  │  → Compare Companies│ │ │
                    │  │  │  → Global Research  │ │ │
                    │  │  └────────┬────────────┘ │ │
                    │  │           ▼               │ │
                    │  │  ┌─────────────────────┐ │ │
                    │  │  │ Query Planner       │ │ │
                    │  │  │  Task → Complexity  │ │ │
                    │  │  │  → Execution Plan   │ │ │
                    │  │  └────────┬────────────┘ │ │
                    │  │           ▼               │ │
                    │  │  ┌─────────────────────┐ │ │
                    │  │  │ Strategy Engine     │ │ │
                    │  │  │  → RAG              │ │ │
                    │  │  │  → Direct LLM       │ │ │
                    │  │  │  → Parallel         │ │ │
                    │  │  │  → MultiStep        │ │ │
                    │  │  │  → Tool Calling     │ │ │
                    │  │  └────────┬────────────┘ │ │
                    │  │           ▼               │ │
                    │  │  ┌─────────────────────┐ │ │
                    │  │  │ Workflow Engine     │ │ │
                    │  │  │  Build → Execute    │ │ │
                    │  │  └─────────────────────┘ │ │
                    │  └──────────────────────────┘ │
                    │             │                  │
                    │  ┌──────────▼───────────────┐ │
                    │  │    HYBRID RETRIEVER       │ │
                    │  │  Semantic + Keyword       │ │
                    │  └──────────┬───────────────┘ │
                    │             │                  │
                    │  ┌──────────▼───────────────┐ │
                    │  │    LLM PROVIDER LAYER     │ │
                    │  │  ProviderFactory          │ │
                    │  │  ProviderRegistry         │ │
                    │  │  ModelRouter              │ │
                    │  └──────────────────────────┘ │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
            ┌──────────────┐ ┌──────────┐ ┌──────────────┐
            │   ChromaDB    │ │  Redis   │ │    SQLite    │
            │  Vector Store │ │ Streams  │ │  Task / User │
            │   Port :8001  │ │ Port :6379│ │    DB        │
            └──────────────┘ └────┬─────┘ └──────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────────┐
                    │        WORKER POOL            │
                    │    TaskWorker (x N replicas)  │
                    │    ┌────────────────────────┐ │
                    │    │ Consumer Group: workers│ │
                    │    │ Auto-retry             │ │
                    │    │ Heartbeat monitoring   │ │
                    │    │ Stale task recovery    │ │
                    │    └────────────────────────┘ │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │    Document Processing        │
                    │  PDF → Chunk → Embed → Store  │
                    └──────────────────────────────┘
```

---

## Multi-Tenant Security

### Tenant Isolation Model

The system implements a **three-layer tenant isolation** model:

```
JWT Token
    │
    ▼
User (user_id, tenant_id FK)
    │
    ▼
Tenant (tenant_id, slug, name)
    │
    ├── Document (tenant_id FK)
    │       └── Vector Metadata (tenant_id in ChromaDB)
    │
    └── Task (tenant_id FK)
            └── Redis Stream Message (tenant_id in payload)
```

### Authentication Flow

1. **Register** → User created with auto-bind to `default` tenant → JWT returned
2. **Login** → Password verified (bcrypt) → JWT issued with `sub: user_id`
3. **Request** → `Authorization: Bearer <token>` → JWT decoded → User loaded → Tenant loaded
4. **Tenant Context** → Injected into all API endpoints via FastAPI `Depends(get_current_tenant)`

### Data Scoping

| Layer | Isolation Mechanism |
|-------|-------------------|
| **Database** | All models (`Document`, `Task`) have `tenant_id` foreign key. Queries filter by `tenant_id`. |
| **Vector Store** | ChromaDB collections include `tenant_id` in metadata. Retrieval filters by `tenant_id`. |
| **Task Queue** | Redis Stream messages include `tenant_id` in payload. Workers filter tasks by tenant. |
| **File Storage** | Uploads organized by tenant directory (not yet implemented, designed). |

### Security Properties

- **No cross-tenant data access**: All queries are scoped to `current_user.tenant_id`
- **Token validation**: JWT signature verification on every request
- **Password hashing**: bcrypt with salt, never stored in plaintext
- **Tenant integrity**: Foreign key constraints ensure referential integrity

---

## Async Task System

### Architecture

```
┌─────────┐     ┌──────────┐     ┌───────────────┐     ┌──────────┐
│ API      │────▶│  SQLite   │────▶│  Redis Streams │────▶│ Worker   │
│ Backend  │     │ Task DB   │     │  Message Queue │     │ Pool     │
└─────────┘     └──────────┘     └───────────────┘     └──────────┘
                                                               │
                                                               ▼
                                                        ┌──────────────┐
                                                        │  Processing  │
                                                        │  ┌─────────┐ │
                                                        │  │ Chunking│ │
                                                        │  │Embedding│ │
                                                        │  │ Store   │ │
                                                        │  └─────────┘ │
                                                        └──────────────┘
```

### Redis Streams

- **Stream Key**: `task:stream`
- **Consumer Group**: `workers` (shared across all worker replicas)
- **Message Format**: `{task_id, task_type, tenant_id, payload}`
- **Acknowledgment**: `XACK` after successful processing
- **Pending Recovery**: `XPENDING` for stale task detection and recovery

### Worker Pool

- **Concurrency**: Configurable via `WORKER_CONCURRENCY` (default: 4 threads per worker)
- **Scaling**: `docker compose up -d --scale worker=3` for horizontal scaling
- **Heartbeat**: Periodic heartbeat to Redis (`HEARTBEAT_INTERVAL` seconds)
- **Stale Recovery**: Workers detect and recover tasks abandoned by crashed workers
- **Retry**: Automatic retry with configurable max attempts and backoff

### Task Lifecycle

```
PENDING → RUNNING → SUCCESS
                  → FAILED (retry) → PENDING
                  → FAILED (max retries exceeded)
```

### Task Types

| Type | Handler | Description |
|------|---------|-------------|
| `PROCESS_DOCUMENT` | `process_document_task` | PDF chunking → embedding → ChromaDB storage |

---

## Data Flow

### Upload Flow

```
User Uploads PDF
    │
    ▼
POST /api/v1/upload
    │
    ├── Save PDF to storage/uploads/
    │
    ├── Create Document record (tenant_id scoped)
    │
    ├── Create Task record (status: PENDING, tenant_id scoped)
    │
    ├── Publish message to Redis Stream
    │
    └── Return task_id to user
            │
            ▼
    Worker picks up task
            │
            ├── Load PDF → Extract text
            ├── Chunk text (sentence-transformers tokenizer)
            ├── Generate embeddings
            ├── Store in ChromaDB (with tenant_id metadata)
            ├── Update Task: status → RUNNING, progress → 50
            ├── Refresh knowledge base
            └── Update Task: status → SUCCESS, progress → 100
```

### Query Flow

```
User Question
    │
    ▼
POST /api/v1/chat
    │
    ▼
Agent Runtime
    │
    ├── Intent Analyzer
    │   └── Classify: Direct Chat / Single Company / Compare / Global
    │
    ├── Query Planner
    │   ├── Task Analysis (entity extraction, keyword classification)
    │   ├── Complexity Analysis (LOW / MEDIUM / HIGH)
    │   └── Build Routing Context
    │
    ├── Strategy Engine
    │   └── Select: RAG / Direct LLM / Parallel / MultiStep / Tool Calling
    │
    ├── Workflow Engine
    │   ├── Build workflow steps (Retrieve → Reason → Answer)
    │   └── Execute steps with dependency resolution
    │
    ├── Hybrid Retriever
    │   ├── Semantic search (embedding similarity)
    │   ├── Keyword search (BM25)
    │   ├── Fusion (weighted combination)
    │   └── Filter by tenant_id
    │
    ├── LLM Provider
    │   ├── ModelRouter selects provider (DeepSeek / Gemini / Claude)
    │   ├── ProviderFactory creates provider instance
    │   └── Generate response with retrieved context
    │
    └── Response
        ├── report: Markdown research report
        ├── citations: Source documents with similarity scores
        ├── reasoning: Intent, evidence count, companies
        ├── execution: Strategy, retrieval usage
        └── workflow: Type, status, steps completed
```

---

## LLM Provider Abstraction

### Factory + Registry + Router Pattern

```
Request
    │
    ▼
ModelRouter
    │
    ├── RoutingPolicy (CapabilityRoutingPolicy)
    │   └── Select provider based on task type, cost, priority
    │
    ├── ProviderRegistry
    │   └── List available providers with capabilities
    │
    └── ProviderFactory
        └── Create provider instance with config
            │
            ▼
BaseProvider.chat(messages)
    ├── DeepSeekProvider (Production)
    ├── GeminiProvider (Supported)
    └── ClaudeProvider (Reserved)
```

### Supported Providers

| Provider | Status | API | Configuration |
|----------|--------|-----|---------------|
| DeepSeek | Production | OpenAI-compatible | `DEEPSEEK_API_KEY` |
| Gemini | Supported | Google AI SDK | `GEMINI_API_KEY` |
| Claude | Reserved | Anthropic SDK | `CLAUDE_API_KEY` |

---

## Infrastructure

### Docker Compose Topology

```
Network: financial_network
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Frontend │  │ Backend  │  │ Worker   │  │ Worker   │   │
│  │ (Nginx)  │  │(FastAPI) │  │  (1)     │  │  (2)     │   │
│  │  :3000   │  │  :8000   │  │          │  │          │   │
│  └──────────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│                     │              │              │          │
│                     └──────────────┼──────────────┘          │
│                                    │                         │
│                     ┌──────────────┼──────────────┐          │
│                     ▼              ▼              ▼          │
│              ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│              │ ChromaDB │  │  Redis   │  │  SQLite  │      │
│              │  :8001   │  │  :6379   │  │ (volume) │      │
│              └──────────┘  └──────────┘  └──────────┘      │
│                                                              │
└──────────────────────────────────────────────────────────────┘

Named Volumes:
  chroma_data    → /chroma/chroma (ChromaDB persistence)
  redis_data     → /data (Redis RDB/AOF)
  db_data        → /app/data (SQLite shared between backend + workers)
  uploads_data   → /app/storage/uploads (PDF files)
  logs_data      → /app/logs (application logs)
```

### Health Checks

| Service | Check | Interval | Timeout |
|---------|-------|----------|---------|
| Frontend | Nginx serving static files | Docker built-in | - |
| Backend | `GET /api/v1/health` | 30s | 10s |
| ChromaDB | `GET /api/v2/heartbeat` | 30s | 10s |
| Redis | `redis-cli ping` | 10s | 5s |
| Worker | Heartbeat to Redis | Configurable | - |

---

## Key Design Decisions

1. **SQLite over PostgreSQL**: Minimizes infrastructure complexity for single-node deployment. Named volume sharing enables multi-container access. Suitable for team-scale usage (< 100 concurrent users).

2. **Redis Streams over Celery**: Lighter weight, fewer dependencies. Redis is already used for caching. Streams provide consumer groups, message acknowledgment, and pending message recovery out of the box.

3. **ChromaDB over Pinecone/Weaviate**: Open-source, self-hosted, no vendor lock-in. Native Docker support. Sufficient performance for document-scale retrieval (< 10K documents).

4. **Agent Runtime over LangChain**: Full control over orchestration logic. No framework lock-in. Clean separation of concerns (Intent → Planning → Strategy → Workflow → Execution). Pluggable capabilities (Memory, Metrics, Tracing).

5. **ProviderFactory over hardcoded LLM**: Swap providers without code changes. ModelRouter selects provider based on task type and capabilities. Registry pattern for extensibility.