# CLAUDE.md

이 프로젝트에서 작업할 때의 지침 모음. 사용자가 명시했거나 작업 중 합의된 결정 사항.

## 사용자 / 환경

- 사용자 한국어 응답 선호
- **어조: 항상 존댓말. 반말 금지.** ("할게", "진행하자", "확인했어" 같은 반말체 사용 X → "하겠습니다", "진행하겠습니다", "확인했습니다")
- 사이드 프로젝트 (한국 대학 학사일정을 iCal로 구독 가능하게)
- mac mini 보유 (24/7 사용 가능). **현재 크롤러 cron 호스트 = mac mini** (Railway 역할 이관 완료, 2026-05-28)
- Supabase Pro plan 결제 중 (활용 의지)
- 도메인 `madeinkr.net` 보유, 후이즈 DNS

## 아키텍처 결정 (옵션 D 변형)

| 구성요소 | 위치 | 비고 |
| --- | --- | --- |
| DB | Supabase Postgres | 이주 완료 |
| iCal 피드 / 통계·복사 API (`/calendar/{slug}.ics`, `/stats`, `/copy/{slug}`) | Supabase Edge Function `web` | 아래 Worker가 프록시해서 호출 (학생에게 supabase.co 미노출). 캘린더 앱 fetch는 browser quirk 영향 없음 |
| 정적 페이지 + 라우팅 (학생용 HTML/CSS/JS) | **Cloudflare Worker `campus-ical`** — Workers + Static Assets (`docs/`, `wrangler.jsonc`), 도메인 campus-cal.com | 같은 워커가 정적 자산 서빙 + 위 `/calendar`·`/stats`·`/copy`를 Edge Function으로 프록시. **Pages 아님** |
| 크롤러 cron (전 학교) | **mac mini** launchd (`ops/mac-cron`, 매일 03:00) | Docker 컨테이너 1회 실행 → `seed_schools && update_schools`. 코드 갱신은 mac mini에서 수동 `git pull && docker build` 필요 (자동 deploy 아님) |

## 코드/기술 제약

- **가천대 SSL handshake**: 가천대 서버가 약한 cipher만 받음. Python은 `LegacyTLSAdapter` + SECLEVEL=1 로 우회. Deno fetch (Edge Function)는 우회 불가 → Selenium 또는 Python `requests` (특수 어댑터)만 가능
- **Supabase는 HTML/JS 정적 frontend 호스팅 용도가 아님** (★중요): Supabase 공식 docs (Storage Quickstart): "For security, HTML files are returned as plain text." Edge Function/Storage public 모두 HTML/JS 응답을 강제로 `content-type: text/plain` + `nosniff` + sandbox CSP로 변환. anon key 인증, Custom Domain 모두 우회 불가. 미디어(image/gif/video)는 정상 서빙. → **정적 HTML은 Cloudflare Worker(Static Assets)가 서빙**, iCal/통계/복사 endpoint(캘린더 앱·프론트가 fetch — browser quirk 영향 없음)만 Supabase Edge Function이 처리(워커가 프록시)
- **GitHub Pages URL은 작동하지 않음** (사용자 명시). 사용 호스팅: **Cloudflare Workers + Static Assets** (단일 워커 `campus-ical`, 커스텀 도메인 campus-cal.com — `*.pages.dev` Pages 아님)
- 로고는 jsDelivr CDN(`cdn.jsdelivr.net/gh/JIM00N/campus-ical@main/...`)으로 link

## UI 패턴

- 학교 페이지에 "전체 받기 / 골라 받기" 세그먼트 토글
- "전체 받기"일 땐 카테고리 chip이 dim + 클릭 불가 (`disabled` 클래스 + `disabled` attr)
- "골라 받기"로 전환 시 chip 활성화, 전환 시 체크 자동 해제
- URL 박스의 값은 카테고리 체크에 따라 동적 업데이트 (`?categories=tuition,exam` 패턴)
- "시작·끝만 표시" 토글 (`?endpoints=1`): 여러 날 일정을 시작일/종료일 두 개의 하루짜리 마커("… (시작)" / "… (종료)")로 분리. 중복 일정 많을 때 캘린더 정리용. 카테고리와 독립 (전체/골라 모두 적용). 구현은 ical(TS)/ical_generator(PY) 양쪽 `toEndpointEvents`/`to_endpoint_events`
- Google AdSense 슬롯 3개 (좌/우 sticky + 하단). client/slot ID 비면 placeholder 박스

