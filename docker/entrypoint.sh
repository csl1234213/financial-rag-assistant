#!/bin/bash
# ============================================================
# Financial RAG Assistant — Backend Entrypoint
# ============================================================
set -e

echo "============================================"
echo " Financial RAG Assistant — Backend API"
echo "============================================"
echo " APP_ENV:  ${APP_ENV:-production}"
echo " API_HOST: ${API_HOST:-0.0.0.0}"
echo " API_PORT: ${API_PORT:-8000}"
echo " LLM_PROVIDER: ${LLM_PROVIDER:-deepseek}"
echo " CHROMA_PATH: ${CHROMA_PATH:-chroma_db}"
echo "============================================"

# Ensure data directories exist
mkdir -p "${CHROMA_PATH:-chroma_db}"
mkdir -p "${UPLOAD_DIR:-storage/uploads}"
mkdir -p "${PDF_DIR:-storage/pdfs}"

# Start Uvicorn
exec uvicorn api.app:app \
    --host "${API_HOST:-0.0.0.0}" \
    --port "${API_PORT:-8000}" \
    --log-level "${LOG_LEVEL:-info}" \
    --no-access-log