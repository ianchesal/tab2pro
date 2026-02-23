from abc import ABC, abstractmethod

from ..models import Song


class SiteAdapter(ABC):
    """Abstract base class for all site-specific adapters."""

    @classmethod
    @abstractmethod
    def can_handle(cls, url: str) -> bool:
        """Return True if this adapter can handle the given URL."""

    @abstractmethod
    def fetch(self, url: str) -> str:
        """Fetch the page at url and return raw HTML.

        Raises FetchError on HTTP-level failures.
        """

    @abstractmethod
    def extract(self, html: str, url: str) -> Song:
        """Parse HTML and return a canonical Song.

        By the time this returns, all chords must be embedded inline within
        Line.content using ChordPro bracket notation ([D], [Am7], etc.).

        Raises ParseError if expected content cannot be found.
        """

    def scrape(self, url: str) -> Song:
        """Convenience method: fetch + extract."""
        html = self.fetch(url)
        return self.extract(html, url)
