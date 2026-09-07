#!/usr/bin/env bash
# Roll back to the previously deployed image tag, or to an explicit one.
#
#   ./rollback.sh            uses .previous_tag
#   ./rollback.sh <tag>      any tag that exists in the registry
#
# Database schema changes are not rolled back by this script.
set -euo pipefail

cd "$(dirname "$0")"
TAG="${1:-$(cat .previous_tag 2>/dev/null || true)}"
[ -n "$TAG" ] || { echo "no previous tag recorded; pass one explicitly" >&2; exit 1; }
exec ./deploy.sh "$TAG"
