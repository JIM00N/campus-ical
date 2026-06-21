"""이화여자대학교 학사일정 크롤러.

학부 학사일정은 연도별 정적 페이지 ``/ewha/bachelor/calendar{연도}.do``로
노출된다 (예: calendar2026.do). 한 페이지가 1월~12월 + 다음해 1·2월(총 14개
월그룹, 다음해 그룹은 "2027년 1월"처럼 연도 명시)을 담는다. 미래를 덮기 위해
올해+내년 페이지를 받는다 (내년 페이지가 아직 없으면 404 → 자연히 skip).

구조: ``.b-cal-list-box`` 안에 월그룹 div들 (첫 ``.b-cal-top-box``는 헤더라
skip). 각 월그룹 = 제목 ``<p>`` ("3월" 또는 "2027년 1월") + 일정 wrapper div.
wrapper 안 일정 div마다 날짜 ``<p>``와 ``<ul><li>`` 제목.

날짜는 일(day)만 노출 — 월그룹 제목의 연·월로 달력연도를 추론한다:
- "3(화)"            → 그룹 월의 그날 하루
- "14(수) ~ 19(월)"  → 같은 달 범위 (종료일이 작으면 다음 달로 넘어간 것)
- "28(월) ~ 10.2(금)" → 종료에 "월.일"이 명시되면 그 월을 쓴다

법정공휴일("(공휴일)" 표기: 신정·설날·삼일절 등)은 학사일정이 아니라 제외.
정적 HTML이라 requests로 충분하다. 과거(오늘 이전 시작)·중복은 제외.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterable

import requests
from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler, RawEvent
from app.crawlers.registry import register_crawler

BASE_URL = "https://www.ewha.ac.kr/ewha/bachelor/calendar{year}.do"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
LABEL_RE = re.compile(r"(?:(\d{4})\s*년)?\s*(\d{1,2})\s*월")
# 날짜 토큰: 선택적 "월." 접두 + 일 + "(요일)". 예: "14(수)", "10.2(금)"
POINT_RE = re.compile(r"(?:(\d{1,2})\.)?(\d{1,2})\s*\([월화수목금토일]\)")


@register_crawler
class EwhaCrawler(BaseCrawler):
    key = "ewha"

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
            BASE_URL.format(year=year),
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        box = soup.select_one(".b-cal-list-box")
        if box is None:
            return []

        events: list[RawEvent] = []
        for group in box.find_all("div", recursive=False):
            if "b-cal-top-box" in (group.get("class") or []):
                continue  # 표 헤더
            label_p = group.find("p", recursive=False)
            if label_p is None:
                continue
            m = LABEL_RE.search(label_p.get_text(" ", strip=True))
            if not m:
                continue
            base_year = int(m.group(1)) if m.group(1) else year
            base_month = int(m.group(2))

            # 일정 wrapper를 위치가 아니라 내용으로 찾는다: 첫 div가 공지/메타
            # 박스로 끼어들거나 "영문 학사일정" 블록이 채워져도 안전하도록,
            # 일정 div(날짜 <p> + <li> 보유)를 가진 첫 wrapper만 채택(=국문).
            for wrapper in group.find_all("div", recursive=False):
                ev_divs = [
                    d
                    for d in wrapper.find_all("div", recursive=False)
                    if d.find("p", recursive=False) is not None and d.find("li") is not None
                ]
                if not ev_divs:
                    continue
                for ev_div in ev_divs:
                    li = ev_div.find("li")
                    title = li.get_text(strip=True)
                    if not title or "없습니다" in title or "(공휴일)" in title:
                        continue
                    date_p = ev_div.find("p", recursive=False)
                    parsed = _parse_dates(date_p.get_text(" ", strip=True), base_year, base_month)
                    if parsed is None:
                        continue
                    dtstart, dtend = parsed
                    events.append(RawEvent(summary=title, dtstart=dtstart, dtend=dtend))
                break  # 국문 wrapper 처리 완료 — 이후 영문 등 wrapper는 skip
        return events


def _parse_dates(text: str, base_year: int, base_month: int) -> tuple[date, date] | None:
    """일(day) 위주 날짜 텍스트 → (dtstart, dtend-exclusive). 월은 그룹 컨텍스트."""
    points = POINT_RE.findall(text)  # [(month_opt, day), ...]
    if not points:
        return None

    s_month = int(points[0][0]) if points[0][0] else base_month
    s_day = int(points[0][1])
    try:
        dtstart = date(base_year, s_month, s_day)
    except ValueError:
        return None

    if len(points) > 1:
        e_mon_opt, e_day_s = points[1]
        e_day = int(e_day_s)
        if e_mon_opt:  # 종료에 월 명시 (예: "10.2")
            e_month = int(e_mon_opt)
            e_year = base_year + 1 if e_month < s_month else base_year
        else:  # 일만 — 작으면 다음 달
            e_month, e_year = s_month, base_year
            if e_day < s_day:
                e_month += 1
                if e_month > 12:
                    e_month, e_year = 1, base_year + 1
    else:
        e_month, e_year, e_day = s_month, base_year, s_day

    try:
        end_inclusive = date(e_year, e_month, e_day)
    except ValueError:
        return None
    if end_inclusive < dtstart:
        return None
    return dtstart, end_inclusive + timedelta(days=1)
