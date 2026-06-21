"""홍익대학교 학사일정 크롤러.

학사일정 list view(``academic-schedule001.do``)는 ``.dataBucket``을 JS Ajax로
채운다. Ajax는 SSO 프록시 ``/sso/APICipher.jsp``에 POST해서 내부
``/schedule/get_schedule.php?GUBUN=0&YEAR={연도}`` 결과(JSON)를 받아온다
(get_schedule.php 직접 호출은 에러 페이지 반환 → 프록시 경유 필수). 정적
JSON이라 selenium 없이 requests로 충분하다.

응답 item:
- ``TITLE``  URL-encoded 한글 일정명 (urllib.parse.unquote 필요)
- ``START`` / ``END``  "YYYY-MM-DD" 또는 월 단위 "YYYY-MM" (기간 별도 공지 항목)
- ``HOLY``  "1"이면 법정공휴일(삼일절·어린이날·개교기념일 등) → 학사일정 아님
- ``END``는 inclusive (그날까지 포함) → iCal DTEND용으로 +1일 해서 exclusive 변환

연도: ``YEAR=2026`` 한 번 호출이 직전 12월~다음해 2월(2025-12~2027-02)까지
담아주므로 올해+내년 두 번 호출하면 미래가 충분히 덮인다. 내년 데이터가
아직 없으면 빈 list라 자연히 skip. 과거(오늘 이전 시작) 일정·중복은 제외.
"""
from __future__ import annotations

import json
import urllib.parse
from calendar import monthrange
from datetime import date, timedelta
from typing import Iterable

import requests

from app.crawlers.base import BaseCrawler, RawEvent
from app.crawlers.registry import register_crawler

API_URL = "https://www.hongik.ac.kr/sso/APICipher.jsp"
LIST_REFERER = "https://www.hongik.ac.kr/kr/education/academic-schedule001.do"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


@register_crawler
class HongikCrawler(BaseCrawler):
    key = "hongik"

    def fetch(self) -> Iterable[RawEvent]:
        today = date.today()
        seen: set[tuple[str, date, date]] = set()
        for year in (today.year, today.year + 1):
            for raw in self._fetch_year(year):
                ev = self._to_event(raw)
                if ev is None or ev.dtstart < today:
                    continue
                identity = (ev.summary, ev.dtstart, ev.dtend)
                if identity in seen:
                    continue
                seen.add(identity)
                yield ev

    def _fetch_year(self, year: int) -> list[dict]:
        payload = json.dumps(
            {
                "url": "/schedule/get_schedule.php",
                "url2": "&GUBUN=",
                "url3": "0",
                "url4": "&YEAR=",
                "url5": str(year),
            }
        )
        resp = requests.post(
            API_URL,
            data={"data": payload},
            headers={
                "User-Agent": USER_AGENT,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": LIST_REFERER,
            },
            timeout=20,
        )
        resp.raise_for_status()
        # JSP가 응답 앞에 빈 줄을 붙여 보내므로 첫 '{'부터 파싱한다.
        text = resp.text
        brace = text.find("{")
        if brace < 0:
            return []
        try:
            doc = json.loads(text[brace:])
        except json.JSONDecodeError:
            return []
        return doc.get("data") or []

    @staticmethod
    def _to_event(raw: dict) -> RawEvent | None:
        if raw.get("HOLY") == "1":  # 법정공휴일은 학사일정 아님
            return None
        title = urllib.parse.unquote(raw.get("TITLE") or "").strip()
        if not title:
            return None
        parsed = _parse_span(raw.get("START") or "", raw.get("END") or "")
        if parsed is None:
            return None
        dtstart, dtend = parsed
        return RawEvent(summary=title, dtstart=dtstart, dtend=dtend)


def _parse_span(start_s: str, end_s: str) -> tuple[date, date] | None:
    """('YYYY-MM-DD'|'YYYY-MM', 동일) → (dtstart, dtend-exclusive)."""
    dtstart = _parse_point(start_s, end=False)
    if dtstart is None:
        return None
    end_inclusive = _parse_point(end_s or start_s, end=True)
    if end_inclusive is None or end_inclusive < dtstart:
        return None
    return dtstart, end_inclusive + timedelta(days=1)


def _parse_point(s: str, end: bool) -> date | None:
    """월 단위('YYYY-MM')면 시작은 1일, 종료는 그 달 마지막 날로 본다."""
    parts = s.split("-")
    try:
        if len(parts) >= 3:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        if len(parts) == 2:
            y, m = int(parts[0]), int(parts[1])
            return date(y, m, monthrange(y, m)[1] if end else 1)
    except (ValueError, IndexError):
        return None
    return None
