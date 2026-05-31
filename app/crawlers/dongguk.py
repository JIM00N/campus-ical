"""동국대학교 학사일정 크롤러.

``/schedule/detail`` 은 파라미터 없이 호출하면 현재 학년도 교내일정 게시물을
자동으로 반환한다. 학년도마다 게시물 seq(``schedule_info_seq``)가 바뀌어도
기본값이 최신으로 갱신되므로 seq를 하드코딩할 필요가 없다. 정적 HTML이라
requests로 충분하다.

일정은 ``table.tbl tbody tr`` 의 row들이고, 각 row는 ``<td>`` 두 개 — 날짜와
제목이다. 날짜는 ``2026.03.01.`` 또는 ``2026.03.03. ~ 2026.03.09.`` 처럼 연·월·일이
다 들어 있어 추론이 필요 없다. 제목 ``<td>`` 안의 "바로가기"(``a``)와 주관부서(``p``)
는 일정명이 아니라 제거한다.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterable

import requests
from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler, RawEvent
from app.crawlers.registry import register_crawler

BASE_URL = "https://www.dongguk.edu/schedule/detail"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
DATE_RE = re.compile(r"(\d{4})\.(\d{1,2})\.(\d{1,2})")


@register_crawler
class DonggukCrawler(BaseCrawler):
    key = "dongguk"

    def fetch(self) -> Iterable[RawEvent]:
        today = date.today()
        seen: set[tuple[str, date, date]] = set()
        for ev in self._fetch_table():
            if ev.dtstart < today:
                continue
            identity = (ev.summary, ev.dtstart, ev.dtend)
            if identity in seen:
                continue
            seen.add(identity)
            yield ev

    def _fetch_table(self) -> list[RawEvent]:
        resp = requests.get(BASE_URL, headers={"User-Agent": USER_AGENT}, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        tbody = soup.select_one("table.tbl tbody")
        if tbody is None:
            return []

        events: list[RawEvent] = []
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue
            date_td, title_td = tds[0], tds[1]
            # 제목 td의 '바로가기' 링크(a)와 주관부서(p)는 일정명이 아니라 제거
            for junk in title_td.select("a, p"):
                junk.extract()
            summary = title_td.get_text(strip=True)
            if not summary:
                continue
            parsed = _parse_full_dates(date_td.get_text(strip=True))
            if parsed is None:
                continue
            dtstart, dtend = parsed
            events.append(RawEvent(summary=summary, dtstart=dtstart, dtend=dtend))
        return events


def _parse_full_dates(text: str) -> tuple[date, date] | None:
    """'2026.03.01.' 또는 '2026.03.03. ~ 2026.03.09.' → (start, end-excl)."""
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
