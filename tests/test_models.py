from tab2pro.models import Line, Section, Song


def test_line_stores_content():
    line = Line(content="[D]pulled into Nazareth")
    assert line.content == "[D]pulled into Nazareth"


def test_section_defaults():
    section = Section(label="Verse 1")
    assert section.label == "Verse 1"
    assert section.lines == []


def test_section_none_label():
    section = Section(label=None)
    assert section.label is None


def test_song_defaults():
    song = Song(title="The Weight", artist="The Band")
    assert song.key is None
    assert song.capo is None
    assert song.tuning is None
    assert song.sections == []
    assert song.source_url == ""


def test_song_all_fields():
    song = Song(
        title="The Weight",
        artist="The Band",
        key="D",
        capo=2,
        tuning="Drop D",
        source_url="https://example.com",
    )
    assert song.key == "D"
    assert song.capo == 2
    assert song.tuning == "Drop D"
    assert song.source_url == "https://example.com"
