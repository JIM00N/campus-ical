"""Cron entry point: re-crawl every active school and refresh its future events.

Run with `python -m app.tasks.update_schools`.
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from sqlalchemy import delete, select

from app.config import CRAWL_MONTHS_AHEAD
from app.crawlers import get_crawler
from app.db import session_scope
from app.models import Event, School

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("update_schools")


def update_school(session, school: School, months_ahead: int) -> int:
    crawler = get_crawler(school.crawler_key)
    log.info("crawling %s (key=%s)", school.slug, school.crawler_key)
    raw_events = list(crawler.fetch(months_ahead))
    log.info("  fetched %d events", len(raw_events))

    # Replace future events to reflect any schedule edits upstream.
    session.execute(
        delete(Event).where(Event.school_id == school.id, Event.dtstart >= date.today())
    )

    inserted = 0
    seen: set[tuple[str, date, date]] = set()
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


def main(only_slug: str | None = None, months_ahead: int = CRAWL_MONTHS_AHEAD) -> int:
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
                total += update_school(session, school, months_ahead)
            except Exception:
                log.exception("failed to update school %s", school.slug)

        log.info("done. %d events total.", total)
        return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", help="update only this school slug")
    parser.add_argument("--months", type=int, default=CRAWL_MONTHS_AHEAD)
    args = parser.parse_args()
    sys.exit(0 if main(args.slug, args.months) >= 0 else 1)
