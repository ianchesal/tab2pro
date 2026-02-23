"""Shared parsing utilities used by all site adapters.

Implements the chord-above-lyric → inline ChordPro merge pipeline:

  1. classify_line()              — BLANK / SECTION / CHORD / TAB / LYRIC
  2. extract_chords_with_offsets() — (column, name) pairs from a chord line
  3. merge_chord_lyric_lines()    — insert chords inline into a lyric line
  4. extract_section_label()      — human-readable label from a section line
  5. parse_text_tab()             — full pipeline: raw text → list[Section]

Two chord notation styles are supported:

  "bracketed"   — Ultimate Guitar: [D]  [Am7]  [G/B]
  "unbracketed" — Rukind:           D    Am7    G/B   (space-aligned)
"""

import re
from enum import Enum, auto

from ..models import Line, Section

# ---------------------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------------------

# Valid chord name without brackets.
# Handles:
#   Standard:          A, Am, Am7, Amaj7, Asus4, G/B, C#m7
#   Lowercase bass:    D/a, C/b, D/f#   (Dylanchords style)
#   Standalone bass:   /b, /a, /f#      (Dylanchords continuation chords)
CHORD_NAME_RE = re.compile(
    r"^(?:"
    r"[A-G][#b]?(?:m(?:aj)?|aug|dim|sus|add)?\d*(?:\/[A-Ga-g][#b]?)?"
    r"|"
    r"\/[A-Ga-g][#b]?"  # standalone slash-bass token, e.g. /b, /f#
    r")$"
)

# A bracketed chord token: [D], [Am7], [G/B]
# (brackets whose content matches a chord name)
_CHORD_BRACKET_PAT = (
    r"\[([A-G][#b]?"
    r"(?:m(?:aj)?|aug|dim|sus|add)?"
    r"\d*"
    r"(?:\/[A-G][#b]?)?)\]"
)
BRACKETED_CHORD_TOKEN_RE = re.compile(_CHORD_BRACKET_PAT)

# Any [token] group regardless of content
ANY_BRACKET_RE = re.compile(r"\[([^\]]+)\]")

# Known section-header keywords (case-insensitive)
SECTION_KEYWORDS_RE = re.compile(
    r"^(?:Verse|Chorus|Bridge|Intro|Outro|Solo|Interlude|Instrumental|"
    r"Pre-?Chorus|Tag|Coda|Refrain|Hook)(?:\s+\d+)?$",
    re.IGNORECASE,
)

# ASCII guitar tab line: e|--0-1-3--, B|--1--
# ASCII guitar tab line.  Two formats appear in the wild:
#   Standard:  e|---0---1---  (string name + pipe + fret chars)
#   Rukind:    E---------2--  (string name + dashes, no leading pipe)
# Match either: string-name followed by "|" + dash-or-digit,  or  "--".
TAB_LINE_RE = re.compile(r"^[eEBGDAd](?:\|[-\d]|--)")

# Tab notation legend line: "(^) Slide Up  (\) Slide Down  (h) Hammer On ..."
# These appear in many tab sites as a key to the notation symbols used.
TAB_LEGEND_RE = re.compile(r"\([\\^hpb]\)\s+\w")


# ---------------------------------------------------------------------------
# LineType
# ---------------------------------------------------------------------------


class LineType(Enum):
    BLANK = auto()  # empty or whitespace only
    SECTION = auto()  # section header: [Verse 1], Chorus:
    CHORD = auto()  # chord-only line: [D]  [G]  [Am7]  or  D  G  Am7
    TAB = auto()  # ASCII guitar tab line: e|--0--1--
    LYRIC = auto()  # everything else


# ---------------------------------------------------------------------------
# Line classification
# ---------------------------------------------------------------------------


def classify_line(line: str, style: str) -> LineType:
    """Classify a single line of tab text.

    Args:
        line:  A single line of raw text.
        style: ``"bracketed"`` (UG) or ``"unbracketed"`` (Rukind).

    Returns:
        The :class:`LineType` for this line.
    """
    stripped = line.strip()
    if not stripped:
        return LineType.BLANK
    if TAB_LINE_RE.match(stripped) or TAB_LEGEND_RE.search(stripped):
        return LineType.TAB
    if style == "bracketed":
        return _classify_bracketed(stripped)
    return _classify_unbracketed(stripped)


def _classify_bracketed(line: str) -> LineType:
    all_tokens = ANY_BRACKET_RE.findall(line)
    remainder = ANY_BRACKET_RE.sub("", line).strip()

    if not all_tokens:
        return LineType.LYRIC

    if remainder:
        # Non-bracket text alongside bracket tokens → lyric with inline chords
        # (or plain lyric — either way it's content, not a chord line)
        return LineType.LYRIC

    # Entire line is [token] groups.
    if len(all_tokens) == 1 and not CHORD_NAME_RE.match(all_tokens[0]):
        # Single non-chord bracket → section header: [Verse 1], [Chorus]
        return LineType.SECTION

    if all(CHORD_NAME_RE.match(t) for t in all_tokens):
        return LineType.CHORD

    # Shouldn't normally occur; treat as lyric to be safe
    return LineType.LYRIC


def _classify_unbracketed(line: str) -> LineType:
    # Handle [Label] style sections that appear even in unbracketed content
    m = re.match(r"^\[([^\]]+)\]$", line)
    if m and not CHORD_NAME_RE.match(m.group(1)):
        return LineType.SECTION

    # Plain section keyword: "Verse 1", "Chorus:", "Bridge"
    candidate = line.rstrip(":").strip()
    if SECTION_KEYWORDS_RE.match(candidate):
        return LineType.SECTION

    # All whitespace-separated tokens are chord names → chord line
    tokens = line.split()
    if tokens and all(CHORD_NAME_RE.match(t) for t in tokens):
        return LineType.CHORD

    return LineType.LYRIC


