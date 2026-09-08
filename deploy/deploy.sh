#!/usr/bin/env bash
# Deploy one image tag on the server, gate on /health, roll back on failure.
#
#   ./deploy.sh <image-tag>          run from /srv/orderdesk
#
# Keeps the previously deployed tag in .previous_tag so rollback.sh can use it.
set -euo pipefail

cd "$(dirname "$0")"
TAG="${1:?usage: deploy.sh <image-tag>}"
COMPOSE=(docker compose -f compose.prod.yaml)
HEALTH_URL="http://127.0.0.1:8000/health"
CURRENT="$(cat .current_tag 2>/dev/null || true)"

echo "deploying $TAG (current: ${CURRENT:-none})"
IMAGE_TAG="$TAG" "${COMPOSE[@]}" pull --quiet api worker
IMAGE_TAG="$TAG" "${COMPOSE[@]}" up -d --remove-orphans

for i in $(seq 1 30); do
  if curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
    echo "healthy after ${i} check(s)"
    [ -n "$CURRENT" ] && echo "$CURRENT" > .previous_tag
    echo "$TAG" > .current_tag
    "${COMPOSE[@]}" ps
    exit 0
  fi
  sleep 2
done

echo "health check failed for $TAG" >&2
"${COMPOSE[@]}" logs --tail=50 api >&2 || true
if [ -n "$CURRENT" ]; then
  echo "rolling back to $CURRENT" >&2
  IMAGE_TAG="$CURRENT" "${COMPOSE[@]}" up -d --remove-orphans
fi
exit 1
