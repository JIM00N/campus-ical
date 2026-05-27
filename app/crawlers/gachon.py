"""가천대학교 학사일정 크롤러.

가천대 학사일정 페이지는 ``?year=Y&month=M``로 월 단위 calendar view만
노출한다 (학년도/list view 같은 합본 endpoint 없음). 그래서 미래 12개월을
month-by-month로 selenium fetch 한다.

SSL: 가천대 서버는 약한 cipher만 허용해 Python urllib/requests 기본
SSLContext로는 handshake 실패. selenium의 brower 엔진이 자체 TLS stack
으로 우회한다 (별도 LegacyTLSAdapter 불필요).
"""
from __future__ import annotations

import os
import re
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Iterable

from selenium.webdriver import Firefox, FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.crawlers.base import BaseCrawler, RawEvent
from app.crawlers.registry import register_crawler

BASE_URL = "https://www.gachon.ac.kr/kor/1075/subview.do"
PERIOD_RE = re.compile(r"(\d{1,2})\.(\d{1,2})(?:\s*~\s*(\d{1,2})\.(\d{1,2}))?")
TABLE_SELECTOR = ".sche-comt tbody"
HORIZON_MONTHS = 12  # today부터 미래 12개월치 (학년도 1년 + 직전 학기 일부)


@contextmanager
def _firefox():
    opts = FirefoxOptions()
    opts.add_argument("-headless")
    opts.set_preference("intl.accept_languages", "ko-KR,ko")

    # Selenium Manager can't provision a driver on linux/aarch64. When the
    # image supplies explicit binary paths (see Dockerfile), use them so
    # Selenium skips Selenium Manager. Absent the env vars (amd64 / local dev),
    # fall back to the default path where Selenium Manager handles provisioning.
    firefox_bin = os.environ.get("FIREFOX_BIN")
    if firefox_bin:
        opts.binary_location = firefox_bin
    geckodriver_bin = os.environ.get("GECKODRIVER_BIN")
    service = FirefoxService(executable_path=geckodriver_bin) if geckodriver_bin else None

    driver = Firefox(options=opts, service=service)
    driver.set_page_load_timeout(30)
    try:
        yield driver
    finally:
        driver.quit()


@register_crawler
class GachonCrawler(BaseCrawler):
    key = "gachon"

    def fetch(self) -> Iterable[RawEvent]:
        today = date.today()
        seen: set[tuple[str, date, date]] = set()
        year, month = today.year, today.month

        with _firefox() as driver:
            for _ in range(HORIZON_MONTHS):
                for ev in self._fetch_month(driver, year, month):
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

    def _fetch_month(self, driver, year: int, month: int) -> list[RawEvent]:
        driver.get(f"{BASE_URL}?year={year}&month={month}")
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, TABLE_SELECTOR))
            )
        except Exception:
            return []

        rows = driver.find_elements(By.CSS_SELECTOR, f"{TABLE_SELECTOR} tr")
        events: list[RawEvent] = []
        for row in rows:
            try:
                period_text = row.find_element(By.TAG_NAME, "th").text.strip()
                summary = row.find_element(By.TAG_NAME, "td").text.strip()
            except Exception:
                continue
            parsed = self._parse_period(period_text, year, month)
            if not parsed:
                continue
            dtstart, dtend = parsed
            # 한 월 페이지에 인접 월의 일정도 보일 수 있는데, 다음 page에서
            # 다시 yield되므로 여기서는 시작 월이 page 월과 같은 것만 채택.
            if dtstart.month != month:
                continue
            events.append(RawEvent(summary=summary, dtstart=dtstart, dtend=dtend))
        return events

    @staticmethod
    def _parse_period(text: str, page_year: int, page_month: int) -> tuple[date, date] | None:
        m = PERIOD_RE.search(text)
        if not m:
            return None
        s_month, s_day = int(m.group(1)), int(m.group(2))
        e_month = int(m.group(3)) if m.group(3) else s_month
        e_day = int(m.group(4)) if m.group(4) else s_day

        start_year = page_year + 1 if s_month < page_month else page_year
        end_year = start_year + 1 if e_month < s_month else start_year

        try:
            dtstart = date(start_year, s_month, s_day)
            dtend_inclusive = date(end_year, e_month, e_day)
        except ValueError:
            return None
        return dtstart, dtend_inclusive + timedelta(days=1)
