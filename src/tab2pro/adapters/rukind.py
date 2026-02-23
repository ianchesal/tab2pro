from .base import SiteAdapter
from ..models import Song


class RukindAdapter(SiteAdapter):
    """Adapter for rukind.com Grateful Dead tab pages."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "rukind.com/gdpedia/titles/tab/" in url

    def fetch(self, url: str) -> str:
        raise NotImplementedError

    def extract(self, html: str, url: str) -> Song:
        raise NotImplementedError
