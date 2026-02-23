"""Adapter for dylanchords.com Bob Dylan chord pages.

URL pattern: dylanchords.com/<album-slug>/<song-slug>

Page structure (Drupal 7):
    <h1>Song Title</h1>
    <div class="field-name-body">
        <div class="field-items">
            <div class="field-item even">
                <pre class="chordcharts">G 320003 ...</pre>   ← skip
                <h2>Freewheelin' version</h2>
                <p>Capo 7th fret (sounding key D major)</p>  ← optional
                <pre class="verse">chord/lyric lines</pre>
                <pre class="verse">...</pre>
                <h2>Live 1975 version</h2>
                <pre class="verse">...</pre>
                ...
            </div>
        </div>
    </div>

Multiple versions are separated by <h2> tags.  The constructor's ``version``
parameter (1-indexed, default 1) selects which version to extract.

Chord notation: unbracketed, space-aligned above lyrics.
Slash chords (C/b, D/f#) are supported by the shared chord regex.
"""

import re

import httpx
from bs4 import BeautifulSoup, Tag

from ..exceptions import FetchError, ParseError
from ..models import Song
from .base import SiteAdapter
from .utils import parse_text_tab

_CAPO_RE = re.compile(r"[Cc]apo\s+(\d+)")
_TUNING_RE = re.compile(
    r"\b(Drop [A-G]|Open [A-G]|DADGAD|DGDGBD|half.?step(?:s)? (?:down|up)|"
    r"[A-G]{6})\b",
    re.IGNORECASE,
)


class DylanchordsAdapter(SiteAdapter):
    """Adapter for dylanchords.com Bob Dylan chord pages."""

    def __init__(self, version: int = 1):
        self.version = version  # 1-indexed; selects which song version to extract

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "dylanchords.com/" in url

    def fetch(self, url: str) -> str:
        try:
            resp = httpx.get(url, follow_redirects=True, timeout=15)
        except httpx.RequestError as exc:
            raise FetchError(url, 0) from exc
        if resp.status_code != 200:
            raise FetchError(url, resp.status_code)
        return resp.text

    def extract(self, html: str, url: str) -> Song:
        soup = BeautifulSoup(html, "html.parser")

        # Song title
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else _title_from_url(url)

        # Main content area (Drupal field-name-body)
        content_div = soup.find("div", class_="field-name-body") or soup.find(
            "div", class_="field-items"
        )
        if not content_div:
            raise ParseError(url, "Could not find Drupal content area (field-name-body)")

        # Split page into version blocks
        versions = _split_versions(content_div)
        if not versions:
            raise ParseError(url, "No chord content found on page")

        if self.version < 1 or self.version > len(versions):
            raise ParseError(
                url,
                f"Version {self.version} requested but page has {len(versions)} version(s)",
            )

        ver = versions[self.version - 1]
        capo = _extract_capo(ver["paragraphs"])
        tuning = _extract_tuning(ver["paragraphs"])

        sections = []
        for verse_text in ver["verses"]:
            parsed = parse_text_tab(verse_text, style="unbracketed")
            sections.extend(s for s in parsed if s.lines)

        return Song(
            title=title,
            artist="Bob Dylan",
            sections=sections,
            capo=capo,
            tuning=tuning,
            source_url=url,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split_versions(content_div: Tag) -> list[dict]:
    """Group the content area into version blocks separated by <h2> tags.

    Each version is a dict:
        {"label": str|None, "verses": [str], "paragraphs": [str]}

    ``verses`` contains the raw text of each ``<pre class="verse">`` block.
    ``paragraphs`` contains ``<p>`` text (used for capo/tuning extraction).
    ``<pre class="chordcharts">`` blocks (chord definition tables) are skipped.

    Returns an empty list if no verse content is found.
    """
    # Drill down to the innermost content div if needed
    inner = content_div.find("div", class_="field-item") or content_div

    versions: list[dict] = []
    current: dict = {"label": None, "verses": [], "paragraphs": []}

    for element in inner.find_all(["h2", "pre", "p"], recursive=True):
        tag = element.name

        if tag == "h2":
            if current["verses"]:
                versions.append(current)
            current = {
                # Use stripped_strings to preserve spaces between inline tags
                # (e.g. <h2><em>Freewheelin'</em> version</h2> → "Freewheelin' version")
                "label": " ".join(element.stripped_strings) or None,
                "verses": [],
                "paragraphs": [],
            }

        elif tag == "pre":
            classes = element.get("class") or []
            if "verse" in classes:
                current["verses"].append(element.get_text())
            # "chordcharts" blocks are intentionally skipped

        elif tag == "p":
            text = element.get_text(strip=True)
            if text:
                current["paragraphs"].append(text)

    # Flush final version
    if current["verses"]:
        versions.append(current)

    return versions


def _extract_capo(paragraphs: list[str]) -> int | None:
    """Return capo fret number from paragraph text, e.g. ``Capo 7th fret``."""
    for p in paragraphs:
        m = _CAPO_RE.search(p)
        if m:
            return int(m.group(1))
    return None


def _extract_tuning(paragraphs: list[str]) -> str | None:
    """Return non-standard tuning name from paragraph text, if present."""
    for p in paragraphs:
        m = _TUNING_RE.search(p)
        if m:
            return m.group(1)
    return None


def _title_from_url(url: str) -> str:
    slug = url.rstrip("/").split("/")[-1]
    return slug.replace("_", " ").replace("-", " ").title()
