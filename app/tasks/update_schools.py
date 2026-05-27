"""Cron entry point: 모든 학교를 재크롤링하고 미래 학사일정을 갱신.

Run: ``python -m app.tasks.update_schools [--slug gachon]``

각 크롤러가 학교 사이트 구조에 맞는 horizon으로 알아서 받아온다
(가천대 12개월 month-by-month, 동서울대 학년도 단위 등).
"""
from __future__ import annotations

import argparse
import logging
import sys

from sqlalchemy import delete, select

from app.crawlers import get_crawler
from app.db import session_scope
from app.models import Event, School

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("update_schools")


def update_school(session, school: School) -> int:
    crawler = get_crawler(school.crawler_key)
    log.info("crawling %s (key=%s)", school.slug, school.crawler_key)
    raw_events = list(crawler.fetch())
    log.info("  fetched %d events", len(raw_events))

    # 크롤링 결과가 단일 source of truth — 전체 삭제 후 재삽입.
    # 학교 사이트가 가끔 과거 일정을 수정 (오타, 기간 연장)하고
    # 재크롤링이 싸므로 row 보존을 시도하지 않는다.
    session.execute(delete(Event).where(Event.school_id == school.id))

    inserted = 0
    seen: set[tuple] = set()
    for ev in raw_events:
        key = (ev.summary, ev.dtstart, ev.dtend)
        if key in seen:
            continue
        seen.add(key)
        session.add(
            Event(
                school_id=school.id,
                summary=ev.summary,
                dtstart=ev.dtstart,
                dtend=ev.dtend,
                description=ev.description,
            )
        )
        inserted += 1

    log.info("  upserted %d events for %s", inserted, school.slug)
    return inserted


def main(only_slug: str | None = None) -> int:
    with session_scope() as session:
        stmt = select(School)
        if only_slug:
            stmt = stmt.where(School.slug == only_slug)
        schools = session.scalars(stmt).all()

        if not schools:
            log.warning("no schools to update (slug=%r)", only_slug)
            return 0

        total = 0
        for school in schools:
            try:
                total += update_school(session, school)
            except Exception:
                log.exception("failed to update school %s", school.slug)

        log.info("done. %d events total.", total)
        return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", help="update only this school slug")
    args = parser.parse_args()
    sys.exit(0 if main(args.slug) >= 0 else 1)
