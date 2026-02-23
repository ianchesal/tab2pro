# tab2pro

A CLI tool that fetches chord/tab pages from music sites and converts them to [ChordPro](https://www.chordpro.org/chordpro/chordpro-introduction/) (`.cho`) format.

**Supported sites:**
- [Ultimate Guitar](https://tabs.ultimate-guitar.com) (`tabs.ultimate-guitar.com`)
- [Rukind](http://www.rukind.com) (`rukind.com/gdpedia/titles/tab/`)
- [Dylan Chords](http://www.dylanchords.com) (`dylanchords.com`)

## Installation

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone <repo>
cd ultimate-guitar-scraper
uv sync
```

## Usage

```bash
uv run tab2pro <url>
```

By default the output is written to `<artist>-<title>.cho` in the current directory.

### Options

```
Usage: tab2pro [OPTIONS] URL

  Convert a chord tab page to ChordPro format.

  Supported sites:
    - tabs.ultimate-guitar.com
    - rukind.com
    - dylanchords.com

Options:
  -o, --output PATH  Output file path (default: <artist>-<title>.cho)
  --stdout           Print to stdout instead of writing a file.
  --browser          Use Playwright headless browser (fallback for 403s).
  --version INTEGER  For sites with multiple song versions, pick version N.
                     [default: 1]
  --help             Show this message and exit.
```

### Examples

```bash
# Ultimate Guitar — writes the-band-the-weight.cho
uv run tab2pro https://tabs.ultimate-guitar.com/tab/the-band/the-weight-chords-61592

# Rukind (Grateful Dead)
uv run tab2pro http://www.rukind.com/gdpedia/titles/tab/dark-star

# Dylan Chords — print to stdout
uv run tab2pro --stdout http://www.dylanchords.com/02_freewheelin/blowin_in_the_wind

# Dylan Chords — pick the second version of a multi-version song
uv run tab2pro --version 2 http://www.dylanchords.com/02_freewheelin/blowin_in_the_wind

# Custom output path
uv run tab2pro -o ~/songs/dark-star.cho http://www.rukind.com/gdpedia/titles/tab/dark-star
```

## Output format

Standard ChordPro `.cho` files with chords inline:

```
{title: The Weight}
{artist: The Band}
{key: D}
{capo: 2}

{start_of_verse: Verse 1}
I [D]pulled into Nazareth, was feelin' about [G]half past [D]dead
{end_of_verse}

{start_of_chorus}
[D]Take a load off [G]Fanny
{end_of_chorus}
```

Section label mapping:

| Label | ChordPro directive |
|---|---|
| `Verse`, `Verse N` | `{start_of_verse: Verse N}` / `{end_of_verse}` |
| `Chorus` | `{start_of_chorus}` / `{end_of_chorus}` |
| `Bridge` | `{start_of_bridge}` / `{end_of_bridge}` |
| `Intro`, `Outro`, `Solo`, `Interlude`, … | `{comment: <label>}` |
| Unlabeled | *(no directive)* |

## Architecture

The tool uses a **site adapter pattern**. Each site has one adapter that handles fetching and parsing. All adapters produce the same canonical `Song` model, which the site-agnostic formatter renders to ChordPro.

```
URL → Registry → Adapter.fetch() → raw HTML
                → Adapter.extract() → Song
                                    → ChordProFormatter.render() → .cho
```

### Adding a new site

1. Create `src/tab2pro/adapters/newsite.py` implementing `SiteAdapter`:
   - `can_handle(url)` — returns True for URLs this adapter owns
   - `fetch(url)` — returns raw HTML (raise `FetchError` on failure)
   - `extract(html, url)` — returns a `Song` with chords already inline as `[ChordName]`
2. Register it in `src/tab2pro/registry.py`

That's it — nothing else changes.

## Development

```bash
# Run unit tests (no network)
uv run pytest -m "not integration"

# Run with coverage
uv run pytest --cov=tab2pro -m "not integration"

# Run all tests including live network
uv run pytest
```

Tests live in `tests/`. Fixture HTML files for offline adapter tests are in `tests/fixtures/`. Integration tests (live network) are marked `@pytest.mark.integration` and skipped by default.
