# 작업 history

큰 그림은 [CLAUDE.md](CLAUDE.md). 시간 순서대로 무엇을 했고 무엇이 막혔는지.

## 1. 초기 분석 (가천대)

- 페이지: `https://www.gachon.ac.kr/kor/1075/subview.do`
- 정적 HTML, `?year=Y&month=M` 으로 월별 직접 접근 가능
- `.sche-comt tbody tr` 의 `th`(날짜) / `td`(일정명) 추출
- **SSL 이슈**: 가천대 서버가 약한 cipher만 받아서 Python urllib3 기본 거부
  → `LegacyTLSAdapter` + SECLEVEL=1 로 우회 (현재 가천대 크롤러 코드)
- 사용자는 처음에 Selenium 고집(과거 경험상 fetch가 안 됐다고 함). LegacyTLSAdapter 시연 후 사실 fetch만으로도 됐었음 확인. 그래도 Selenium 유지

## 2. 첫 PR 시리즈 — Railway 배포

| PR | 내용 | 비고 |
| --- | --- | --- |
| #1 | 초기 구현 (FastAPI + Selenium + PostgreSQL) | 머지 |
| #2 | `DATABASE_URL` prefix 자동 보정 (`postgres://` → `postgresql+psycopg://`) | 머지 |
| #3 | Dockerfile에 `${PORT:-8000}` fallback + exec uvicorn | 머지 |
| #5 | `railway.json`에서 startCommand 제거 (Railway가 exec form으로 실행해서 `&&`, `${VAR:-x}` 다 깨졌음) | 머지. Railway Diagnose가 짚어줌 |

**교훈**: Railway의 Dockerfile builder는 `railway.json.startCommand`를 shell 없이 실행. shell 문법 필요하면 Dockerfile CMD에 `["sh", "-c", "..."]`로.

## 3. 기능 추가

- **PR #4**: 카테고리 필터링 — DB schema 변경 없이 keyword 동적 매칭. URL `?categories=tuition,exam`. 학교 페이지에 chip UI
- **PR #6**: 동서울대 추가 + UI 개선
  - 동서울대는 `/ajax/ScheduleListDataMonth.do` JSON POST API → Selenium 불필요, requests로 충분
  - "전체 받기" 모드에서 chip을 `disabled`로 dim 처리 (이전엔 hidden이었음)
  - `update_schools`가 부분 삭제 → 전체 삭제로 변경 (가천대 페이지가 오늘보다 과거 시작 일정도 노출해 unique 충돌)
  - 카테고리 keyword 보강 (`기말시험`, `계절수업` 등)

## 4. mac mini cron 준비

- **PR #7**: `ops/mac-cron/` 디렉토리
  - `install.sh`: Docker image build + launchd plist 등록 + 1회 검증 실행
  - `run.sh`: 매일 03:00 trigger되는 wrapper (docker run --rm)
  - `uninstall.sh`: launchd 해제
  - `com.campus-ical.cron.plist.template`: macOS LaunchAgent
  - 사용자는 mac mini에서 `git clone` → `cp .env.example .env` (DATABASE_URL 채움) → `./install.sh` 한 번
- Railway trial 종료 시 cron만 mac mini로 옮길 준비

## 5. Supabase 이주

### 5.1 옵션 비교
- A: DB만 Supabase + Railway 그대로 (작업 30분, 비용 그대로)
- B: 전체 Edge Functions로 (가천대 SSL 이슈로 **불가**)
- D: Web Edge Function + mac mini cron (작업 반나절, 장기 비용 0)
- E: 전부 mac mini (코드 변경 0, 24/7 켜둠)

사용자가 D 선택.

### 5.2 진행
1. Supabase 프로젝트 `campus-ical` (rhjovcmtvzhqublrqxic, ap-northeast-2)
2. schema 생성 (schools + events) + RLS 활성화 (우리 앱은 service_role로 우회)
3. Connection string 형식 함정:
   - 옛 pooler: `aws-0-{region}.pooler.supabase.com`
   - 새 프로젝트: `aws-1-{region}.pooler.supabase.com` (사용자가 대시보드에서 확인)
