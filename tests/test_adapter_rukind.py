from pathlib import Path

import pytest

from tab2pro.adapters.rukind import RukindAdapter
from tab2pro.exceptions import ParseError

FIXTURE = Path(__file__).parent / "fixtures" / "rukind" / "dark-star.html"
TEST_URL = "http://www.rukind.com/gdpedia/titles/tab/dark-star"


def load_fixture() -> str:
    return FIXTURE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# can_handle
# ---------------------------------------------------------------------------


def test_can_handle_rukind_url():
    assert RukindAdapter.can_handle(TEST_URL)


def test_cannot_handle_ug_url():
    assert not RukindAdapter.can_handle("https://tabs.ultimate-guitar.com/tab/foo")


def test_cannot_handle_dylanchords_url():
    assert not RukindAdapter.can_handle("http://www.dylanchords.com/song")


# ---------------------------------------------------------------------------
# extract — metadata
# ---------------------------------------------------------------------------


def test_extract_title():
    song = RukindAdapter().extract(load_fixture(), TEST_URL)
    assert song.title == "Dark Star"


def test_extract_artist_always_grateful_dead():
    song = RukindAdapter().extract(load_fixture(), TEST_URL)
    assert song.artist == "Grateful Dead"


def test_extract_source_url():
    song = RukindAdapter().extract(load_fixture(), TEST_URL)
    assert song.source_url == TEST_URL


# ---------------------------------------------------------------------------
# extract — sections and content
# ---------------------------------------------------------------------------


def test_extract_sections_non_empty():
    song = RukindAdapter().extract(load_fixture(), TEST_URL)
    assert len(song.sections) >= 1


def test_extract_intro_section_label():
    song = RukindAdapter().extract(load_fixture(), TEST_URL)
    labels = [s.label for s in song.sections]
    assert "Intro" in labels


def test_extract_chords_inline():
    song = RukindAdapter().extract(load_fixture(), TEST_URL)
    all_lines = [line.content for s in song.sections for line in s.lines]
    assert any("[" in line for line in all_lines)


def test_extract_tab_blocks_not_in_output():
    # Tab lines (e|--, B|--) should never appear as content lines
    song = RukindAdapter().extract(load_fixture(), TEST_URL)
    for section in song.sections:
        for line in section.lines:
            assert not line.content.startswith("e|")
            assert not line.content.startswith("B|")
            assert not line.content.startswith("G|")


def test_extract_verse_section_label():
    # The Verse section should exist (tab block between two pre blocks is skipped)
    song = RukindAdapter().extract(load_fixture(), TEST_URL)
    labels = [s.label for s in song.sections]
    assert "Verse" in labels


# ---------------------------------------------------------------------------
# extract — error cases
# ---------------------------------------------------------------------------


def test_extract_missing_tab_div_raises_parse_error():
    with pytest.raises(ParseError):
        RukindAdapter().extract("<html><body><h1>Dark Star</h1></body></html>", TEST_URL)
