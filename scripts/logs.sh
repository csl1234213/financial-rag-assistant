#!/usr/bin/env bash
# ============================================================
# logs.sh — Follow container logs
# ============================================================
# Usage:
#   ./scripts/logs.sh           # follow all logs
#   ./scripts/logs.sh api       # follow API logs only
#   ./scripts/logs.sh ui        # follow UI logs only
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

COMPOSE_BASE="$PROJECT_ROOT/deploy/docker-compose.base.yml"
COMPOSE_PROD="$PROJECT_ROOT/deploy/docker-compose.prod.yml"
COMPOSE_DEV="$PROJECT_ROOT/deploy/docker-compose.dev.yml"

SERVICE="${1:-}"

cd "$PROJECT_ROOT"

# Detect running compose project
if docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_PROD" ps --format '{{.Names}}' 2>/dev/null | grep -q "financial"; then
    COMPOSE_FILES="-f $COMPOSE_BASE -f $COMPOSE_PROD"
elif docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_DEV" ps --format '{{.Names}}' 2>/dev/null | grep -q "financial"; then
    COMPOSE_FILES="-f $COMPOSE_BASE -f $COMPOSE_DEV"
else
    echo "No running containers detected."
    echo "Start first: ./scripts/start.sh"
    exit 1
fi

if [ -n "$SERVICE" ]; then
    docker compose $COMPOSE_FILES logs -f "$SERVICE"
else
    docker compose $COMPOSE_FILES logs -f
fi