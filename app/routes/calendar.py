from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.ical_generator import build_calendar
from app.models import Event, School

router = APIRouter()


@router.get("/calendar/{slug}.ics")
def get_calendar(slug: str, session: Session = Depends(get_session)):
    school = session.scalar(select(School).where(School.slug == slug))
    if not school:
        raise HTTPException(status_code=404, detail="school not found")

    events = session.scalars(
        select(Event).where(Event.school_id == school.id).order_by(Event.dtstart)
    ).all()

    body = build_calendar(school, events)
    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'inline; filename="{slug}.ics"',
            "Cache-Control": "public, max-age=3600",
        },
    )