# ---------------------------------------------------------------------------
# Chord extraction
# ---------------------------------------------------------------------------


def extract_chords_with_offsets(line: str, style: str) -> list[tuple[int, str]]:
    """Return ``(column_offset, chord_name)`` pairs from a chord line.

    The offset is the character position of the chord's opening ``[`` (bracketed)
    or first letter (unbracketed) in the original *line*.  This offset is used by
    :func:`merge_chord_lyric_lines` to position the chord inside the lyric.

    Args:
        line:  A CHORD-classified line.
        style: ``"bracketed"`` or ``"unbracketed"``.

    Returns:
        List of ``(offset, name)`` tuples sorted left to right.
    """
    if style == "bracketed":
        return [(m.start(), m.group(1)) for m in BRACKETED_CHORD_TOKEN_RE.finditer(line)]
    # unbracketed: each non-whitespace run that is a valid chord name
    return [
        (m.start(), m.group()) for m in re.finditer(r"\S+", line) if CHORD_NAME_RE.match(m.group())
    ]


# ---------------------------------------------------------------------------
# Merge algorithm
# ---------------------------------------------------------------------------


def merge_chord_lyric_lines(chord_line: str, lyric_line: str, style: str) -> str:
    """Merge a chord line and its lyric line into a single inline ChordPro line.

    Chords are inserted at the column offset they occupied in *chord_line*.  If
    a chord's offset exceeds the current length of the (growing) result string,
    the chord is appended to the end rather than silently dropped.

    Example (bracketed style)::

        chord_line = "      [D]              [G]                 [D]"
        lyric_line = "I pulled into Nazareth, was feelin' about half past dead"
        result     = "I [D]pulled into Nazareth, was feelin' about [G]half past [D]dead"

    Args:
        chord_line: A CHORD-classified line.
        lyric_line: The LYRIC line immediately following *chord_line*.
        style:      ``"bracketed"`` or ``"unbracketed"``.

    Returns:
        The lyric line with ``[ChordName]`` brackets inserted inline.
    """
    chords = extract_chords_with_offsets(chord_line, style)
    if not chords:
        return lyric_line

    result = lyric_line
    inserted = 0  # total characters inserted so far (adjusts all future offsets)

    for offset, name in chords:
        bracket = f"[{name}]"
        pos = min(offset + inserted, len(result))
        result = result[:pos] + bracket + result[pos:]
        inserted += len(bracket)

    return result


# ---------------------------------------------------------------------------
# Section label extraction
# ---------------------------------------------------------------------------


def extract_section_label(line: str) -> str:
    """Return the human-readable label from a SECTION line.

    Handles ``[Verse 1]``, ``Chorus:``, and bare ``Bridge`` formats.
    """
    stripped = line.strip()
    m = re.match(r"^\[([^\]]+)\]$", stripped)
    if m:
        return m.group(1)
    return stripped.rstrip(":").strip()


# ---------------------------------------------------------------------------
# Full parser
# ---------------------------------------------------------------------------


def parse_text_tab(text: str, style: str) -> list[Section]:
    """Parse raw tab text into a list of :class:`~tab2pro.models.Section` objects.

    This is the shared core parsing pipeline used by all adapters.  By the time
    this function returns, every :class:`~tab2pro.models.Line` contains chords
    embedded inline using ChordPro bracket notation.

    Algorithm
    ---------
    1. Split *text* into lines and classify each one.
    2. Group lines into sections using SECTION markers as boundaries.
    3. Within each section, pair each CHORD line with the LYRIC line that
       immediately follows it and merge them with :func:`merge_chord_lyric_lines`.
    4. CHORD lines not followed by a LYRIC line (instrumental passages) are
       emitted as chord-only lines: ``[D] [G] [A]``.
    5. BLANK and TAB lines are skipped.

    Args:
        text:  Raw tab text as extracted from the source page.
        style: ``"bracketed"`` (UG) or ``"unbracketed"`` (Rukind).

    Returns:
        Ordered list of :class:`~tab2pro.models.Section` objects.
    """
    lines = text.splitlines()
    sections: list[Section] = []
    current = Section(label=None)

    i = 0
    while i < len(lines):
        lt = classify_line(lines[i], style)

        if lt in (LineType.BLANK, LineType.TAB):
            i += 1
            continue

        if lt == LineType.SECTION:
            if current.lines:
                sections.append(current)
            current = Section(label=extract_section_label(lines[i]))
            i += 1
            continue

        if lt == LineType.CHORD:
            next_lt = classify_line(lines[i + 1], style) if i + 1 < len(lines) else None
            if next_lt == LineType.LYRIC:
                merged = merge_chord_lyric_lines(lines[i], lines[i + 1], style)
                current.lines.append(Line(content=merged))
                i += 2
            else:
                # Chord-only passage (instrumental / intro riff with no lyric)
                chord_names = [n for _, n in extract_chords_with_offsets(lines[i], style)]
                current.lines.append(Line(content=" ".join(f"[{n}]" for n in chord_names)))
                i += 1
            continue

        # LineType.LYRIC — lyric with no preceding chord line
        current.lines.append(Line(content=lines[i]))
        i += 1

    if current.lines:
        sections.append(current)

    return sections
