from .base import SiteAdapter
from ..models import Song


class DylanchordsAdapter(SiteAdapter):
    """Adapter for dylanchords.com Bob Dylan chord pages."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "dylanchords.com/" in url

    def fetch(self, url: str) -> str:
        raise NotImplementedError

    def extract(self, html: str, url: str) -> Song:
        raise NotImplementedError
