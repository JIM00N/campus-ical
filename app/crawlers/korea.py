"""고려대학교(서울) 학사일정 크롤러.

``registrar.korea.ac.kr/eduinfo/affairs/schedule.do`` 는 학기 단위로 일정을
보여준다. 학기 select(``#sCateYear``)의 option이 학년도→srCategoryId1 값을
주고, ``?cYear={학년도}&hakGi={1|2}&srCategoryId1={값}`` 로 특정 학기 표를
받는다. 현재 학년도와 (있으면) 다음 학년도의 1·2학기를 받는다.

표는 ``.college_schedule table`` 의 row들이고, 월은 ``<th><span class="monthN">``
로 rowspan 묶여 있다. 날짜는 ``2(월)~25(수)`` 처럼 일만 — 학년도/학기와 월로
달력연도를 추론한다:
- 1학기: 모든 월 → 학년도 Y (2~8월)
- 2학기: 7월 이상 → Y, 1~2월 → Y+1

정적 HTML이라 requests만 쓴다.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterable

import requests
from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler, RawEvent
from app.crawlers.registry import register_crawler

BASE_URL = "https://registrar.korea.ac.kr/eduinfo/affairs/schedule.do"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
MONTH_RE = re.compile(r"(\d{1,2})월")
DAY_RANGE_RE = re.compile(
    r"(\d{1,2})\([월화수목금토일]\)\s*(?:~\s*(\d{1,2})\([월화수목금토일]\))?"
)


@register_crawler
class KoreaCrawler(BaseCrawler):
    key = "korea"

    def fetch(self) -> Iterable[RawEvent]:
        today = date.today()
        acad_year = today.year if today.month >= 3 else today.year - 1

        year_to_cat = self._load_category_map()
        seen: set[tuple[str, date, date]] = set()
        for year in (acad_year, acad_year + 1):
            cat = year_to_cat.get(year)
            if cat is None:
                continue
            for term in (1, 2):
                for ev in self._fetch_term(year, term, cat):
                    if ev.dtstart < today:
                        continue
                    identity = (ev.summary, ev.dtstart, ev.dtend)
                    if identity in seen:
                        continue
                    seen.add(identity)
                    yield ev

    def _load_category_map(self) -> dict[int, str]:
        soup = self._get()
        select = soup.select_one("select#sCateYear")
        out: dict[int, str] = {}
        if select is None:
            return out
        for opt in select.find_all("option"):
            y, val = opt.get("data-year"), opt.get("value")
            if y and val and y.isdigit():
                out[int(y)] = val
        return out

    def _fetch_term(self, year: int, term: int, cat: str) -> list[RawEvent]:
        soup = self._get({"cYear": str(year), "hakGi": str(term), "srCategoryId1": cat})
        table = soup.select_one(".college_schedule table")
        if table is None:
            return []

        events: list[RawEvent] = []
        current_month: int | None = None
        for tr in table.find_all("tr"):
            th = tr.find("th")
            if th is not None:
                m = MONTH_RE.search(th.get_text(strip=True))
                if m:
                    current_month = int(m.group(1))
            date_td = tr.find("td", class_="dateInfo")
            if date_td is None or current_month is None:
                continue
            desc_td = next(
                (td for td in tr.find_all("td") if "dateInfo" not in (td.get("class") or [])),
                None,
            )
            if desc_td is None:
                continue
            summary = desc_td.get_text(strip=True)
            if not summary:
                continue
            cal_year = _calendar_year(year, term, current_month)
            parsed = _parse_day_range(date_td.get_text(strip=True), cal_year, current_month)
            if parsed is None:
                continue
            dtstart, dtend = parsed
            events.append(RawEvent(summary=summary, dtstart=dtstart, dtend=dtend))
        return events

    def _get(self, params: dict | None = None) -> BeautifulSoup:
        resp = requests.get(
            BASE_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=20
        )
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")


def _calendar_year(acad_year: int, term: int, month: int) -> int:
    if term == 1:
        return acad_year
    return acad_year if month >= 7 else acad_year + 1


def _parse_day_range(text: str, year: int, month: int) -> tuple[date, date] | None:
    m = DAY_RANGE_RE.search(text)
    if not m:
        return None
    s_day = int(m.group(1))
    e_day = int(m.group(2)) if m.group(2) else s_day

    e_month, e_year = month, year
    if e_day < s_day:
        e_month += 1
        if e_month > 12:
            e_month = 1
            e_year += 1
    try:
        dtstart = date(year, month, s_day)
        end_inclusive = date(e_year, e_month, e_day)
    except ValueError:
        return None
    return dtstart, end_inclusive + timedelta(days=1)
