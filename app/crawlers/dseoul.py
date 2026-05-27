"""동서울대학교 학사일정 크롤러.

페이지는 정적 HTML로 보이지만 일정 데이터는 `/ajax/ScheduleListDataMonth.do`
에 POST해서 JSON으로 받아온다. 한 번 호출로 해당 학년도(SCH_YEAR) 1년치를
받으므로 Selenium 없이 requests만 쓴다.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable

import requests

from app.crawlers.base import BaseCrawler, RawEvent
from app.crawlers.registry import register_crawler

API_URL = "https://www.du.ac.kr/ajax/ScheduleListDataMonth.do"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


@register_crawler
class DseoulCrawler(BaseCrawler):
    key = "dseoul"

    def fetch(self, months_ahead: int) -> Iterable[RawEvent]:
        today = date.today()
        # cutoff = 오늘로부터 months_ahead개월 뒤(다음 달 1일 기준 N개월).
        cutoff_month = today.month + months_ahead
        cutoff_year = today.year + (cutoff_month - 1) // 12
        cutoff_month = ((cutoff_month - 1) % 12) + 1
        cutoff = date(cutoff_year, cutoff_month, 1)

        years_needed = {today.year}
        if cutoff.year != today.year:
            years_needed.add(cutoff.year)

        seen: set[tuple[str, date, date]] = set()
        for year in sorted(years_needed):
            for raw in self._fetch_year(year):
                ev = self._to_event(raw)
                if ev is None:
                    continue
                # 과거(오늘 이전 시작) 또는 cutoff 이후는 제외.
                if ev.dtstart < today or ev.dtstart >= cutoff:
                    continue
                identity = (ev.summary, ev.dtstart, ev.dtend)
                if identity in seen:
                    continue
                seen.add(identity)
                yield ev

    def _fetch_year(self, year: int) -> list[dict]:
        resp = requests.post(
            API_URL,
            data={"SCH_YEAR": str(year), "SCH_DEPT_CD": "", "SCH_CONTENTS_TYPE": ""},
            headers={
                "User-Agent": USER_AGENT,
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json",
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json() or []

    @staticmethod
    def _to_event(raw: dict) -> RawEvent | None:
        try:
            start = datetime.strptime(raw["START_DAY"], "%Y-%m-%d").date()
            end_inclusive = datetime.strptime(raw["END_DAY"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            return None
        summary = (raw.get("SUBJECT") or "").strip()
        if not summary:
            return None
        # iCal DTEND는 DATE 값에서 exclusive.
        return RawEvent(summary=summary, dtstart=start, dtend=end_inclusive + timedelta(days=1))
