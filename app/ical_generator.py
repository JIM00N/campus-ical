from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from hashlib import sha1
from types import SimpleNamespace
from typing import Iterable

from icalendar import Calendar, Event

from app.models import Event as EventModel, School


def to_endpoint_events(events: Iterable[EventModel]) -> list:
    """여러 날 일정을 시작일/종료일 두 개의 하루짜리 마커로 분리한다.

    DTEND는 exclusive라 실제 마지막 날은 dtend - 1일. 하루짜리 일정은 그대로 둔다.
    """
    out: list = []
    for ev in events:
        last_day = ev.dtend - timedelta(days=1)
        if last_day <= ev.dtstart:
            out.append(ev)
            continue
        out.append(SimpleNamespace(
            summary=f"{ev.summary} (시작)",
            dtstart=ev.dtstart,
            dtend=ev.dtstart + timedelta(days=1),
            description=ev.description,
        ))
        out.append(SimpleNamespace(
            summary=f"{ev.summary} (종료)",
            dtstart=last_day,
            dtend=ev.dtend,
            description=ev.description,
        ))
    return out


def _uid(school_slug: str, ev: EventModel) -> str:
    raw = f"{school_slug}|{ev.summary}|{ev.dtstart.isoformat()}|{ev.dtend.isoformat()}"
    return f"{sha1(raw.encode('utf-8')).hexdigest()}@ical-db"


def build_calendar(
    school: School,
    events: Iterable[EventModel],
    calendar_name: str | None = None,
) -> bytes:
    cal = Calendar()
    cal.add("prodid", f"-//ical-db//{school.slug}//KR")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", f"{calendar_name or school.name} 학사일정")
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
