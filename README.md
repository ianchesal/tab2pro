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

### Setup

```bash
git clone <repo>
cd tab2pro
uv sync
```

### Running checks locally

The same checks that run in CI can be run locally via `make`:

```bash
make check       # lint + security + unit tests (mirrors CI exactly)
make lint        # ruff linting only
make format      # auto-format with ruff (writes files)
make security    # bandit SAST + pip-audit dependency scan
make test        # unit tests with coverage (no network)
make test-all    # all tests including live network integration tests
```

Or invoke the tools directly with `uv run`:

```bash
uv run ruff check src tests          # lint
uv run ruff format src tests         # format
uv run bandit -r src/tab2pro -c pyproject.toml   # SAST
uv run pip-audit                     # dependency CVE scan
uv run pytest -m "not integration"   # unit tests
uv run pytest                        # all tests (live network)
```

### Pre-commit hooks (optional)

Install [pre-commit](https://pre-commit.com/) to have ruff and bandit run automatically before every commit:

```bash
pip install pre-commit
pre-commit install
```

After that, `git commit` will run ruff (lint + format) and bandit on staged files and block the commit if anything fails.

### CI

GitHub Actions runs `lint`, `security`, and `test` jobs in parallel on every pull request and every push to `main`. The test job runs against Python 3.12 and 3.13. Pull requests must pass all three jobs before merging.

Tests live in `tests/`. Fixture HTML files for offline adapter tests are in `tests/fixtures/`. Integration tests (live network) are marked `@pytest.mark.integration` and excluded from CI.
