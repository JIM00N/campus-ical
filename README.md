# ical-db

대학 학사일정을 매일 크롤링해서 DB에 저장하고, 학생이 본인 캘린더 앱(Google / Apple / Outlook)에 **URL 한 줄로 구독**할 수 있게 해 주는 서비스.

- 학사일정 페이지를 매일 크롤링 → PostgreSQL 저장
- `https://your-domain/calendar/{학교}.ics` 로 iCal 피드 제공
- 학교별로 로고 + URL 복사 버튼만 있는 페이지 (`/s/{학교}`) 제공
- Google AdSense 슬롯 내장 (Client/Slot ID만 환경변수로 채우면 활성화)
- 새 학교는 `app/crawlers/` 에 크롤러 한 개 + `scripts/seed_schools.py` 한 줄로 추가

현재 지원 학교: **가천대학교**

## 구조

```
app/
├── main.py                  # FastAPI 진입점
├── config.py                # 환경변수
├── db.py                    # SQLAlchemy 세션
├── models.py                # School / Event 모델
├── ical_generator.py        # DB → iCal 변환
├── routes/
│   ├── calendar.py          # /calendar/{slug}.ics
│   └── pages.py             # / , /s/{slug}
├── crawlers/
│   ├── base.py              # BaseCrawler / RawEvent
│   ├── registry.py          # 학교 → 크롤러 매핑
│   └── gachon.py            # 가천대 (Selenium)
└── tasks/
    └── update_schools.py    # cron 진입점 (전체 학교 재크롤링)
templates/                   # Jinja2 (base/index/school)
static/                      # CSS + 로고
scripts/
└── seed_schools.py          # 학교 메타데이터 시드 (idempotent)
```

## 로컬 실행

### 1. PostgreSQL 띄우기

```bash
docker run -d --name ical-pg -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=ical_db \
  postgres:16
```

### 2. 환경 / 의존성

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # DATABASE_URL 수정
```

`.env` 예시:
```
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ical_db
BASE_URL=http://localhost:8000
```

### 3. 학교 시드 + 첫 크롤링

```bash
python -m scripts.seed_schools          # schools 테이블에 가천대 등록
python -m app.tasks.update_schools      # 모든 학교 크롤링 (Selenium → Firefox 필요)
```

### 4. 서버 실행

```bash
uvicorn app.main:app --reload
```

- 학교 목록: http://localhost:8000/
- 가천대 페이지: http://localhost:8000/s/gachon
- iCal 피드: http://localhost:8000/calendar/gachon.ics

## 배포 (Railway)

1. Railway에서 **PostgreSQL** 플러그인 추가 → `DATABASE_URL` 자동 주입
2. 이 레포를 연결하면 `Dockerfile` 기반으로 빌드됨 (Firefox 포함)
3. 환경변수 설정:
   - `BASE_URL` = `https://<your-app>.up.railway.app`
   - (선택) `ADSENSE_CLIENT_ID`, `ADSENSE_SLOT_ID`
4. 별도 서비스로 **Cron** 작업 추가:
   - Command: `python -m app.tasks.update_schools`
   - Schedule: `0 3 * * *` (매일 새벽 3시 KST 기준 18:00 UTC면 `0 18 * * *`)
5. 웹 서비스는 시작 시 `scripts.seed_schools`를 자동 실행해 새 학교 메타데이터를 반영

## 새 학교 추가하는 방법

1. `app/crawlers/<school>.py` 작성:
   ```python
   from app.crawlers.base import BaseCrawler, RawEvent
   from app.crawlers.registry import register_crawler

   @register_crawler
   class FooCrawler(BaseCrawler):
       key = "foo"
       def fetch(self, months_ahead):
           ...
           yield RawEvent(summary=..., dtstart=..., dtend=...)
   ```
2. `app/crawlers/__init__.py` 에 `from app.crawlers import foo` 추가
3. `scripts/seed_schools.py` `SCHOOLS` 리스트에 학교 메타데이터 한 줄 추가
4. `static/logos/<slug>.svg` 로고 파일
5. 배포 → 다음 cron 실행 시 자동으로 데이터 수집

## 환경변수

| 이름 | 기본값 | 설명 |
| ---- | ------ | ---- |
| `DATABASE_URL` | localhost | SQLAlchemy 형식 (`postgresql+psycopg://...`) |
| `BASE_URL` | `http://localhost:8000` | iCal 피드 절대 URL 생성용 |
| `CRAWL_MONTHS_AHEAD` | `4` | 현재 월 포함 N개월치 크롤링 |
| `ADSENSE_CLIENT_ID` | (빈 값) | 비워두면 placeholder 박스만 표시 |
| `ADSENSE_SLOT_ID` | (빈 값) | 위와 같음 |
