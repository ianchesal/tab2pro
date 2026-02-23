import re
import sys
from pathlib import Path

import click

from .chordpro import ChordProFormatter
from .exceptions import FetchError, ParseError, UnsupportedSiteError
from .registry import get_adapter


def _slugify(text: str) -> str:
    """Convert a string to a lowercase hyphenated slug suitable for filenames."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)   # drop punctuation
    text = re.sub(r"[\s_]+", "-", text)     # spaces/underscores → hyphens
    text = re.sub(r"-{2,}", "-", text)      # collapse multiple hyphens
    return text.strip("-")


def _default_filename(artist: str, title: str) -> str:
    return f"{_slugify(artist)}-{_slugify(title)}.cho"


@click.command()
@click.argument("url")
@click.option("-o", "--output", "output_path", default=None, metavar="PATH",
              help="Output file path (default: <artist>-<title>.cho)")
@click.option("--stdout", is_flag=True, default=False,
              help="Print to stdout instead of writing a file.")
@click.option("--browser", is_flag=True, default=False,
              help="Use Playwright headless browser (fallback for 403s).")
@click.option("--version", "song_version", default=1, show_default=True,
              help="For sites with multiple song versions, pick version N.")
def main(url: str, output_path: str | None, stdout: bool, browser: bool, song_version: int) -> None:
    """Convert a chord tab page to ChordPro format.

    \b
    Supported sites:
      - tabs.ultimate-guitar.com
      - rukind.com
      - dylanchords.com
    """
    # --- Resolve adapter ---
    try:
        adapter = get_adapter(url)
    except UnsupportedSiteError as exc:
        click.echo(f"Error: {exc}", err=True)
        click.echo(
            "Supported sites: tabs.ultimate-guitar.com, rukind.com, dylanchords.com",
            err=True,
        )
        sys.exit(1)

    # Pass version to adapters that support it (DylanchordsAdapter)
    if hasattr(adapter, "version"):
        adapter.version = song_version

    # --- Fetch + parse ---
    try:
        song = adapter.scrape(url)
    except FetchError as exc:
        msg = f"Error: Could not fetch {exc.url}"
        if exc.status_code:
            msg += f" (HTTP {exc.status_code})"
        if exc.status_code == 403:
            msg += " — try --browser for sites that block automated requests"
        click.echo(msg, err=True)
        sys.exit(1)
    except ParseError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    # --- Render ---
    formatter = ChordProFormatter()
    chordpro_text = formatter.render(song)

    # --- Output ---
    if stdout:
        click.echo(chordpro_text, nl=False)
        return

    dest = Path(output_path) if output_path else Path(_default_filename(song.artist, song.title))
    dest.write_text(chordpro_text, encoding="utf-8")
    click.echo(f"Written to {dest}")
