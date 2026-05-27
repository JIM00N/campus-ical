#!/bin/bash
# mac mini에서 한 번만 실행: Docker image build → launchd 등록 → 즉시 1회 검증 실행.
# 멱등(idempotent)이라 재실행해도 안전.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LABEL="com.campus-ical.cron"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs/campus-ical"
IMAGE="${IMAGE:-campus-ical-cron:local}"

log() { echo "[install] $*"; }

# 0. 사전 점검
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  log "ERROR: $SCRIPT_DIR/.env 가 없습니다."
  log "       cp $SCRIPT_DIR/.env.example $SCRIPT_DIR/.env 후 DATABASE_URL을 채워주세요."
  exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
  log "ERROR: docker가 없습니다. Docker Desktop 또는 colima를 먼저 설치해주세요."
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  log "ERROR: Docker daemon이 실행 중이 아닙니다. Docker Desktop을 실행해주세요."
  exit 1
fi

# 1. 이미지 빌드 (Firefox 포함)
log "Docker image 빌드 중: $IMAGE"
docker build -t "$IMAGE" "$REPO_ROOT"

# 2. 로그 디렉토리
mkdir -p "$LOG_DIR"
log "로그 디렉토리: $LOG_DIR"

# 3. launchd plist 생성 (template의 placeholder 치환)
mkdir -p "$HOME/Library/LaunchAgents"
sed \
  -e "s|__RUN_SH__|$SCRIPT_DIR/run.sh|g" \
  -e "s|__LOG_DIR__|$LOG_DIR|g" \
  "$SCRIPT_DIR/com.campus-ical.cron.plist.template" > "$PLIST_PATH"
chmod 644 "$PLIST_PATH"
log "plist 생성: $PLIST_PATH"

# 4. run.sh 실행권한
chmod +x "$SCRIPT_DIR/run.sh"

# 5. launchd 재등록 (이미 load되어 있으면 unload 먼저)
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"
log "launchd 등록 완료. 매일 새벽 03:00에 실행됩니다."

# 6. 즉시 한 번 실행해 검증
log "지금 한 번 실행해 동작 검증:"
log "----- begin run.sh -----"
"$SCRIPT_DIR/run.sh"
log "----- end run.sh -----"

cat <<EOF

설치 완료.

  스케줄    : 매일 03:00 (시스템 로컬 시간)
  로그      : $LOG_DIR/cron.log
  수동 실행 : $SCRIPT_DIR/run.sh
  해제      : $SCRIPT_DIR/uninstall.sh

다음 자동 실행 시각 확인:
  launchctl list | grep $LABEL
EOF
