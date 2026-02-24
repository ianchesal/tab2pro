from tab2pro.adapters.utils import (
    LineType,
    classify_line,
    extract_chords_with_offsets,
    extract_section_label,
    merge_chord_lyric_lines,
    parse_text_tab,
)

# ---------------------------------------------------------------------------
# classify_line
# ---------------------------------------------------------------------------


def test_classify_blank():
    assert classify_line("", "bracketed") == LineType.BLANK
    assert classify_line("   ", "unbracketed") == LineType.BLANK


def test_classify_tab_standard():
    assert classify_line("e|--0--1--2--|", "bracketed") == LineType.TAB
    assert classify_line("B|--3--1--0--|", "unbracketed") == LineType.TAB


def test_classify_tab_rukind_format():
    # Rukind uses E-- without leading pipe
    assert classify_line("E------2--", "unbracketed") == LineType.TAB


def test_classify_tab_legend():
    assert (
        classify_line(r"(^) Slide Up  (\) Slide Down  (h) Hammer On", "unbracketed") == LineType.TAB
    )


def test_classify_section_bracketed_single_non_chord():
    assert classify_line("[Verse 1]", "bracketed") == LineType.SECTION
    assert classify_line("[Chorus]", "bracketed") == LineType.SECTION


def test_classify_chord_bracketed():
    assert classify_line("      [D]              [G]", "bracketed") == LineType.CHORD
    assert classify_line("[Am7]   [G/B]   [D]", "bracketed") == LineType.CHORD


def test_classify_lyric_bracketed_inline():
    # Non-bracket text alongside bracket tokens → lyric (inline chords already merged)
    assert classify_line("[D]pulled into Nazareth", "bracketed") == LineType.LYRIC


def test_classify_lyric_bracketed_plain():
    assert classify_line("I pulled into Nazareth", "bracketed") == LineType.LYRIC


def test_classify_section_unbracketed_keyword():
    assert classify_line("Verse 1", "unbracketed") == LineType.SECTION
    assert classify_line("Chorus:", "unbracketed") == LineType.SECTION
    assert classify_line("Bridge", "unbracketed") == LineType.SECTION


def test_classify_chord_unbracketed_basic():
    assert classify_line("D  G  Am7", "unbracketed") == LineType.CHORD


def test_classify_chord_unbracketed_slash_bass():
    # Dylanchords style: G C /b D/a G
    assert classify_line("G  C  /b  D/a  G", "unbracketed") == LineType.CHORD


def test_classify_slash_bass_standalone():
    assert classify_line("/b  /f#", "unbracketed") == LineType.CHORD


def test_classify_lyric_unbracketed():
    assert classify_line("Dark star crashes, pouring its light", "unbracketed") == LineType.LYRIC


# ---------------------------------------------------------------------------
# extract_chords_with_offsets
# ---------------------------------------------------------------------------


def test_extract_offsets_bracketed():
    line = "   [D]   [G]"
    result = extract_chords_with_offsets(line, "bracketed")
    assert result == [(3, "D"), (9, "G")]


def test_extract_offsets_unbracketed():
    line = "D  G  Am7"
    result = extract_chords_with_offsets(line, "unbracketed")
    assert result[0] == (0, "D")
    assert result[1] == (3, "G")
    assert result[2] == (6, "Am7")


def test_extract_offsets_empty_line():
    assert extract_chords_with_offsets("   ", "bracketed") == []
    assert extract_chords_with_offsets("   ", "unbracketed") == []


def test_extract_offsets_slash_bass():
    line = "G  /b  D/a"
    result = extract_chords_with_offsets(line, "unbracketed")
    names = [name for _, name in result]
    assert "G" in names
    assert "/b" in names
    assert "D/a" in names


# ---------------------------------------------------------------------------
# merge_chord_lyric_lines
# ---------------------------------------------------------------------------


def test_merge_bracketed_inserts_at_offset():
    chord_line = "  [D]"
    lyric_line = "I pulled into Nazareth"
    result = merge_chord_lyric_lines(chord_line, lyric_line, "bracketed")
    assert result == "I [D]pulled into Nazareth"


