from dataclasses import dataclass, field


@dataclass
class Line:
    """A single line of lyrics with chords already embedded inline.

    Example: "I [D]pulled into Nazareth, was feelin' about [G]half past [D]dead"
    Chord-only lines (instrumental passages) will have content like "[D] [G] [A]".
    """

    content: str


@dataclass
class Section:
    """A labelled section of a song (verse, chorus, bridge, etc.)."""

    label: str | None  # e.g. "Verse 1", "Chorus", None for unlabelled passages
    lines: list[Line] = field(default_factory=list)


@dataclass
class Song:
    """Canonical representation of a song, site-agnostic."""

    title: str
    artist: str
    sections: list[Section] = field(default_factory=list)
    key: str | None = None
    capo: int | None = None
    tuning: str | None = None  # e.g. "Drop D", "DADGAD"
    source_url: str = ""
