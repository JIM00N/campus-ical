# mac mini에서 cron 돌리기

가천대 Selenium 크롤러를 mac mini에서 매일 한 번 실행시키는 가이드.
Supabase Postgres에 직접 INSERT하므로 외부 노출 없음(outbound HTTPS만).

## 사전 준비 (한 번만)

1. **Docker Desktop** 설치 (또는 colima): https://www.docker.com/products/docker-desktop
2. **mac mini가 sleep 중에도 깨어 cron 실행**하도록:
   - System Settings → Battery / Energy → "Prevent automatic sleeping when display is off" 켜기
   - 또는 03:00 부근에 깨우도록 `sudo pmset repeat wake MTWRFSU 02:55:00`

## 설치

```bash
git clone git@github.com:JIM00N/campus-ical.git
cd campus-ical/ops/mac-cron

# 환경변수 파일 만들기 (DATABASE_URL 채워야 함)
cp .env.example .env
$EDITOR .env

# 설치 (Docker build + launchd 등록 + 즉시 1회 검증)
./install.sh
```

설치 스크립트가 자동으로:
- Firefox 포함 Docker image 빌드 (`campus-ical-cron:local`)
- launchd plist 등록 (`~/Library/LaunchAgents/com.campus-ical.cron.plist`)
- 매일 03:00에 자동 실행되도록 스케줄
- 즉시 한 번 실행해 동작 검증

## 수동 실행

```bash
ops/mac-cron/run.sh
```

(설치 안 한 상태에서도 `.env`만 있으면 동작)

## 로그 확인

```bash
tail -f ~/Library/Logs/campus-ical/cron.log
```

## 스케줄 확인

```bash
launchctl list | grep com.campus-ical.cron
```

## 코드 업데이트하기

크롤러나 카테고리 등 코드를 새로 받아온 뒤:

```bash
git pull
docker build -t campus-ical-cron:local ../..
```

(launchd는 그대로 두면 다음 실행부터 새 image 사용)

## 해제

```bash
./uninstall.sh
```

launchd만 해제. Docker image, 로그, 레포는 직접 정리.

## 자주 묻는 것

**Q. mac mini가 꺼져 있으면?**
A. 그 날 cron은 안 돕니다. 다음 켜졌을 때 자동 catch-up 안 함. 24/7 유지 권장.

**Q. 다른 학교 추가하려면?**
A. `app/crawlers/` 에 새 크롤러 추가 → `scripts/seed_schools.py` 에 학교 한 줄 → `git pull && docker build` 만 mac mini에서. 다음 cron부터 자동 수집.

**Q. 크롤링 즉시 다시 돌리고 싶으면?**
A. `ops/mac-cron/run.sh` 그냥 실행. launchd 스케줄과 무관.
