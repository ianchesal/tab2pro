# Implementation Plan: Multi-Site Chord Scraper → ChordPro

## Goal

Build a CLI tool that:
1. Accepts a chord/tab page URL from any supported site
2. Automatically detects which site the URL belongs to and dispatches to the right adapter
3. Fetches and parses the page to extract song metadata and chord/lyric content
4. Converts the content to ChordPro format
5. Writes the result to a `.cho` file

**Supported sites (initial):**
- Ultimate Guitar (`tabs.ultimate-guitar.com`)
- Rukind (`rukind.com/gdpedia/titles/tab/`)
- Dylan Chords (`dylanchords.com`)

---

## Architecture Overview

The core design is a **site adapter pattern** with a shared canonical data model:

```
URL
 │
 ▼
Registry ──► finds adapter via can_handle(url)
 │
 ▼
Adapter.fetch(url) ──► raw HTML
 │
 ▼
Adapter.extract(html, url) ──► Song  ← canonical model
 │
 ▼
ChordProFormatter.render(song) ──► .cho file
```

Each site gets its own adapter. All adapters implement the same interface and produce the same `Song` datamodel. The ChordPro formatter is entirely site-agnostic. Adding a new site means adding one new adapter file and registering it — nothing else changes.

---

## Phase 1 — Project Scaffolding

**Tasks:**
- [ ] Add `.gitignore` — cover Python standard ignores (`__pycache__`, `*.pyc`, `.venv`, `dist/`, `*.egg-info/`), uv artifacts (`.uv/`), editor files (`.vscode/`, `.idea/`, `*.swp`), OS files (`.DS_Store`), Claude Code local config (`.claude/settings.local.json`), and any downloaded test fixture HTML files that shouldn't be committed
- [ ] Add `.python-version` — pin the Python version (e.g. `3.12`) so `uv` and other tooling agree
- [ ] Initialize a `pyproject.toml` using `uv init` with `[project.scripts]` entry point (`tab2pro = "tab2pro.cli:main"`)
- [ ] Add dependencies: `httpx`, `beautifulsoup4`, `click`
- [ ] Add dev dependencies: `pytest`, `pytest-cov`, `respx`
- [ ] Create the full package layout (see Structure section in CLAUDE.md)
- [ ] Create `tests/fixtures/` with subdirectories per site
- [ ] Verify `git status` is clean and make an initial commit

---

## Phase 2 — Canonical Data Model (`models.py`)

Define the shared intermediate representation that all adapters produce and the formatter consumes. This is the contract between the site-specific and site-agnostic layers.

```python
from dataclasses import dataclass, field

@dataclass
class Line:
    # Lyric text with chords already embedded inline ChordPro-style.
    # e.g. "I [D]pulled into Nazareth, was feelin' about [G]half past [D]dead"
    # Chord-only lines (instrumental passages) have no lyric text.
    content: str

@dataclass
class Section:
    label: str | None     # e.g. "Verse 1", "Chorus", "Bridge", None for unlabelled
    lines: list[Line] = field(default_factory=list)

@dataclass
class Song:
    title: str
    artist: str
    sections: list[Section] = field(default_factory=list)
    key: str | None = None
    capo: int | None = None
    tuning: str | None = None   # e.g. "Drop D", "DADGAD" (used by Dylanchords)
    source_url: str = ""
```

**Key contract:** By the time an adapter returns a `Song`, all chords must already be **inline** within `Line.content` using ChordPro bracket notation (`[D]`, `[Am7]`, etc.). The formatter does not perform any chord merging — that is the adapter's responsibility.

---

## Phase 3 — Adapter Interface (`adapters/base.py`)

```python
from abc import ABC, abstractmethod
from ..models import Song

class SiteAdapter(ABC):

    @classmethod
    @abstractmethod
    def can_handle(cls, url: str) -> bool:
        """Return True if this adapter knows how to handle the given URL."""

    @abstractmethod
    def fetch(self, url: str) -> str:
        """Fetch the page and return raw HTML. Raise FetchError on failure."""

    @abstractmethod
    def extract(self, html: str, url: str) -> Song:
        """Parse HTML and return a canonical Song. Raise ParseError on failure."""

    def scrape(self, url: str) -> Song:
        """Convenience: fetch + extract in one call."""
        html = self.fetch(url)
        return self.extract(html, url)
```

**Custom exceptions** (in `exceptions.py`):
- `FetchError(url, status_code)` — HTTP-level failure
- `ParseError(url, reason)` — Could not extract expected data from the page
- `UnsupportedSiteError(url)` — No adapter matched the URL

---

## Phase 4 — Adapter Registry (`registry.py`)

A simple registry that holds all known adapter classes and finds the right one for a URL.

