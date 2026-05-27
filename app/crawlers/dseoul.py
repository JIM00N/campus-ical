"""동서울대학교 학사일정 크롤러.

페이지는 정적 HTML이지만 일정 데이터는 ``/ajax/ScheduleListDataMonth.do``에
POST해서 학년도(SCH_YEAR) 단위 JSON으로 받는다. 한 번 호출로 그 학년도
1년치를 모두 받으므로 Selenium 없이 requests만 쓴다.

학교가 노출하는 모든 미래 학사일정을 가져온다 — 현재 학년도 + 다음 학년도
(다음 학년도 API가 빈 응답이면 자연히 skip). 과거 일정은 제외.
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

    def fetch(self) -> Iterable[RawEvent]:
        today = date.today()
        # 현재 학년도 + 다음 학년도. 다음 학년도 데이터가 아직 없으면
        # API가 빈 list를 반환해서 자연히 skip된다.
        years_to_fetch = [today.year, today.year + 1]

        seen: set[tuple[str, date, date]] = set()
        for year in years_to_fetch:
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
