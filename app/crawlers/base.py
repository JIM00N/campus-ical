from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class RawEvent:
    summary: str
    dtstart: date
    dtend: date  # exclusive (iCal DTEND-style)
    description: str | None = None


class BaseCrawler(ABC):
    """학교별 크롤러. 출력은 timezone-naive DATE — iCal 변환 시 tzid 부여.

    학교마다 사이트의 노출 방식이 다르다 (가천대는 월별 calendar,
    동서울대는 학년도 API 등). 각 크롤러가 자체적으로 적합한 horizon
    을 결정해 미래 학사일정을 가능한 만큼 받아온다.

    공통 규칙:
    - 과거(오늘 이전 시작) 일정은 제외
    - 중복 제거 (같은 summary/dtstart/dtend)
    """

    key: str  # matches School.crawler_key

    @abstractmethod
    def fetch(self) -> Iterable[RawEvent]:
        raise NotImplementedError
