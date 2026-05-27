from typing import Type
from app.crawlers.base import BaseCrawler

_REGISTRY: dict[str, Type[BaseCrawler]] = {}


def register_crawler(cls: Type[BaseCrawler]) -> Type[BaseCrawler]:
    if not getattr(cls, "key", None):
        raise ValueError(f"{cls.__name__} missing class attribute 'key'")
    _REGISTRY[cls.key] = cls
    return cls


def get_crawler(key: str) -> BaseCrawler:
    if key not in _REGISTRY:
        raise KeyError(f"No crawler registered for key={key!r}. Registered: {list(_REGISTRY)}")
    return _REGISTRY[key]()
