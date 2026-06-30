#!/usr/bin/env bash
# ============================================================
# stop.sh — Stop all containers (preserve volumes)
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

COMPOSE_BASE="$PROJECT_ROOT/deploy/docker-compose.base.yml"
COMPOSE_PROD="$PROJECT_ROOT/deploy/docker-compose.prod.yml"
COMPOSE_DEV="$PROJECT_ROOT/deploy/docker-compose.dev.yml"

MODE="${1:-prod}"

if [ "$MODE" = "dev" ]; then
    COMPOSE_FILES="-f $COMPOSE_BASE -f $COMPOSE_DEV"
else
    COMPOSE_FILES="-f $COMPOSE_BASE -f $COMPOSE_PROD"
fi

cd "$PROJECT_ROOT"

echo "Stopping containers..."
docker compose $COMPOSE_FILES down

echo ""
echo "Containers stopped. Volumes preserved."
echo "  docker compose $COMPOSE_FILES up -d"
echo "  ./scripts/start.sh"
echo ""