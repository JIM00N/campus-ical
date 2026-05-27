from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import engine
from app.models import Base
from app.routes import calendar, pages

app = FastAPI(title="ical-db", description="대학 학사일정 iCal 구독 서비스")


@app.on_event("startup")
def on_startup():
    # Convenient for fresh PostgreSQL volumes. Production should still run
    # migrations explicitly, but this keeps local/dev one-step.
    Base.metadata.create_all(bind=engine)


app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(pages.router)
app.include_router(calendar.router)


@app.get("/healthz")
def healthz():
    return {"ok": True}
