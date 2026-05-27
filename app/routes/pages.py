from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.categories import CATEGORIES
from app.config import ADSENSE_CLIENT_ID, ADSENSE_SLOT_ID, BASE_URL
from app.db import get_session
from app.models import School

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _ads_context() -> dict:
    return {
        "adsense_client_id": ADSENSE_CLIENT_ID,
        "adsense_slot_id": ADSENSE_SLOT_ID,
        "ads_enabled": bool(ADSENSE_CLIENT_ID and ADSENSE_SLOT_ID),
    }


@router.get("/", response_class=HTMLResponse)
def index(request: Request, session: Session = Depends(get_session)):
    schools = session.scalars(select(School).order_by(School.name)).all()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"schools": schools, **_ads_context()},
    )


@router.get("/s/{slug}", response_class=HTMLResponse)
def school_page(slug: str, request: Request, session: Session = Depends(get_session)):
    school = session.scalar(select(School).where(School.slug == slug))
    if not school:
        raise HTTPException(status_code=404, detail="school not found")
    ical_url = f"{BASE_URL.rstrip('/')}/calendar/{school.slug}.ics"
    # Calendar subscriptions use webcal:// so that clicking opens the OS calendar app.
    webcal_url = ical_url.replace("http://", "webcal://").replace("https://", "webcal://")
    return templates.TemplateResponse(
        request,
        "school.html",
        {
            "school": school,
            "ical_url": ical_url,
            "webcal_url": webcal_url,
            "categories": CATEGORIES,
            **_ads_context(),
        },
    )
