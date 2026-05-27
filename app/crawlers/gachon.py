from __future__ import annotations

import re
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Iterable

from selenium.webdriver import Firefox, FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.crawlers.base import BaseCrawler, RawEvent
from app.crawlers.registry import register_crawler

BASE_URL = "https://www.gachon.ac.kr/kor/1075/subview.do"
PERIOD_RE = re.compile(r"(\d{1,2})\.(\d{1,2})(?:\s*~\s*(\d{1,2})\.(\d{1,2}))?")
TABLE_SELECTOR = ".sche-comt tbody"


@contextmanager
def _firefox():
    opts = FirefoxOptions()
    opts.add_argument("-headless")
    opts.set_preference("intl.accept_languages", "ko-KR,ko")
    driver = Firefox(options=opts)
    driver.set_page_load_timeout(30)
    try:
        yield driver
    finally:
        driver.quit()


@register_crawler
class GachonCrawler(BaseCrawler):
    key = "gachon"

    def fetch(self, months_ahead: int) -> Iterable[RawEvent]:
        today = date.today()
        seen: set[tuple[str, date, date]] = set()
        year, month = today.year, today.month

        with _firefox() as driver:
            for _ in range(months_ahead):
                for ev in self._fetch_month(driver, year, month):
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
            # Only keep rows whose start month matches the page month.
            # Other months on the same page are duplicates from neighboring pages.
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
