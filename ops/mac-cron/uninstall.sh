#!/bin/bash
# launchd 등록 해제. Docker image / 로그 / 레포는 그대로 둠 (수동 정리).
set -euo pipefail

LABEL="com.campus-ical.cron"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ -f "$PLIST_PATH" ]; then
  launchctl unload "$PLIST_PATH" 2>/dev/null || true
  rm -f "$PLIST_PATH"
  echo "[uninstall] launchd 해제 + plist 삭제 완료."
else
  echo "[uninstall] plist가 없음. 이미 해제된 상태."
fi

cat <<EOF

해제 완료. 필요시 추가 정리:
  docker image rm campus-ical-cron:local
  rm -rf $HOME/Library/Logs/campus-ical
EOF
