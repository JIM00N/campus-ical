from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.categories import CATEGORY_BY_SLUG, filter_events, parse_category_param
from app.db import get_session
from app.ical_generator import build_calendar, to_endpoint_events
from app.models import Event, School

router = APIRouter()


@router.get("/calendar/{slug}.ics")
def get_calendar(
    slug: str,
    categories: str = Query("", description="comma-separated category slugs"),
    endpoints: bool = Query(False, description="multi-day events as start/end markers only"),
    session: Session = Depends(get_session),
):
    school = session.scalar(select(School).where(School.slug == slug))
    if not school:
        raise HTTPException(status_code=404, detail="school not found")

    events = session.scalars(
        select(Event).where(Event.school_id == school.id).order_by(Event.dtstart)
    ).all()

    wanted = parse_category_param(categories)
    events = filter_events(events, wanted)
    if endpoints:
        events = to_endpoint_events(events)

    cal_name = school.name
    if wanted:
        labels = [CATEGORY_BY_SLUG[s].label for s in wanted]
        cal_name = f"{school.name} ({', '.join(labels)})"

    body = build_calendar(school, events, calendar_name=cal_name)
    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'inline; filename="{slug}.ics"',
            "Cache-Control": "public, max-age=3600",
        },
    )