## 카테고리 (동적 keyword 매칭, DB 컬럼 아님)

`tuition`, `registration`, `exam`, `major-change`, `leave`, `summer`, `withdrawal`, `graduation` — 정의는 [supabase/functions/web/lib/categories.ts](supabase/functions/web/lib/categories.ts) 와 [app/categories.py](app/categories.py). 공백 무시 normalize.

- **학교별 노출은 데이터 주도** (2026-06-02): ical 빌더가 매칭 카테고리를 각 VEVENT의 표준 `CATEGORIES:` 속성으로 출력하고, 프론트([docs/subscribe.js](docs/subscribe.js) `applyCategoryChips`)가 그 학교 `.ics`의 `CATEGORIES` 합집합으로 **실제 존재하는 칩만** 노출. 칩=실제 필터 결과라 "칩 보이는데 빈 결과" 모순 없음 (자퇴 없는 학교는 자퇴 칩 자동 제외). `.ics`에 `CATEGORIES`가 전혀 없으면 8칩 유지(배포 과도기 방어). **→ 학교 추가 시 카테고리 칩 수작업 불필요**

## 학교 추가 절차

1. `app/crawlers/<slug>.py` 작성 (`BaseCrawler` 상속, `@register_crawler`)
2. `app/crawlers/__init__.py` 에 import 추가
3. `scripts/seed_schools.py` `SCHOOLS` 리스트에 한 줄
4. `static/logos/<slug>.{png,svg}` 로고
5. `docs/s/<slug>.html` 학교 페이지 (기존 학교 HTML 복제 후 학교명·로고 URL(jsDelivr)·slug·`.ics` URL만 교체)
6. `docs/index.html` `.school-grid` 에 학교 카드 한 줄 추가 — **지원 학교 수(`#statsSchools`)는 카드 수로 자동 계산되니 수동 수정 불필요** (`subscribe.js`가 `.school-card` 개수를 셈)
7. **★ `docs/subscribe.js` `initChangelog`의 `entries` 맨 앞에 업데이트 내역 한 항목 추가 — Claude가 매번 직접 작성** (날짜·제목·`body`, "총 N개교 지원" 문구 포함)
8. 카테고리 칩: 데이터 주도라 별도 작업 없음 (위 "카테고리" 섹션 참조)
9. (Edge Function 측에서도 schools 테이블 select하므로 별도 작업 없음)

## PR / git 정책

- 새 작업마다 새 branch + PR
- **자가 머지 금지**: PR 만들면 사용자가 머지함
- force push 금지 (특히 main)
- 보호 정책상 destructive git 명령은 사용자 명시 동의 필요
- 첫 commit 때 author override 안 함 (사용자 글로벌 git config 그대로)

## 외부 작업이 필요한 (자동화 불가) 액션

- Supabase: 프로젝트 생성, DB password reset, RLS 정책 변경 권한
- mac mini cron: 코드 머지 후 mac mini에서 `git pull && docker build -t campus-ical-cron:local .` 후 다음 03:00 자동 실행 또는 `ops/mac-cron/run.sh`로 즉시 실행 (학교/일정 DB 반영)
- 후이즈: DNS nameserver 변경
- Cloudflare: 도메인 등록, Worker 라우트(campus-cal.com) 설정
- GitHub: 머지 (자가 머지 금지)

### ★ 운영 배포는 머지로 자동 안 됨 — 수동 필요 (2026-05-30 확인)

PR 머지는 Supabase **preview branch**만 갱신하고, 운영엔 아무것도 자동 배포되지 않는다 (배포 CI 없음). Edge Function 코드·`supabase/migrations/`·`docs/`·`worker/`를 건드린 PR은 **머지 후 아래를 직접 실행**해야 반영됨:

- **Cloudflare (프론트 `docs/` + 워커 `worker/`)**: repo root에서 `npx wrangler deploy` (`wrangler login` 필요 — Worker+Static Assets 한 번에 배포)
- **Supabase Edge Function `web`**: `supabase functions deploy web --project-ref rhjovcmtvzhqublrqxic` (CLI는 access token으로 이미 인증됨, `link` 불필요)
- **운영 마이그레이션**: 대시보드 SQL Editor에 마이그레이션 SQL 실행이 가장 빠름 (운영 DB 비번은 mac mini `ops/mac-cron/.env`에만 있고 repo `.env`는 localhost). 또는 Session pooler URL로 `supabase db push --db-url …`

## 작업 history는 [session-log.md](session-log.md) 참조
