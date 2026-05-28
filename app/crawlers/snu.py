"""서울대학교 학사일정 크롤러.

``/academics/resources/calendar?year={학년도}`` 한 페이지에 한 학년도(3월~다음
2월) 전체가 ``.calendar-wrap > .work-wrap`` (월별) 구조로 들어 있다. 미래를
덮기 위해 현재 학년도 + 다음 학년도를 받는다 (다음 학년도 페이지가 비어
있으면 자연히 skip).

날짜 표기:
- 단일일: ``01(일)``
- 같은 달 범위: ``03(화) ~ 09(월)``
- 다른 달 범위: ``30(월) ~ 04.03.(금)`` (종료측에 MM.DD. 명시)

학년도 Y의 월 M → 달력연도: M>=3 이면 Y, M<=2 이면 Y+1.
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

BASE_URL = "https://www.snu.ac.kr/academics/resources/calendar"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
MONTH_RE = re.compile(r"(\d{1,2})월")
# 한 토큰: 'MM.DD.' (월 명시) 또는 'DD(' (일만)
MD_TOKEN_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.")
DAY_TOKEN_RE = re.compile(r"(\d{1,2})\(")


@register_crawler
class SnuCrawler(BaseCrawler):
    key = "snu"

    def fetch(self) -> Iterable[RawEvent]:
        today = date.today()
        # 학년도: 3월 이후면 올해, 1~2월이면 작년이 현재 학년도.
        acad_year = today.year if today.month >= 3 else today.year - 1

        seen: set[tuple[str, date, date]] = set()
        for year in (acad_year, acad_year + 1):
            for ev in self._fetch_acad_year(year):
                if ev.dtstart < today:
                    continue
                identity = (ev.summary, ev.dtstart, ev.dtend)
                if identity in seen:
                    continue
                seen.add(identity)
                yield ev

    def _fetch_acad_year(self, acad_year: int) -> list[RawEvent]:
        resp = requests.get(
            BASE_URL,
            params={"year": str(acad_year)},
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        events: list[RawEvent] = []
        for wrap in soup.select(".calendar-wrap .work-wrap"):
            month_el = wrap.select_one(".month-text")
            if month_el is None:
                continue
            m = MONTH_RE.search(month_el.get_text(strip=True))
            if not m:
                continue
            month = int(m.group(1))
            cal_year = acad_year if month >= 3 else acad_year + 1
            for work in wrap.select(".work"):
                day_el = work.select_one(".day")
                desc_el = work.select_one(".desc")
                if day_el is None or desc_el is None:
                    continue
                summary = desc_el.get_text(strip=True)
                if not summary:
                    continue
                parsed = _parse_day(day_el.get_text(strip=True), cal_year, month)
                if parsed is None:
                    continue
                dtstart, dtend = parsed
                events.append(RawEvent(summary=summary, dtstart=dtstart, dtend=dtend))
        return events


def _parse_side(token: str, default_month: int) -> tuple[int, int] | None:
    """범위의 한 쪽 토큰 → (month, day). 'MM.DD.' 우선, 없으면 'DD('."""
    md = MD_TOKEN_RE.search(token)
    if md:
        return int(md.group(1)), int(md.group(2))
    d = DAY_TOKEN_RE.search(token)
    if d:
        return default_month, int(d.group(1))
    return None


def _parse_day(text: str, cal_year: int, month: int) -> tuple[date, date] | None:
    parts = text.split("~")
    start = _parse_side(parts[0], month)
    if start is None:
        return None
    s_month, s_day = start

    if len(parts) > 1:
        end = _parse_side(parts[1], s_month)
        if end is None:
            return None
        e_month, e_day = end
    else:
        e_month, e_day = s_month, s_day

    s_year = cal_year
    # 시작 월이 컨텍스트 월과 달라도(드묾) 시작 월 기준으로 연도 유지.
    e_year = s_year + 1 if e_month < s_month else s_year
    try:
        dtstart = date(s_year, s_month, s_day)
        end_inclusive = date(e_year, e_month, e_day)
    except ValueError:
        return None
    if end_inclusive < dtstart:
        return None
    return dtstart, end_inclusive + timedelta(days=1)
