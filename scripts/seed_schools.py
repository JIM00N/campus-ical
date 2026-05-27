"""Seed the schools table. Idempotent — safe to run on every deploy."""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.db import engine, session_scope
from app.models import Base, School

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s :: %(message)s")
log = logging.getLogger("seed")

SCHOOLS = [
    {
        "slug": "gachon",
        "name": "가천대학교",
        "name_en": "Gachon University",
        "logo_path": "/static/logos/gachon.svg",
        "website": "https://www.gachon.ac.kr/kor/1075/subview.do",
        "crawler_key": "gachon",
        "timezone": "Asia/Seoul",
    },
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with session_scope() as session:
        for data in SCHOOLS:
            existing = session.scalar(select(School).where(School.slug == data["slug"]))
            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
                log.info("updated %s", data["slug"])
            else:
                session.add(School(**data))
                log.info("inserted %s", data["slug"])
    log.info("done.")


if __name__ == "__main__":
    main()
