# TODO / Future Ideas

A running list of improvements and features that would be nice to have.
Contributions welcome — see the adapter pattern in `CLAUDE.md` for how to add a new site.

---

## New Site Adapters

- **Chordie** (`chordie.com`) — large chord/tab repository
- **E-Chords** (`e-chords.com`) — another large database
- **Chordify** (`chordify.net`) — auto-generated chords from audio
- **Musicnotes** (`musicnotes.com`) — sheet music with chord annotations
- **Tabs4Acoustic** (`tabs4acoustic.com`) — acoustic-focused tab site
- **Local file input** — accept a plain-text tab file as input instead of a URL (useful for tabs downloaded or typed by hand)

---

## CLI Improvements

- **Batch mode** — accept a file of URLs (one per line) and convert all of them in one run
- **`--dry-run` flag** — print the parsed `Song` structure (title, artist, sections, chord count) without writing output; useful for debugging a new adapter
- **`--list-versions` flag** — for multi-version sites (Dylan Chords), print the available versions and exit without writing output
- **`--format` option** — support output formats beyond ChordPro, e.g. plain text or JSON (Song model dump)
- **Shell completion** — add `click`-generated shell completion for bash/zsh/fish
- **Config file** — support a `~/.tab2prorc` (TOML/INI) for persistent defaults (output directory, preferred version, etc.)

---

## Parsing & Accuracy

- **Capo detection from text** — some sites bury capo info in free-text annotations rather than structured metadata; add heuristic extraction
- **Key transposition** — `--transpose N` semitones flag, implemented in the formatter layer
- **Chord normalization** — canonicalize enharmonic equivalents (`Db` ↔ `C#`) and simplify redundant voicings
- **Tab-block extraction** — currently ASCII guitar tab blocks are skipped; optionally render them as `{textblock}` ChordPro directives
- **Confidence scoring** — report a parse confidence score when the heuristic chord/lyric merger is uncertain (e.g. ambiguous unbracketed lines)
- **Playwright as a first-class dependency** — right now it's an optional fallback; consider making it easier to install via an extras group (`uv add tab2pro[browser]`)

---

## Output & Integration

- **iReal Pro export** — generate `.irealb` files for use in iReal Pro (complex format, but highly requested in the guitarist community)
- **OpenSong export** — another open chord chart format used by worship software
- **`{define:}` directives** — emit ChordPro `{define:}` blocks for unusual chords with fingering diagrams when the source site provides them
- **PDF rendering** — pipe output through `chordpro` CLI or `chordsong` to produce a PDF directly
- **Watch mode** — `--watch` flag that re-fetches and re-renders when the source page changes (useful during rehearsal prep)

---

## Testing & Quality

- **More fixture coverage** — add saved HTML fixtures for edge-case pages (instrumental-only sections, very long songs, unusual section labels, unicode song titles)
- **Property-based tests** — use `hypothesis` to fuzz the chord-merge algorithm with random chord/lyric line combinations
- **Snapshot tests** — store golden `.cho` files alongside fixtures and diff against them on each run
- **CI pipeline** — GitHub Actions workflow running unit tests on Python 3.12 and 3.13, with coverage reporting
- **Pre-commit hooks** — `ruff` linting + `pyright` type checking on commit

---

## Developer Experience

- **Adapter scaffold script** — `tab2pro new-adapter <site-name>` that generates the boilerplate adapter file with all abstract methods stubbed out
- **Debug HTML dump** — `--save-html PATH` flag to write the raw fetched HTML to disk for offline debugging
- **Verbose logging** — `--verbose` / `-v` flag that emits structured logs (section boundaries detected, chord lines merged, etc.)
- **Type stubs** — add `py.typed` marker and ensure `pyright` passes in strict mode
