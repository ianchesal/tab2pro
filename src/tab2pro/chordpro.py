"""Site-agnostic ChordPro formatter.

Renders a :class:`~tab2pro.models.Song` to ChordPro (``.cho``) text.

Section label → ChordPro directive mapping
------------------------------------------

+--------------------------------------+------------------------------------+
| Label (case-insensitive prefix)      | Directive pair                     |
+======================================+====================================+
| ``Verse``, ``Verse N``               | ``{start_of_verse: Verse N}`` /    |
|                                      | ``{end_of_verse}``                 |
+--------------------------------------+------------------------------------+
| ``Chorus``                           | ``{start_of_chorus}`` /            |
|                                      | ``{end_of_chorus}``                |
+--------------------------------------+------------------------------------+
| ``Bridge``                           | ``{start_of_bridge}`` /            |
|                                      | ``{end_of_bridge}``                |
+--------------------------------------+------------------------------------+
| ``Intro``, ``Outro``, ``Solo``,      | ``{comment: <label>}``             |
| ``Interlude``, ``Instrumental``,     | (no matching ChordPro standard)    |
| ``Pre-Chorus``, ``Tag``, ``Coda``,   |                                    |
| ``Refrain``, ``Hook``                |                                    |
+--------------------------------------+------------------------------------+
| ``None`` / unlabeled                 | no wrapper directive               |
+--------------------------------------+------------------------------------+

Usage::

    from tab2pro.chordpro import ChordProFormatter
    formatter = ChordProFormatter()
    text = formatter.render(song)
    Path("output.cho").write_text(text)
"""

import re

from .models import Section, Song

# Section labels whose directives ChordPro has standardised.
_STRUCTURED = {
    "verse": ("start_of_verse", "end_of_verse"),
    "chorus": ("start_of_chorus", "end_of_chorus"),
    "bridge": ("start_of_bridge", "end_of_bridge"),
}

# Section labels that exist in ChordPro as comment annotations only.
_COMMENT_KEYWORDS_RE = re.compile(
    r"^(?:Intro|Outro|Solo|Interlude|Instrumental|Pre-?Chorus|Tag|Coda|Refrain|Hook)",
    re.IGNORECASE,
)


class ChordProFormatter:
    """Render a :class:`~tab2pro.models.Song` to ChordPro text."""

    def render(self, song: Song) -> str:
        """Return ChordPro text for *song*.

        The returned string ends with a single newline and uses Unix line
        endings (``\\n``) throughout.
        """
        parts: list[str] = []

        # --- Metadata block ---
        parts.append(f"{{title: {song.title}}}")
        parts.append(f"{{artist: {song.artist}}}")
        if song.key:
            parts.append(f"{{key: {song.key}}}")
        if song.capo:
            parts.append(f"{{capo: {song.capo}}}")
        if song.tuning:
            parts.append(f"{{tuning: {song.tuning}}}")

        # --- Section blocks ---
        for section in song.sections:
            parts.append("")  # blank line before every section
            parts.extend(_render_section(section))

        return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _render_section(section: Section) -> list[str]:
    """Return a list of lines for one section (no trailing blank line)."""
    label = section.label
    lines = [line.content for line in section.lines]

    if not label:
        # Unlabeled — just emit content lines with no wrapper
        return lines

    label_lower = label.lower().split()[0]  # first word, e.g. "verse" from "Verse 1"

    # Structured directives: verse / chorus / bridge
    if label_lower in _STRUCTURED:
        start_dir, end_dir = _STRUCTURED[label_lower]
        # Include the full label for verse (e.g. "Verse 1"), bare directive for chorus/bridge
        if label_lower == "verse":
            start_line = f"{{{start_dir}: {label}}}"
        else:
            start_line = f"{{{start_dir}}}"
        return [start_line, *lines, f"{{{end_dir}}}"]

    # Comment annotation: Intro, Outro, Solo, etc.
    if _COMMENT_KEYWORDS_RE.match(label):
        return [f"{{comment: {label}}}", *lines]

    # Fallback for any other label — treat as a comment
    return [f"{{comment: {label}}}", *lines]
