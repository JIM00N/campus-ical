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
| iCal 피드 (`/calendar/{slug}.ics`) | Supabase Edge Function `web` | 캘린더 앱이 직접 fetch |
| 학생용 HTML 페이지 | 정적 HTML / 다른 호스팅 | brower quirk로 Edge Function 못 씀 |
| 크롤러 cron (전 학교) | **mac mini** launchd (`ops/mac-cron`, 매일 03:00) | Docker 컨테이너 1회 실행 → `seed_schools && update_schools`. 코드 갱신은 mac mini에서 수동 `git pull && docker build` 필요 (자동 deploy 아님) |

## 코드/기술 제약

- **가천대 SSL handshake**: 가천대 서버가 약한 cipher만 받음. Python은 `LegacyTLSAdapter` + SECLEVEL=1 로 우회. Deno fetch (Edge Function)는 우회 불가 → Selenium 또는 Python `requests` (특수 어댑터)만 가능
- **Supabase는 HTML/JS 정적 frontend 호스팅 용도가 아님** (★중요): Supabase 공식 docs (Storage Quickstart): "For security, HTML files are returned as plain text." Edge Function/Storage public 모두 HTML/JS 응답을 강제로 `content-type: text/plain` + `nosniff` + sandbox CSP로 변환. anon key 인증, Custom Domain 모두 우회 불가. 미디어(image/gif/video)는 정상 서빙. → **정적 HTML은 Cloudflare Pages 같은 외부 호스팅**, iCal endpoint(캘린더 앱이 fetch — brower quirk 영향 없음)만 Supabase Edge Function 유지
- **GitHub Pages URL은 작동하지 않음** (사용자 명시). 사용 호스팅: **Cloudflare Pages** (무료 *.pages.dev)
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

## 학교 추가 절차

1. `app/crawlers/<slug>.py` 작성 (`BaseCrawler` 상속, `@register_crawler`)
2. `app/crawlers/__init__.py` 에 import 추가
3. `scripts/seed_schools.py` `SCHOOLS` 리스트에 한 줄
4. `static/logos/<slug>.{png,svg}` 로고
5. (Edge Function 측에서도 schools 테이블 select하므로 별도 작업 없음)

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
- Cloudflare: 도메인 등록, Worker 작성
- GitHub: 머지 (자가 머지 금지)

## 작업 history는 [session-log.md](session-log.md) 참조
