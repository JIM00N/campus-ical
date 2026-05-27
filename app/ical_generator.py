from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha1
from typing import Iterable

from icalendar import Calendar, Event

from app.models import Event as EventModel, School


def _uid(school_slug: str, ev: EventModel) -> str:
    raw = f"{school_slug}|{ev.summary}|{ev.dtstart.isoformat()}|{ev.dtend.isoformat()}"
    return f"{sha1(raw.encode('utf-8')).hexdigest()}@ical-db"


def build_calendar(school: School, events: Iterable[EventModel]) -> bytes:
    cal = Calendar()
    cal.add("prodid", f"-//ical-db//{school.slug}//KR")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", f"{school.name} 학사일정")
    cal.add("x-wr-timezone", school.timezone)

    now = datetime.now(timezone.utc)

    for ev in events:
        item = Event()
        item.add("uid", _uid(school.slug, ev))
        item.add("summary", ev.summary)
        # All-day events use DATE, not DATETIME.
        item.add("dtstart", ev.dtstart)
        item.add("dtend", ev.dtend)
        item.add("dtstamp", now)
        if ev.description:
            item.add("description", ev.description)
        cal.add_component(item)

    return cal.to_ical()
