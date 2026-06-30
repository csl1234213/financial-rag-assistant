#!/usr/bin/env bash
# ============================================================
# status.sh — Show container status and recent logs
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

COMPOSE_BASE="$PROJECT_ROOT/deploy/docker-compose.base.yml"
COMPOSE_PROD="$PROJECT_ROOT/deploy/docker-compose.prod.yml"
COMPOSE_DEV="$PROJECT_ROOT/deploy/docker-compose.dev.yml"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "  Container Status"
echo "=========================================="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  No containers running."

echo ""
echo "=========================================="
echo "  Recent Logs"
echo "=========================================="

# Try prod first, then dev
if docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_PROD" ps --format '{{.Names}}' 2>/dev/null | grep -q "financial"; then
    docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_PROD" logs --tail=20
elif docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_DEV" ps --format '{{.Names}}' 2>/dev/null | grep -q "financial"; then
    docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_DEV" logs --tail=20
else
    echo "  No running containers detected."
fi

echo ""
echo "=========================================="
echo "  Disk Usage"
echo "=========================================="
docker system df -v 2>/dev/null | head -20 || echo "  Docker not available."