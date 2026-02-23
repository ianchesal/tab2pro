"""Adapter for tabs.ultimate-guitar.com chord pages.

UG returns 403 without browser-like headers.

Two page formats are supported (UG has migrated away from Next.js):

New format (current):
    <div class="js-store" data-content="<html-entity-encoded JSON>">
    JSON path:
        store.page.data.tab
            .song_name        → Song.title
            .artist_name      → Song.artist
            .tonality_name    → Song.key
        store.page.data.tab_view
            .wiki_tab.content → raw tab text

Legacy format (Next.js, kept as fallback):
    <script id="__NEXT_DATA__" type="application/json">
    JSON path:
        props.pageProps.data.tab_view
            .song_name / .artist_name / .capo / .tonality_name
            .wiki_tab.content

The tab text uses ``[ch]D[/ch]`` notation (stripped to ``[D]``) and may wrap
chord+lyric pairs in ``[tab]...[/tab]`` tags (also stripped).  Chord lines
use the bracketed style (``[D]``, ``[Am7]``).
"""

import html as html_module
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
_TAB_TAG_RE = re.compile(r"\[/?tab\]")


def _strip_ug_tags(text: str) -> str:
    """Strip UG-specific markup from tab content.

    - ``[ch]D[/ch]`` → ``[D]``
    - ``[tab]`` / ``[/tab]`` → removed
    """
    text = _CH_TAG_RE.sub(r"[\1]", text)
    text = _TAB_TAG_RE.sub("", text)
    return text


def _extract_page_data(soup: BeautifulSoup, url: str) -> dict:
    """Return the ``page.data`` dict from whichever JSON container is present.

    Tries the current ``js-store`` format first, then falls back to the
    legacy ``__NEXT_DATA__`` format.

    Raises :class:`~tab2pro.exceptions.ParseError` if neither is found or
    can be parsed.
    """
    # --- Current format: <div class="js-store" data-content="..."> ---
    store_div = soup.find("div", class_="js-store")
    if store_div and store_div.get("data-content"):
        try:
            data = json.loads(html_module.unescape(store_div["data-content"]))
            return data["store"]["page"]["data"]
        except (KeyError, TypeError, json.JSONDecodeError):
            pass  # fall through to legacy

    # --- Legacy format: <script id="__NEXT_DATA__"> ---
    script_tag = soup.find("script", id="__NEXT_DATA__")
    if script_tag and script_tag.string:
        try:
            data = json.loads(script_tag.string)
            return data["props"]["pageProps"]["data"]
        except (KeyError, TypeError, json.JSONDecodeError):
            pass

    raise ParseError(url, "Could not find tab data (tried js-store and __NEXT_DATA__)")


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
        page_data = _extract_page_data(soup, url)

        # Metadata lives in page_data["tab"] (new) or page_data["tab_view"] (legacy).
        tab_meta = page_data.get("tab") or page_data.get("tab_view") or {}
        tab_view = page_data.get("tab_view") or {}

        title = tab_meta.get("song_name") or ""
        artist = tab_meta.get("artist_name") or ""
        # capo: present in legacy tab_view; may be absent in new format
        capo_raw = tab_meta.get("capo") or tab_view.get("capo") or 0
        capo = int(capo_raw) if capo_raw else None
        key = tab_meta.get("tonality_name") or tab_view.get("tonality_name") or None

        # Tab content is always in tab_view.wiki_tab.content
        wiki_tab = tab_view.get("wiki_tab") or {}
        content = wiki_tab.get("content") or ""
        if not content:
            raise ParseError(url, "wiki_tab.content is empty or missing")

        content = _strip_ug_tags(content)
        sections = parse_text_tab(content, style="bracketed")

        return Song(
            title=title,
            artist=artist,
            sections=sections,
            key=key,
            capo=capo,
            source_url=url,
        )
