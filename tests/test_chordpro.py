from tab2pro.chordpro import ChordProFormatter
from tab2pro.models import Line, Section, Song


def _song(**kwargs) -> Song:
    defaults = dict(title="Dark Star", artist="Grateful Dead")
    defaults.update(kwargs)
    return Song(**defaults)


def _render(song: Song) -> str:
    return ChordProFormatter().render(song)


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_title_and_artist_in_output():
    out = _render(_song())
    assert "{title: Dark Star}" in out
    assert "{artist: Grateful Dead}" in out


def test_optional_metadata_omitted_when_none():
    out = _render(_song())
    assert "{key:" not in out
    assert "{capo:" not in out
    assert "{tuning:" not in out


def test_key_emitted():
    assert "{key: G}" in _render(_song(key="G"))


def test_capo_emitted():
    assert "{capo: 2}" in _render(_song(capo=2))


def test_tuning_emitted():
    assert "{tuning: Drop D}" in _render(_song(tuning="Drop D"))


# ---------------------------------------------------------------------------
# Verse sections
# ---------------------------------------------------------------------------


def test_verse_section_directives():
    song = _song(sections=[
        Section(label="Verse 1", lines=[Line(content="[D]some lyrics")])
    ])
    out = _render(song)
    assert "{start_of_verse: Verse 1}" in out
    assert "{end_of_verse}" in out
    assert "[D]some lyrics" in out


def test_verse_n_label_preserved_in_directive():
    song = _song(sections=[
        Section(label="Verse 2", lines=[Line(content="x")])
    ])
    assert "{start_of_verse: Verse 2}" in _render(song)


# ---------------------------------------------------------------------------
# Chorus / Bridge
# ---------------------------------------------------------------------------


def test_chorus_section_directives():
    song = _song(sections=[
        Section(label="Chorus", lines=[Line(content="[G]chorus line")])
    ])
    out = _render(song)
    assert "{start_of_chorus}" in out
    assert "{end_of_chorus}" in out


def test_bridge_section_directives():
    song = _song(sections=[
        Section(label="Bridge", lines=[Line(content="[A]bridge")])
    ])
    out = _render(song)
    assert "{start_of_bridge}" in out
    assert "{end_of_bridge}" in out


# ---------------------------------------------------------------------------
# Comment sections (Intro, Outro, Solo, …)
# ---------------------------------------------------------------------------


def test_intro_rendered_as_comment():
    song = _song(sections=[Section(label="Intro", lines=[Line(content="[D] [G]")])])
    out = _render(song)
    assert "{comment: Intro}" in out
    assert "{start_of_intro}" not in out


def test_outro_rendered_as_comment():
    song = _song(sections=[Section(label="Outro", lines=[Line(content="[D]")])])
    assert "{comment: Outro}" in _render(song)


def test_solo_rendered_as_comment():
    song = _song(sections=[Section(label="Solo", lines=[Line(content="[D]")])])
    assert "{comment: Solo}" in _render(song)


# ---------------------------------------------------------------------------
# Unlabeled sections
# ---------------------------------------------------------------------------


def test_unlabeled_section_no_directive():
    song = _song(sections=[Section(label=None, lines=[Line(content="plain line")])])
    out = _render(song)
    assert "plain line" in out
    assert "{start_of" not in out
    assert "{comment" not in out


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def test_blank_line_between_sections():
    song = _song(sections=[
        Section(label="Verse 1", lines=[Line(content="line one")]),
        Section(label="Chorus", lines=[Line(content="line two")]),
    ])
    assert "\n\n" in _render(song)


def test_output_ends_with_newline():
    assert _render(_song()).endswith("\n")


def test_metadata_comes_before_sections():
    song = _song(key="D", sections=[
        Section(label="Verse 1", lines=[Line(content="lyric")])
    ])
    out = _render(song)
    title_pos = out.index("{title:")
    verse_pos = out.index("{start_of_verse")
    assert title_pos < verse_pos
