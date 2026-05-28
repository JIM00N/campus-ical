"""한국체육대학교 학사일정 크롤러.

``academic-schedule.do?mode=list&cYear={Y}&allYn=Y`` 로 한 달력연도(cYear)의
12개월치 일정을 한 페이지에 받는다 (allYn=Y = 전체 월). cYear는 달력연도라
1월~12월이 모두 해당 연도 (학년도 아님 — 3월 1학기 개강, 9월 2학기 개강,
12월 2학기 종강이 모두 같은 cYear에 묶임). 미래를 덮기 위해 올해+내년을 받는다.

정적 HTML이라 selenium 없이 requests만 쓴다.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterable

import requests
from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler, RawEvent
from app.crawlers.registry import register_crawler

BASE_URL = "https://www.knsu.ac.kr/knsu/academic/academic-schedule.do"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
MONTH_RE = re.compile(r"(\d{1,2})월")
DAY_RANGE_RE = re.compile(
    r"(\d{1,2})\([월화수목금토일]\)(?:\s*~\s*(\d{1,2})\([월화수목금토일]\))?"
)


@register_crawler
class KnsuCrawler(BaseCrawler):
    key = "knsu"

    def fetch(self) -> Iterable[RawEvent]:
        today = date.today()
        seen: set[tuple[str, date, date]] = set()
        for year in (today.year, today.year + 1):
            for ev in self._fetch_year(year):
                if ev.dtstart < today:
                    continue
                identity = (ev.summary, ev.dtstart, ev.dtend)
                if identity in seen:
                    continue
                seen.add(identity)
                yield ev

    def _fetch_year(self, year: int) -> list[RawEvent]:
        resp = requests.get(
            BASE_URL,
            params={"mode": "list", "cYear": str(year), "allYn": "Y"},
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        box = soup.select_one(".b-cal-list-box")
        if box is None:
            return []

        events: list[RawEvent] = []
        for group in box.find_all("div", recursive=False):
            head = group.find("p")
            if head is None:
                continue
            m = MONTH_RE.match(head.get_text(strip=True))
            if not m:
                continue
            month = int(m.group(1))
            for ul in group.find_all("ul"):
                li = ul.find("li")
                date_p = ul.parent.find("p")
                if li is None or date_p is None:
                    continue
                summary = li.get_text(strip=True)
                if not summary:
                    continue
                parsed = _parse_day_range(date_p.get_text(strip=True), year, month)
                if parsed is None:
                    continue
                dtstart, dtend = parsed
                events.append(RawEvent(summary=summary, dtstart=dtstart, dtend=dtend))
        return events


def _parse_day_range(text: str, year: int, month: int) -> tuple[date, date] | None:
    """'5(월) ~ 9(금)' (day-only, month from context) → (dtstart, dtend-exclusive).

    종료일이 시작일보다 작으면 다음 달로 넘어간 것으로 본다.
    """
    m = DAY_RANGE_RE.search(text)
    if not m:
        return None
    s_day = int(m.group(1))
    e_day = int(m.group(2)) if m.group(2) else s_day

    s_month, s_year = month, year
    e_month, e_year = month, year
    if e_day < s_day:
        e_month += 1
        if e_month > 12:
            e_month = 1
            e_year += 1
    try:
        dtstart = date(s_year, s_month, s_day)
        end_inclusive = date(e_year, e_month, e_day)
    except ValueError:
        return None
    return dtstart, end_inclusive + timedelta(days=1)
