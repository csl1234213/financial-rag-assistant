#!/bin/bash
set -e

echo "=== Financial Agent Runtime Assistant v7.3.3 ==="

cd /app

echo "[Entrypoint] Running knowledge bootstrap..."
python /app/docker/bootstrap_knowledge.py

echo "[Entrypoint] Starting API server..."
exec uvicorn api.main:app --host 0.0.0.0 --port 8000
