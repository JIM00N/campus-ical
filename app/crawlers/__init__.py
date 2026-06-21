from app.crawlers.base import BaseCrawler, RawEvent
from app.crawlers.registry import get_crawler, register_crawler
from app.crawlers import gachon  # noqa: F401  register on import
from app.crawlers import dseoul  # noqa: F401  register on import
from app.crawlers import snu  # noqa: F401  register on import
from app.crawlers import korea  # noqa: F401  register on import
from app.crawlers import knsu  # noqa: F401  register on import
from app.crawlers import hallym  # noqa: F401  register on import
from app.crawlers import dongguk  # noqa: F401  register on import
from app.crawlers import hongik  # noqa: F401  register on import
from app.crawlers import ewha  # noqa: F401  register on import

__all__ = ["BaseCrawler", "RawEvent", "get_crawler", "register_crawler"]
