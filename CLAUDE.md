# Multi-Site Chord Scraper → ChordPro

## Project Overview

A Python CLI tool that fetches chord/tab pages from supported music sites, extracts song lyrics and chords, and writes the result as a [ChordPro](https://www.chordpro.org/chordpro/chordpro-introduction/) `.cho` file.

**Supported sites:**
- Ultimate Guitar (`tabs.ultimate-guitar.com`)
- Rukind (`rukind.com/gdpedia/titles/tab/`)
- Dylan Chords (`dylanchords.com`)

Adding a new site = one new adapter file + one registry entry.

## Technology Stack

- **Language**: Python 3.12+
- **Package manager**: `uv`
- **HTTP fetching**: `httpx` with browser-like headers; optional `playwright` fallback
- **HTML parsing**: `beautifulsoup4`
- **CLI**: `click`
- **Testing**: `pytest`, `respx` (httpx mocking)

## Key Commands

```bash
# Install dependencies
uv sync

# Run the scraper
uv run tab2pro <url> [--output <file>]
uv run tab2pro https://tabs.ultimate-guitar.com/tab/the-band/the-weight-chords-61592
uv run tab2pro http://www.rukind.com/gdpedia/titles/tab/dark-star
uv run tab2pro http://www.dylanchords.com/02_freewheelin/blowin_in_the_wind

# Run tests (unit only)
uv run pytest -m "not integration"

# Run all tests including live network
uv run pytest

# Run with coverage
uv run pytest --cov=tab2pro -m "not integration"
```

## Project Structure

```
.
├── CLAUDE.md
├── PLAN.md
├── pyproject.toml
├── src/
│   └── tab2pro/
│       ├── __init__.py
│       ├── cli.py               # Click CLI entry point
│       ├── models.py            # Canonical Song/Section/Line dataclasses
│       ├── exceptions.py        # FetchError, ParseError, UnsupportedSiteError
│       ├── registry.py          # Maps URLs to adapters
│       ├── chordpro.py          # Site-agnostic ChordPro formatter
│       └── adapters/
│           ├── __init__.py
│           ├── base.py          # SiteAdapter abstract base class
│           ├── utils.py         # Shared chord-merge algorithm, line classifier
│           ├── ultimate_guitar.py
│           ├── rukind.py
│           └── dylanchords.py
└── tests/
    ├── fixtures/
    │   ├── ultimate_guitar/     # Saved HTML for offline tests
    │   ├── rukind/
    │   └── dylanchords/
    ├── test_models.py
    ├── test_utils.py
    ├── test_adapter_ug.py
    ├── test_adapter_rukind.py
    ├── test_adapter_dylanchords.py
    ├── test_chordpro.py
    └── test_cli.py
```

## Key Architectural Rules

- **Adapters own all site-specific logic**: fetching strategy, HTML extraction, chord notation normalization, and the conversion to inline ChordPro chord notation.
- **The canonical `Song` model is the interface**: by the time `adapter.extract()` returns, all chords must already be inline in `Line.content` as `[ChordName]`.
- **`chordpro.py` is site-agnostic**: it only renders `Song` → ChordPro text; it performs no parsing.
- **`adapters/utils.py` holds shared parsing**: the chord-above-lyric merge algorithm is used by all adapters, parameterized by chord notation style (`bracketed` vs `unbracketed`).

## Site-Specific Notes

### Ultimate Guitar
- Returns 403 without browser-like `User-Agent` and `Accept-Language` headers
- Tab data is JSON embedded in `<script id="__NEXT_DATA__" type="application/json">`
- JSON path: `props.pageProps.data.tab_view` → `wiki_tab.content` (raw text), `song_name`, `artist_name`, `capo`, `tonality_name`
- Content may use `[ch]D[/ch]` tags — strip to `[D]` before parsing
- Chord notation: **bracketed** (`[D]`, `[Am7]`) on lines above lyrics

### Rukind
- No known bot protection; standard `httpx` GET works
- Artist is always "Grateful Dead"
- Chord notation: **unbracketed**, space-aligned (`D  G  A`) on lines above lyrics
- Pages may mix chord sections with ASCII guitar tab blocks — skip tab blocks

### Dylan Chords
- Drupal-based; no known bot protection
- Can have multiple song versions (different capo/tuning) on one page
- Chord notation: TBD on first integration
- `Song.tuning` field captures non-standard tunings (e.g. "Drop D", "DADGAD")

## ChordPro Output
- File extension: `.cho`
- Chords inline: `I [D]pulled into Nazareth, was feelin' about [G]half past [D]dead`
- Metadata directives: `{title:}`, `{artist:}`, `{key:}`, `{capo:}`, `{tuning:}`
- Sections: `{start_of_verse: Verse 1}` / `{end_of_verse}`, `{start_of_chorus}` / `{end_of_chorus}`
- Unlabeled sections (Intro, Outro, Solo): `{comment: Intro}`
