"""Adapter for tabs.ultimate-guitar.com chord pages.

UG returns 403 without browser-like headers.  Tab data is embedded as JSON in
a ``<script id="__NEXT_DATA__" type="application/json">`` tag.

JSON path:
    props.pageProps.data.tab_view
        .song_name          → Song.title
        .artist_name        → Song.artist
        .capo               → Song.capo  (0 means no capo)
        .tonality_name      → Song.key   ("" means unknown)
        .wiki_tab.content   → raw tab text

The tab text may use ``[ch]D[/ch]`` notation — these are stripped to ``[D]``
before parsing.  Chord lines use the bracketed style (``[D]``, ``[Am7]``).
"""

import json
import re

import httpx
from bs4 import BeautifulSoup

from .base import SiteAdapter
from .utils import parse_text_tab
from ..exceptions import FetchError, ParseError
from ..models import Song

_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/webp,*/*;q=0.8"
    ),
    "Referer": "https://www.google.com/",
}

_CH_TAG_RE = re.compile(r"\[ch\]([^\[]*)\[/ch\]")


def _strip_ch_tags(text: str) -> str:
    """Convert ``[ch]D[/ch]`` → ``[D]``."""
    return _CH_TAG_RE.sub(r"[\1]", text)


class UltimateGuitarAdapter(SiteAdapter):
    """Adapter for tabs.ultimate-guitar.com chord pages."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "tabs.ultimate-guitar.com/tab/" in url

    def fetch(self, url: str) -> str:
        """GET the page with browser-like headers to avoid 403."""
        try:
            resp = httpx.get(
                url,
                headers=_FETCH_HEADERS,
                follow_redirects=True,
                timeout=15,
            )
        except httpx.RequestError as exc:
            raise FetchError(url, 0) from exc
        if resp.status_code != 200:
            raise FetchError(url, resp.status_code)
        return resp.text

    def extract(self, html: str, url: str) -> Song:
        soup = BeautifulSoup(html, "html.parser")

        # Locate the __NEXT_DATA__ JSON blob
        script_tag = soup.find("script", id="__NEXT_DATA__")
        if not script_tag:
            raise ParseError(url, "Could not find <script id='__NEXT_DATA__'>")

        try:
            data = json.loads(script_tag.string)
            tab_view = data["props"]["pageProps"]["data"]["tab_view"]
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ParseError(url, f"Could not navigate __NEXT_DATA__ JSON: {exc}") from exc

        # Metadata
        title = tab_view.get("song_name") or ""
        artist = tab_view.get("artist_name") or ""
        capo_raw = tab_view.get("capo", 0)
        capo = int(capo_raw) if capo_raw else None
        key = tab_view.get("tonality_name") or None

        # Tab content
        wiki_tab = tab_view.get("wiki_tab") or {}
        content = wiki_tab.get("content") or ""
        if not content:
            raise ParseError(url, "wiki_tab.content is empty or missing")

        content = _strip_ch_tags(content)
        sections = parse_text_tab(content, style="bracketed")

        return Song(
            title=title,
            artist=artist,
            sections=sections,
            key=key,
            capo=capo,
            source_url=url,
        )
