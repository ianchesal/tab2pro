from .base import SiteAdapter
from ..models import Song


class UltimateGuitarAdapter(SiteAdapter):
    """Adapter for tabs.ultimate-guitar.com chord pages."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "tabs.ultimate-guitar.com/tab/" in url

    def fetch(self, url: str) -> str:
        raise NotImplementedError

    def extract(self, html: str, url: str) -> Song:
        raise NotImplementedError