4. Railway web/cron의 `DATABASE_URL` 교체 (psycopg3 prefix `postgresql+psycopg://`)
5. cron service의 DATABASE_URL은 `postgresql://`로 박혀 있어 psycopg2 import 실패 → web과 동일하게 prefix 교체

### 5.3 PR #8 — Edge Function `web` 작성
- `supabase/functions/web/index.ts` 단일 router
- `lib/categories.ts` (Python 포팅), `lib/ical.ts` (직접 VCALENDAR 생성), `lib/html.ts` (template literal)
- 로고는 jsDelivr CDN 경유
- 첫 deploy에서 `lib/html.ts` placeholder 박은 실수 → v2 재배포
- 동작 확인: `/`, `/s/{slug}`, `/calendar/{slug}.ics`, 카테고리 필터 모두 OK (curl 기준)

## 6. brower quirk — root cause 확정 (2026-05-27 재진단)

### 증상
- Supabase Edge Function HTML 응답이 **macOS Safari, macOS Chrome, iPhone Safari** 모두에서 raw text + 한국어 mojibake
- Safari Web Inspector로 보면 `<body>` 안에 `<pre>` 하나만 박혀 있음 → brower가 plain text로 인식

### root cause (Supabase 의도된 정책)
공식 docs (Storage Quickstart, Files 섹션) 인용:
> "For security, **HTML files are returned as plain text**."

응답 헤더 검증 결과:
- 우리가 `Content-Type: text/html; charset=utf-8` 보내도 → 응답은 `content-type: text/plain`
- `content-security-policy: default-src 'none'; sandbox` 자동 추가
- `x-content-type-options: nosniff` 자동 추가 → brower sniffing 차단
- Edge Function, Storage public, Storage authenticated, REST API 등 모든 경로 검증 결과: **HTML/JS 콘텐츠는 모두 text/plain으로 강제 변환** (이미지/JSON은 원본 유지)

이는 *.supabase.co 도메인 abuse 방지를 위한 의도된 정책. **anon key 인증, Authorization Bearer, ?apikey=, Custom Domain 모두 우회 불가능** (Custom Domain docs는 명시적으로 "frontend hosting 용도 아님" 명시).

### 실패한 시도들 (전부 root cause를 비껴감)
1. BOM 추가 — text/plain은 그대로
2. nosniff 제거 — Supabase가 자동 재추가
3. Binary 응답 — Content-Type만 강제 변환
4. 여러 brower — 모두 동일 (당연. 서버 응답이 동일)

### 결론
**Supabase는 정적 HTML/JS frontend hosting 용도가 아님**. 백엔드(DB/Auth/Storage[미디어]/Edge Functions[API])용. Frontend는 별도 호스팅 필수.
- 정적 HTML → **Cloudflare Pages** (무료 *.pages.dev 서브도메인)
- iCal endpoint는 그대로 Supabase Edge Function 유지 (캘린더 앱이 ics 파일로 fetch하므로 brower quirk 영향 없음)

## 7. 정적 HTML 우회 (feat-static-pages branch)

- `docs/index.html` (학교 목록), `docs/s/{slug}.html` 두 개, `docs/style.css`, `docs/subscribe.js`
- 로고는 jsDelivr CDN
- iCal URL은 Supabase Edge Function URL을 학교 페이지에 박음
- 학생 흐름: 정적 HTML → URL 복사 → 캘린더 앱에 등록 → 캘린더가 Supabase에서 iCal fetch
- **GitHub Pages URL이 작동하지 않음** (사용자 명시) → 다른 정적 호스팅 옵션 필요

## 8. 현재 미정

- 정적 HTML을 어디에 호스팅할지 (GitHub Pages 안 됨)
- mac mini에 cron 활성화 시점
- Railway web 서비스 종료 시점 (정적 호스팅 결정 후)

## 9. 정리되지 않은 PR/branch

- `feat-static-pages` (push 안 됨, 보류 중)
- `feat-edge-functions-web` (PR #8 머지 여부 확인 필요)
- `mac-cron-setup` (PR #7 머지 완료 추정)
- 원격 `deploy`, `initial-deploy` (초기 임시 branch, 정리 가능)