def test_merge_bracketed_multiple_chords():
    chord_line = "  [D]                [G]"
    lyric_line = "I pulled into Nazareth, feelin' half past dead"
    result = merge_chord_lyric_lines(chord_line, lyric_line, "bracketed")
    assert "[D]" in result
    assert "[G]" in result


def test_merge_unbracketed_basic():
    chord_line = "A  G"
    lyric_line = "Dark star crashes"
    result = merge_chord_lyric_lines(chord_line, lyric_line, "unbracketed")
    assert "[A]" in result
    assert "[G]" in result


def test_merge_chord_beyond_lyric_appended():
    # Chord column exceeds lyric length — appended rather than dropped
    chord_line = "                     [D]"
    lyric_line = "Short"
    result = merge_chord_lyric_lines(chord_line, lyric_line, "bracketed")
    assert result.endswith("[D]")


def test_merge_no_chords_returns_lyric_unchanged():
    result = merge_chord_lyric_lines("   ", "Some lyrics here", "bracketed")
    assert result == "Some lyrics here"


def test_merge_preserves_unicode_lyrics():
    chord_line = "[G]     [D]"
    lyric_line = "café au lait"
    result = merge_chord_lyric_lines(chord_line, lyric_line, "bracketed")
    assert "[G]" in result
    assert "[D]" in result
    assert "café" in result


# ---------------------------------------------------------------------------
# extract_section_label
# ---------------------------------------------------------------------------


def test_extract_label_bracketed():
    assert extract_section_label("[Verse 1]") == "Verse 1"
    assert extract_section_label("[Chorus]") == "Chorus"


def test_extract_label_colon():
    assert extract_section_label("Chorus:") == "Chorus"


def test_extract_label_bare():
    assert extract_section_label("Bridge") == "Bridge"


# ---------------------------------------------------------------------------
# parse_text_tab
# ---------------------------------------------------------------------------


def test_parse_text_tab_bracketed_basic():
    text = "[Verse 1]\n   [D]    [G]\nI pulled into Nazareth\n"
    sections = parse_text_tab(text, style="bracketed")
    assert len(sections) == 1
    assert sections[0].label == "Verse 1"
    assert len(sections[0].lines) == 1
    assert "[D]" in sections[0].lines[0].content
    assert "[G]" in sections[0].lines[0].content


def test_parse_text_tab_unbracketed_basic():
    text = "D  G\nDark star crashes\n"
    sections = parse_text_tab(text, style="unbracketed")
    assert len(sections) == 1
    assert "[D]" in sections[0].lines[0].content
    assert "[G]" in sections[0].lines[0].content


def test_parse_text_tab_chord_only_line():
    # Chord line NOT followed by a lyric → chord-only output
    text = "[Verse 1]\n[D]  [G]  [A]\n"
    sections = parse_text_tab(text, style="bracketed")
    content = sections[0].lines[0].content
    assert "[D]" in content
    assert "[G]" in content
    assert "[A]" in content


def test_parse_text_tab_skips_tab_lines():
    text = "e|--0--1--2--|\nB|--3--2--0--|\n"
    sections = parse_text_tab(text, style="bracketed")
    assert sections == []


def test_parse_text_tab_multiple_sections():
    text = "[Verse 1]\n[D]\nLine one\n[Chorus]\n[G]\nLine two\n"
    sections = parse_text_tab(text, style="bracketed")
    assert len(sections) == 2
    assert sections[0].label == "Verse 1"
    assert sections[1].label == "Chorus"


def test_parse_text_tab_lyric_without_chord_emitted_as_is():
    text = "[Verse 1]\nJust some lyrics\n"
    sections = parse_text_tab(text, style="bracketed")
    assert sections[0].lines[0].content == "Just some lyrics"


def test_parse_text_tab_blank_lines_skipped():
    text = "\n\n[D]\nLyric\n\n\n"
    sections = parse_text_tab(text, style="bracketed")
    assert len(sections) == 1
    assert len(sections[0].lines) == 1
