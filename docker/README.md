# Docker Build Guide

## Images

| Dockerfile | Container | Purpose |
|-----------|-----------|---------|
| `Dockerfile.api` | `financial-api` | FastAPI backend |
| `Dockerfile.ui` | `financial-ui` | Streamlit frontend |
| `Dockerfile.dev` | `financial-dev` | Combined dev image |

## Build

```bash
# API
docker build -f docker/Dockerfile.api -t financial-rag-assistant/api .

# UI
docker build -f docker/Dockerfile.ui -t financial-rag-assistant/ui .

# Dev (combined)
docker build -f docker/Dockerfile.dev -t financial-rag-assistant/dev .
```

## Run with Docker Compose

```bash
# Development
docker compose -f deploy/docker-compose.dev.yml up

# Production
docker compose -f deploy/docker-compose.prod.yml up -d
```