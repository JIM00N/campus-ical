"""한림대학교 학사일정 크롤러.

``1062/subview.do?year={Y}&month={M}`` 로 월 단위 학사일정 list를 받는다
(``.sche-comt`` table). 가천대와 같은 subview.do CMS지만 한림대는 SSL/JS
이슈가 없어 requests로 충분하다. 미래 12개월을 month-by-month로 받는다.

``<th>`` 에 ``2026.05.01(금)`` 처럼 연·월·일이 다 들어 있어 연도 추론이
필요 없다. ``list_hldy`` row(어린이날 등 법정공휴일)는 학사일정이 아니라
제외한다.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterable

import requests
from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler, RawEvent
from app.crawlers.registry import register_crawler

BASE_URL = "https://www.hallym.ac.kr/hallym/1062/subview.do"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
HORIZON_MONTHS = 12
DATE_RE = re.compile(r"(\d{4})\.(\d{1,2})\.(\d{1,2})")


@register_crawler
class HallymCrawler(BaseCrawler):
    key = "hallym"

    def fetch(self) -> Iterable[RawEvent]:
        today = date.today()
        seen: set[tuple[str, date, date]] = set()
        year, month = today.year, today.month
        for _ in range(HORIZON_MONTHS):
            for ev in self._fetch_month(year, month):
                if ev.dtstart < today:
                    continue
                identity = (ev.summary, ev.dtstart, ev.dtend)
                if identity in seen:
                    continue
                seen.add(identity)
                yield ev
            month += 1
            if month > 12:
                month = 1
                year += 1

    def _fetch_month(self, year: int, month: int) -> list[RawEvent]:
        resp = requests.get(
            BASE_URL,
            params={"year": str(year), "month": str(month)},
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        table = soup.select_one(".sche-comt table tbody")
        if table is None:
            return []

        events: list[RawEvent] = []
        for tr in table.find_all("tr"):
            if "list_hldy" in (tr.get("class") or []):
                continue
            th = tr.find("th")
            td = tr.find("td")
            if th is None or td is None:
                continue
            summary = td.get_text(strip=True)
            if not summary:
                continue
            parsed = _parse_full_dates(th.get_text(strip=True))
            if parsed is None:
                continue
            dtstart, dtend = parsed
            # 한 달 페이지에 인접 월 일정이 섞일 수 있으니 시작 월만 채택
            # (다른 월은 그 월 page에서 다시 yield된다).
            if dtstart.month != month or dtstart.year != year:
                continue
            events.append(RawEvent(summary=summary, dtstart=dtstart, dtend=dtend))
        return events


def _parse_full_dates(text: str) -> tuple[date, date] | None:
    """'2026.05.01(금)' 또는 '2026.05.26(화) ~ 2026.05.28(목)' → (start, end-excl)."""
    matches = DATE_RE.findall(text)
    if not matches:
        return None
    try:
        dtstart = date(int(matches[0][0]), int(matches[0][1]), int(matches[0][2]))
        last = matches[1] if len(matches) > 1 else matches[0]
        end_inclusive = date(int(last[0]), int(last[1]), int(last[2]))
    except ValueError:
        return None
    if end_inclusive < dtstart:
        return None
    return dtstart, end_inclusive + timedelta(days=1)
