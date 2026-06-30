#!/usr/bin/env bash
# ============================================================
# start.sh — One-Command Deploy
# ============================================================
# Usage:
#   ./scripts/start.sh          # production mode (default)
#   ./scripts/start.sh dev      # development mode (hot-reload)
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

COMPOSE_BASE="$PROJECT_ROOT/deploy/docker-compose.base.yml"
COMPOSE_PROD="$PROJECT_ROOT/deploy/docker-compose.prod.yml"
COMPOSE_DEV="$PROJECT_ROOT/deploy/docker-compose.dev.yml"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

MODE="${1:-prod}"
API_URL="http://localhost:8000"
UI_URL="http://localhost:8501"
HEALTH_URL="${API_URL}/api/v1/health"
MAX_RETRIES=30
RETRY_INTERVAL=2

# ============================================================
# Step 1: Auto .env initialization
# ============================================================
if [ ! -f "$ENV_FILE" ]; then
    echo "=========================================="
    echo "  .env not found — creating from .env.example"
    echo "=========================================="
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo ""
    echo "  IMPORTANT: Please edit .env to set your DEEPSEEK_API_KEY before proceeding."
    echo "  File: $ENV_FILE"
    echo ""
    read -rp "  Press Enter to continue after editing, or Ctrl+C to abort... "
fi

# ============================================================
# Step 2: Select compose files
# ============================================================
if [ "$MODE" = "dev" ]; then
    echo "=========================================="
    echo "  Starting in DEVELOPMENT mode (hot-reload)"
    echo "=========================================="
    COMPOSE_FILES="-f $COMPOSE_BASE -f $COMPOSE_DEV"
    PROJECT_NAME="financial-rag-dev"
else
    echo "=========================================="
    echo "  Starting in PRODUCTION mode"
    echo "=========================================="
    COMPOSE_FILES="-f $COMPOSE_BASE -f $COMPOSE_PROD"
    PROJECT_NAME="financial-rag-prod"
fi

# ============================================================
# Step 3: Build & Start
# ============================================================
cd "$PROJECT_ROOT"

echo ""
echo "Building and starting containers..."
docker compose $COMPOSE_FILES up -d --build 2>&1

# ============================================================
# Step 4: Health check loop
# ============================================================
echo ""
echo "Waiting for API to become healthy..."
for i in $(seq 1 $MAX_RETRIES); do
    if curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" 2>/dev/null | grep -q "200"; then
        echo ""
        echo "=========================================="
        echo "  Financial Research Copilot Ready!"
        echo "=========================================="
        echo ""
        echo "  API:      $API_URL"
        echo "  Swagger:  $API_URL/docs"
        echo "  UI:       $UI_URL"
        echo ""
        echo "  Status:   docker ps"
        echo "  Logs:     ./scripts/logs.sh"
        echo "  Stop:     ./scripts/stop.sh"
        echo ""
        exit 0
    fi
    printf "  [%2d/%2d] Waiting...\r" "$i" "$MAX_RETRIES"
    sleep "$RETRY_INTERVAL"
done

echo ""
echo "=========================================="
echo "  WARNING: API did not become healthy within $((MAX_RETRIES * RETRY_INTERVAL))s"
echo "=========================================="
echo "  Check logs: ./scripts/logs.sh"
echo ""
exit 1