from pathlib import Path

import pytest

from tab2pro.adapters.dylanchords import DylanchordsAdapter
from tab2pro.exceptions import ParseError

FIXTURE = Path(__file__).parent / "fixtures" / "dylanchords" / "blowin-in-the-wind.html"
TEST_URL = "http://www.dylanchords.com/02_freewheelin/blowin_in_the_wind"


def load_fixture() -> str:
    return FIXTURE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# can_handle
# ---------------------------------------------------------------------------


def test_can_handle_dylanchords_url():
    assert DylanchordsAdapter.can_handle(TEST_URL)


def test_cannot_handle_ug_url():
    assert not DylanchordsAdapter.can_handle("https://tabs.ultimate-guitar.com/tab/foo")


def test_cannot_handle_rukind_url():
    assert not DylanchordsAdapter.can_handle("http://www.rukind.com/gdpedia/titles/tab/dark-star")


# ---------------------------------------------------------------------------
# extract — metadata
# ---------------------------------------------------------------------------


def test_extract_title():
    song = DylanchordsAdapter().extract(load_fixture(), TEST_URL)
    assert song.title == "Blowin' in the Wind"


def test_extract_artist_always_bob_dylan():
    song = DylanchordsAdapter().extract(load_fixture(), TEST_URL)
    assert song.artist == "Bob Dylan"


def test_extract_capo_version_1():
    song = DylanchordsAdapter().extract(load_fixture(), TEST_URL)
    assert song.capo == 7


def test_extract_source_url():
    song = DylanchordsAdapter().extract(load_fixture(), TEST_URL)
    assert song.source_url == TEST_URL


# ---------------------------------------------------------------------------
# extract — versions
# ---------------------------------------------------------------------------


def test_extract_version_1_default():
    song = DylanchordsAdapter().extract(load_fixture(), TEST_URL)
    assert len(song.sections) >= 1


def test_extract_version_2_no_capo():
    # Version 2 in our fixture has no <p> capo tag
    song = DylanchordsAdapter(version=2).extract(load_fixture(), TEST_URL)
    assert song.capo is None


def test_extract_version_2_has_content():
    song = DylanchordsAdapter(version=2).extract(load_fixture(), TEST_URL)
    assert len(song.sections) >= 1


def test_extract_invalid_version_raises_parse_error():
    with pytest.raises(ParseError, match="version"):
        DylanchordsAdapter(version=99).extract(load_fixture(), TEST_URL)


# ---------------------------------------------------------------------------
# extract — content
# ---------------------------------------------------------------------------


def test_extract_chords_inline():
    song = DylanchordsAdapter().extract(load_fixture(), TEST_URL)
    all_lines = [line.content for s in song.sections for line in s.lines]
    assert any("[" in line for line in all_lines)


def test_extract_chordcharts_skipped():
    # chordcharts pre blocks contain chord definitions like "G 320003"
    # They should NOT appear as song lines
    song = DylanchordsAdapter().extract(load_fixture(), TEST_URL)
    for section in song.sections:
        for line in section.lines:
            assert "320003" not in line.content


# ---------------------------------------------------------------------------
# extract — error cases
# ---------------------------------------------------------------------------


def test_extract_no_content_area_raises_parse_error():
    with pytest.raises(ParseError):
        DylanchordsAdapter().extract("<html><body><h1>Title</h1></body></html>", TEST_URL)