```python
from .adapters.ultimate_guitar import UltimateGuitarAdapter
from .adapters.rukind import RukindAdapter
from .adapters.dylanchords import DylanchordsAdapter

_ADAPTERS: list[type[SiteAdapter]] = [
    UltimateGuitarAdapter,
    RukindAdapter,
    DylanchordsAdapter,
]

def get_adapter(url: str) -> SiteAdapter:
    for cls in _ADAPTERS:
        if cls.can_handle(url):
            return cls()
    raise UnsupportedSiteError(url)
```

To add a new site: create `adapters/newsite.py`, implement `SiteAdapter`, add to `_ADAPTERS`. Done.

---

## Phase 5 — Shared Parsing Utilities (`adapters/utils.py`)

The most complex parsing logic — merging chord lines into lyric lines — is common across all three target sites. Extracting it into a shared utility means each adapter can reuse it with minor configuration.

### Problem: Two chord notation styles

| Site | Chord notation | Example chord line |
|---|---|---|
| Ultimate Guitar | Bracketed | `      [D]              [G]` |
| Rukind | Unbracketed, space-aligned | `      D              G` |
| Dylanchords | Likely bracketed or unbracketed | TBD on first integration |

### Shared algorithm: `merge_chord_lyric_lines(chord_line, lyric_line, style)`

1. **Scan** the chord line from left to right.
2. **Extract** each chord token and its start character offset.
3. For each chord, **calculate the insertion point** in the lyric line (same character offset, adjusted for chords already inserted before it).
4. **Insert** `[ChordName]` at that position in the lyric string.
5. Return the merged lyric string.

The `style` parameter tells the function whether to expect `[D]` (strip brackets to get name) or bare `D` (treat as-is).

### Shared algorithm: `classify_line(line, style) -> LineType`

Determines whether a line is:
- `SECTION` — matches section header patterns (`[Verse 1]`, `[Chorus]`, `Verse 1:`, etc.)
- `CHORD` — all space-separated tokens are valid chord names (regex: `[A-G][#b]?(m|maj|min|aug|dim|sus|add)?[0-9]*(\/[A-G][#b]?)?`)
- `BLANK` — empty or whitespace only
- `LYRIC` — everything else

The `style` parameter handles `[D]` vs bare `D` chord notation.

### Shared algorithm: `parse_text_tab(text, style) -> list[Section]`

Full pipeline that takes raw tab text and returns parsed sections:
1. Split into lines
2. Classify each line
3. Group into sections by `SECTION` markers
4. Within each section, pair `CHORD` + `LYRIC` lines and merge them
5. Handle chord-only passages (no following lyric)

---

## Phase 6 — Site-Specific Adapters

### 6a — Ultimate Guitar (`adapters/ultimate_guitar.py`)

**URL pattern:** `tabs.ultimate-guitar.com/tab/...`

**Fetch:** `httpx` GET with browser-like headers:
```
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...
Accept-Language: en-US,en;q=0.9
```
Optional `--browser` flag falls back to `playwright` (Chromium) for persistent 403s.

**Extract:**
1. Find `<script id="__NEXT_DATA__" type="application/json">` (preferred) or scan script tags for `window.UGAPP`
2. Parse JSON; navigate to `store.page.data.tab_view`
3. Metadata: `song_name`, `artist_name`, `capo`, `tonality_name`
4. Content: `wiki_tab.content`
5. Content may use `[ch]D[/ch]` HTML-like tags — strip to `[D]` before parsing
6. Pass content through `parse_text_tab(text, style="bracketed")`

**Known challenges:**
- 403 without browser headers
- May mix chord content with guitar tab (ASCII tablature) blocks — detect and skip tab blocks

### 6b — Rukind (`adapters/rukind.py`)

**URL pattern:** `rukind.com/gdpedia/titles/tab/...`

**Fetch:** Standard `httpx` GET (no known bot protection).

**Extract:**
1. Find main content area (likely `<div class="field-item">` or `<pre>` tags)
2. Metadata: extract from page `<h1>` and surrounding elements; artist is always "Grateful Dead"
3. Chords are unbracketed (`D  G  A`), space-aligned above lyrics
4. Pass content through `parse_text_tab(text, style="unbracketed")`

**Known challenges:**
- Pages may contain ASCII guitar tab sections mixed with chord sections — detect and skip tab blocks (lines like `e|---0---1---`)
- No structured metadata; capo/key may not be present

### 6c — Dylan Chords (`adapters/dylanchords.py`)

**URL pattern:** `dylanchords.com/...`

**Fetch:** Standard `httpx` GET (Drupal site, no known bot protection).

**Extract:**
1. Find Drupal content area (`<div class="field-items">` or similar)
2. Metadata: title from `<h1>`, writer from structured field, capo from text annotation
3. Pages can have **multiple versions** of a song (different capo/tuning) — by default, extract the first version; expose `--version N` CLI option to select others
4. Chord notation TBD on first integration (likely space-aligned unbracketed or bracketed)
5. Pass content through `parse_text_tab(text, style=detected)`

**Known challenges:**
- Multiple versions per page; need to present them clearly
- Tuning variants (e.g. "Drop D", "DADGAD") — capture in `Song.tuning`

---

