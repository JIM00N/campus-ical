"""학사일정 카테고리 정의 + 매칭 로직.

각 학교 페이지의 summary 텍스트를 keyword로 매칭해 카테고리를 부여한다.
DB 컬럼이 아니라 동적 분류라서, 카테고리 정의를 늘리고 줄이는 데 마이그레이션이
필요 없다. 매칭은 공백을 무시(`수강 신청기간` ↔ `수강신청`)한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Category:
    slug: str               # URL 식별자
    label: str              # 사용자에게 보이는 한국어
    keywords: tuple[str, ...]


CATEGORIES: tuple[Category, ...] = (
    Category("tuition",      "등록금",          ("등록금",)),
    Category("registration", "수강신청",        ("수강신청", "예비수강")),
    Category("exam",         "시험",            ("중간고사", "기말고사", "기말시험", "중간시험", "성적공시", "정정")),
    Category("major-change", "전과·부복수전공",  ("전과", "부전공", "복수전공", "다전공", "융합전공", "조기졸업")),
    Category("leave",        "휴학·복학",       ("휴학", "복학")),
    Category("summer",       "계절학기",        ("계절학기", "계절수업")),
    Category("withdrawal",   "자퇴",            ("자퇴",)),
    Category("graduation",   "학위수여식",      ("학위수여", "졸업식")),
)

CATEGORY_BY_SLUG: dict[str, Category] = {c.slug: c for c in CATEGORIES}


def _normalize(s: str) -> str:
    return s.replace(" ", "").replace(" ", "")


def event_categories(summary: str) -> set[str]:
    """해당 이벤트의 summary에 매칭되는 카테고리 slug 집합."""
    norm = _normalize(summary)
    return {
        c.slug
        for c in CATEGORIES
        if any(_normalize(kw) in norm for kw in c.keywords)
    }


def parse_category_param(raw: str | None) -> set[str]:
    """`?categories=tuition,exam` → {'tuition', 'exam'}.

    알 수 없는 slug는 조용히 무시한다 (URL이 살짝 깨져도 빈 캘린더 대신
    인식되는 부분만 반환). 빈 셋이면 호출자는 '필터 없음'으로 취급.
    """
    if not raw:
        return set()
    requested = {s.strip() for s in raw.split(",") if s.strip()}
    return requested & CATEGORY_BY_SLUG.keys()


def filter_events(events: Iterable, wanted: set[str]) -> list:
    """wanted가 비어 있으면 전체 그대로. 아니면 카테고리가 겹치는 것만."""
    if not wanted:
        return list(events)
    return [e for e in events if event_categories(e.summary) & wanted]
