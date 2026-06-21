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
    {
        "slug": "dseoul",
        "name": "동서울대학교",
        "name_en": "Dongseoul University",
        "logo_path": "/static/logos/dseoul.svg",
        "website": "https://www.du.ac.kr/submenu.do?menuUrl=mk%2F8AIUzCNRzSS%2BQycenWQ%3D%3D&",
        "crawler_key": "dseoul",
        "timezone": "Asia/Seoul",
    },
    {
        "slug": "snu",
        "name": "서울대학교",
        "name_en": "Seoul National University",
        "logo_path": "/static/logos/snu.svg",
        "website": "https://www.snu.ac.kr/academics/resources/calendar",
        "crawler_key": "snu",
        "timezone": "Asia/Seoul",
    },
    {
        "slug": "korea",
        "name": "고려대학교",
        "name_en": "Korea University",
        "logo_path": "/static/logos/korea.svg",
        "website": "https://registrar.korea.ac.kr/eduinfo/affairs/schedule.do",
        "crawler_key": "korea",
        "timezone": "Asia/Seoul",
    },
    {
        "slug": "knsu",
        "name": "한국체육대학교",
        "name_en": "Korea National Sport University",
        "logo_path": "/static/logos/knsu.svg",
        "website": "https://www.knsu.ac.kr/knsu/academic/academic-schedule.do",
        "crawler_key": "knsu",
        "timezone": "Asia/Seoul",
    },
    {
        "slug": "hallym",
        "name": "한림대학교",
        "name_en": "Hallym University",
        "logo_path": "/static/logos/hallym.svg",
        "website": "https://www.hallym.ac.kr/hallym/1062/subview.do",
        "crawler_key": "hallym",
        "timezone": "Asia/Seoul",
    },
    {
        "slug": "dongguk",
        "name": "동국대학교",
        "name_en": "Dongguk University",
        "logo_path": "/static/logos/dongguk.png",
        "website": "https://www.dongguk.edu/schedule/detail",
        "crawler_key": "dongguk",
        "timezone": "Asia/Seoul",
    },
    {
        "slug": "hongik",
        "name": "홍익대학교",
        "name_en": "Hongik University",
        "logo_path": "/static/logos/hongik.svg",
        "website": "https://www.hongik.ac.kr/kr/education/academic-schedule001.do",
        "crawler_key": "hongik",
        "timezone": "Asia/Seoul",
    },
    {
        "slug": "ewha",
        "name": "이화여자대학교",
        "name_en": "Ewha Womans University",
        "logo_path": "/static/logos/ewha.svg",
        "website": "https://www.ewha.ac.kr/ewha/bachelor/calendar2026.do",
        "crawler_key": "ewha",
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
