"""Adapter for rukind.com Grateful Dead tab pages.

URL pattern: rukind.com/gdpedia/titles/tab/<song-slug>

Page structure:
    <h1>Song Title</h1>           (page title, outside tab div)
    <div id="tab">
        <html>                    (nested HTML island)
            <h3>Album Name</h3>   (version context, e.g. "Live Dead")
            <h1>Intro</h1>        (section label)
            <pre>chord/lyric content</pre>
            <h1>Verse</h1>
            <pre>chord/lyric content</pre>
            ...
        </html>
    </div>

Chord notation: unbracketed, space-aligned above lyrics:
    A  G      A      G
    Dark star crashes, pouring its light into ashes

ASCII guitar tab blocks (e|--0--1--|) are detected and skipped by the
shared parse_text_tab() utility.
"""

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag

from ..exceptions import FetchError, ParseError
from ..models import Song
from .base import SiteAdapter
from .utils import parse_text_tab


class RukindAdapter(SiteAdapter):
    """Adapter for rukind.com Grateful Dead tab pages."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "rukind.com/gdpedia/titles/tab/" in url

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

        # Song title from the first <h1> in the outer page.
        # Section headings inside #tab are also <h1> but come later in the tree.
        outer_h1 = soup.find("h1")
        title = outer_h1.get_text(strip=True) if outer_h1 else _title_from_url(url)

        tab_div = soup.find("div", id="tab")
        if not tab_div:
            raise ParseError(url, "Could not find <div id='tab'>")

        sections = _extract_sections(tab_div, url)
        if not sections:
            raise ParseError(url, "No chord content found inside #tab")

        return Song(
            title=title,
            artist="Grateful Dead",
            sections=sections,
            source_url=url,
        )


def _extract_sections(tab_div: Tag, url: str) -> list:
    """Walk the tab div's headings and <pre> blocks and build Section objects.

    Headings (h1/h2/h3) set the current section label.
    Each <pre> block is parsed and its lines appended to the current section.
    Empty sections (all-tab content, skipped by parse_text_tab) are dropped.
    """

    sections = []
    current_label: str | None = None

    # find_all navigates into the nested <html> island transparently
    for element in tab_div.find_all(["h1", "h2", "h3", "pre"]):
        if element.name in ("h1", "h2", "h3"):
            current_label = element.get_text(strip=True) or None
            continue

        # <pre> block — extract only direct text nodes.
        # Rukind embeds navigation links (<h7><a>), metadata (<em>), and
        # <br> tags inside <pre>.  Using get_text() would pull in all of that
        # noise.  We want only the chord/lyric content, which lives in the
        # direct NavigableString children.
        text = _pre_text(element)
        parsed = parse_text_tab(text, style="unbracketed")

        # Drop empty sections (all-tab blocks produce no lines)
        parsed = [s for s in parsed if s.lines]
        if not parsed:
            continue

        # Assign the preceding heading as the label for the first sub-section
        if current_label is not None:
            parsed[0].label = current_label
            current_label = None

        sections.extend(parsed)

    return sections


def _pre_text(pre_element: Tag) -> str:
    """Extract chord/lyric text from a <pre> block, ignoring embedded HTML.

    Rukind embeds navigation links (``<h7><a>``), metadata (``<em>``), and
    ``<br>`` tags inside ``<pre>`` blocks.  This function collects only the
    direct :class:`NavigableString` children (the actual tab text) and treats
    ``<br>`` elements as newlines.
    """
    parts: list[str] = []
    for child in pre_element.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif isinstance(child, Tag) and child.name == "br":
            parts.append("\n")
        # All other tags (<em>, <h7>, <a>, …) are intentionally skipped
    return "".join(parts)


def _title_from_url(url: str) -> str:
    """Derive a song title from the URL slug as a last-resort fallback."""
    slug = url.rstrip("/").split("/")[-1]
    return slug.replace("-", " ").title()
