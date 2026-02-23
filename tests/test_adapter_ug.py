import json
from pathlib import Path

import pytest

from tab2pro.adapters.ultimate_guitar import UltimateGuitarAdapter
from tab2pro.exceptions import ParseError

FIXTURE = Path(__file__).parent / "fixtures" / "ultimate_guitar" / "the-weight.html"
TEST_URL = "https://tabs.ultimate-guitar.com/tab/the-band/the-weight-chords-61592"


def load_fixture() -> str:
    return FIXTURE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# can_handle
# ---------------------------------------------------------------------------


def test_can_handle_ug_url():
    assert UltimateGuitarAdapter.can_handle(TEST_URL)


def test_cannot_handle_rukind_url():
    assert not UltimateGuitarAdapter.can_handle("http://www.rukind.com/gdpedia/titles/tab/dark-star")


def test_cannot_handle_dylanchords_url():
    assert not UltimateGuitarAdapter.can_handle("http://www.dylanchords.com/song")


# ---------------------------------------------------------------------------
# extract — metadata
# ---------------------------------------------------------------------------


def test_extract_title():
    song = UltimateGuitarAdapter().extract(load_fixture(), TEST_URL)
    assert song.title == "The Weight"


def test_extract_artist():
    song = UltimateGuitarAdapter().extract(load_fixture(), TEST_URL)
    assert song.artist == "The Band"


def test_extract_capo():
    song = UltimateGuitarAdapter().extract(load_fixture(), TEST_URL)
    assert song.capo == 2


def test_extract_key():
    song = UltimateGuitarAdapter().extract(load_fixture(), TEST_URL)
    assert song.key == "D"


def test_extract_source_url():
    song = UltimateGuitarAdapter().extract(load_fixture(), TEST_URL)
    assert song.source_url == TEST_URL


# ---------------------------------------------------------------------------
# extract — sections and content
# ---------------------------------------------------------------------------


def test_extract_sections_non_empty():
    song = UltimateGuitarAdapter().extract(load_fixture(), TEST_URL)
    assert len(song.sections) >= 1


def test_extract_verse_section_exists():
    song = UltimateGuitarAdapter().extract(load_fixture(), TEST_URL)
    verse = next((s for s in song.sections if s.label and "Verse" in s.label), None)
    assert verse is not None


def test_extract_verse_has_inline_chords():
    song = UltimateGuitarAdapter().extract(load_fixture(), TEST_URL)
    verse = next(s for s in song.sections if s.label and "Verse" in s.label)
    assert "[D]" in verse.lines[0].content


def test_extract_ch_tags_stripped():
    song = UltimateGuitarAdapter().extract(load_fixture(), TEST_URL)
    for section in song.sections:
        for line in section.lines:
            assert "[ch]" not in line.content
            assert "[/ch]" not in line.content


# ---------------------------------------------------------------------------
# extract — error cases
# ---------------------------------------------------------------------------


def test_extract_missing_next_data_raises_parse_error():
    with pytest.raises(ParseError):
        UltimateGuitarAdapter().extract(
            "<html><body>No __NEXT_DATA__ here</body></html>", TEST_URL
        )


def test_extract_empty_content_raises_parse_error():
    data = {
        "props": {
            "pageProps": {
                "data": {
                    "tab_view": {
                        "song_name": "Test",
                        "artist_name": "Artist",
                        "wiki_tab": {"content": ""},
                    }
                }
            }
        }
    }
    html = (
        f'<script id="__NEXT_DATA__" type="application/json">'
        f"{json.dumps(data)}"
        f"</script>"
    )
    with pytest.raises(ParseError):
        UltimateGuitarAdapter().extract(html, TEST_URL)


def test_extract_malformed_json_raises_parse_error():
    html = '<script id="__NEXT_DATA__" type="application/json">not json</script>'
    with pytest.raises(ParseError):
        UltimateGuitarAdapter().extract(html, TEST_URL)
