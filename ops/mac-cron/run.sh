#!/bin/bash
# launchd가 매일 한 번 호출하는 진입점.
# 컨테이너 1회 실행 → seed_schools + update_schools → 종료.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "[$(date -Iseconds)] ERROR: $ENV_FILE not found. Copy .env.example and fill DATABASE_URL." >&2
  exit 1
fi

DOCKER_BIN="${DOCKER_BIN:-$(command -v docker || true)}"
if [ -z "$DOCKER_BIN" ]; then
  for p in /opt/homebrew/bin/docker /usr/local/bin/docker; do
    [ -x "$p" ] && DOCKER_BIN="$p" && break
  done
fi
if [ -z "$DOCKER_BIN" ]; then
  echo "[$(date -Iseconds)] ERROR: docker binary not found. Install Docker Desktop or colima." >&2
  exit 1
fi

IMAGE="${IMAGE:-campus-ical-cron:local}"

echo "[$(date -Iseconds)] starting cron run with image=$IMAGE"
"$DOCKER_BIN" run --rm \
  --env-file "$ENV_FILE" \
  --name campus-ical-cron-once \
  "$IMAGE" \
  sh -c "python -m scripts.seed_schools && python -m app.tasks.update_schools"
echo "[$(date -Iseconds)] cron run finished"