## Phase 7 — ChordPro Formatter (`chordpro.py`)

Site-agnostic. Renders a `Song` to ChordPro text.

```
{title: The Weight}
{artist: The Band}
{key: D}
{capo: 2}

{start_of_verse: Verse 1}
I [D]pulled into Nazareth, was feelin' about [G]half past [D]dead
I just need some place where I can [G]lay my [D]head
{end_of_verse}

{start_of_chorus}
[D]Take a load off [G]Fanny
[D]Take a load for [G]free
{end_of_chorus}
```

**Section label → ChordPro directive mapping:**

| Label (case-insensitive) | `start_of_*` directive |
|---|---|
| `Verse`, `Verse N` | `start_of_verse: Verse N` |
| `Chorus` | `start_of_chorus` |
| `Bridge` | `start_of_bridge` |
| `Intro`, `Outro`, `Solo`, `Interlude`, `Instrumental` | `{comment: label}` (no standard directive) |
| `None` / unlabeled | no directive (just emit lines) |

**Rules:**
- Emit metadata block first (`title`, `artist`, then optional `key`, `capo`, `tuning`)
- Blank line between sections
- File extension: `.cho`

---

## Phase 8 — CLI (`cli.py`)

```
Usage: tab2pro [OPTIONS] URL

  Convert a chord tab page to ChordPro format.

  Supported sites:
    - tabs.ultimate-guitar.com
    - rukind.com
    - dylanchords.com

Options:
  -o, --output PATH      Output file (default: <artist>-<title>.cho)
  --stdout               Print to stdout instead of writing a file
  --browser              Use Playwright headless browser (fallback for 403s)
  --version INTEGER      For sites with multiple song versions, pick version N [default: 1]
  --help                 Show this message and exit.
```

**Behavior:**
1. Call `registry.get_adapter(url)` — raises `UnsupportedSiteError` with a helpful message if no adapter matches
2. Run `adapter.scrape(url)` → `Song`
3. Render with `ChordProFormatter`
4. Write to file or stdout
5. Derive default filename from artist + title (slugified, lowercase, hyphens)
6. Non-zero exit code + stderr message on any error

---

## Phase 9 — Tests

**Structure:**
```
tests/
├── fixtures/
│   ├── ultimate_guitar/
│   │   └── the-weight.html     # saved real page HTML
│   ├── rukind/
│   │   └── dark-star.html
│   └── dylanchords/
│       └── blowin-in-the-wind.html
├── test_models.py
├── test_utils.py               # chord merge algorithm unit tests
├── test_adapter_ug.py
├── test_adapter_rukind.py
├── test_adapter_dylanchords.py
├── test_chordpro.py
└── test_cli.py
```

**Unit tests (no network):**
- `test_utils.py`: Cover the chord-merging algorithm with known inputs — bracketed and unbracketed styles, chord-only lines, uneven line lengths, unicode lyrics
- `test_adapter_*.py`: Load fixture HTML, call `adapter.extract(html, url)`, assert resulting `Song` fields
- `test_chordpro.py`: Feed known `Song` objects, assert output string matches expected ChordPro
- `test_cli.py`: Use `click.testing.CliRunner` with mocked adapters

**Integration tests (live network, opt-in):**
- Mark with `@pytest.mark.integration`
- Skip by default: `pytest -m "not integration"`

---

## Decisions & Trade-offs

| Decision | Choice | Rationale |
|---|---|---|
| Architecture | Site adapter pattern | Isolated, independently testable, easy to add new sites |
| HTTP library | `httpx` | Modern API, easy to mock with `respx` |
| HTML parser | `beautifulsoup4` | Handles both modern JSON extraction and old-school HTML |
| CLI framework | `click` | Clean help output, easy testing with CliRunner |
| Package manager | `uv` | Fast, lockfile support |
| Browser fallback | `playwright` (optional dep) | Only install when `--browser` used |
| Chord merging | Shared utility, per-adapter style config | Avoids duplication; handles both bracketed and unbracketed |
| Output format | `.cho` | Per ChordPro spec |
| Multiple versions | Default to first; `--version N` to select | Pragmatic default; Dylanchords often has many versions |

---

## Open Questions

1. **Dylanchords chord notation** — Is it bracketed `[D]` or unbracketed `D`? Confirm on first integration by inspecting a live page.
2. **UG `[ch]` tags** — Does the JSON content use `[ch]D[/ch]` or plain `[D]`? Need to check against real fetched JSON.
3. **Rukind mixed tab/chord pages** — How common are pages with guitar tab (ASCII) sections? Does every page have them, or only some? Define the skip heuristic.
4. **Dylanchords multi-version UX** — Should the default behavior extract all versions into one file (with `{comment:}` separators), or just the first? Consider what's most useful for a ChordPro app.
5. **Tool rename** — The CLI entry point is currently `ug2chordpro`, named for Ultimate Guitar only. With multi-site support, consider renaming to something like `tab2pro` or `chord2pro`.
