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
    """Implement one per school. Output is timezone-naive DATE only —
    iCal generation adds the school's tzid."""

    key: str  # matches School.crawler_key

    @abstractmethod
    def fetch(self, months_ahead: int) -> Iterable[RawEvent]:
        """Return events covering the next `months_ahead` calendar months
        (including the current month). Implementations should de-duplicate
        events that appear on multiple month pages."""
        raise NotImplementedError
