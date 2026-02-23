from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from tab2pro.cli import _slugify, main
from tab2pro.exceptions import FetchError, ParseError, UnsupportedSiteError
from tab2pro.models import Line, Section, Song

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_song(title="Dark Star", artist="Grateful Dead") -> Song:
    return Song(
        title=title,
        artist=artist,
        sections=[Section(label="Verse 1", lines=[Line(content="[A]Dark star [G]crashes")])],
    )


def _mock_adapter(song=None) -> MagicMock:
    adapter = MagicMock()
    adapter.scrape.return_value = song or _make_song()
    return adapter


# ---------------------------------------------------------------------------
# _slugify
# ---------------------------------------------------------------------------


def test_slugify_basic():
    assert _slugify("The Weight") == "the-weight"
    assert _slugify("Grateful Dead") == "grateful-dead"


def test_slugify_apostrophe():
    assert _slugify("Blowin' in the Wind") == "blowin-in-the-wind"


def test_slugify_collapses_spaces():
    assert _slugify("A  B") == "a-b"


def test_slugify_already_clean():
    assert _slugify("dark-star") == "dark-star"


# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------


def test_help_output():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Convert a chord tab page" in result.output
    assert "tabs.ultimate-guitar.com" in result.output


# ---------------------------------------------------------------------------
# --stdout
# ---------------------------------------------------------------------------


def test_stdout_flag_prints_chordpro():
    with patch("tab2pro.cli.get_adapter", return_value=_mock_adapter()):
        result = CliRunner().invoke(
            main,
            ["--stdout", "http://www.rukind.com/gdpedia/titles/tab/dark-star"],
        )
    assert result.exit_code == 0
    assert "{title: Dark Star}" in result.output
    assert "{artist: Grateful Dead}" in result.output


def test_stdout_flag_does_not_write_file(tmp_path):
    with patch("tab2pro.cli.get_adapter", return_value=_mock_adapter()):
        with CliRunner().isolated_filesystem(temp_dir=tmp_path):
            result = CliRunner().invoke(
                main,
                ["--stdout", "http://www.rukind.com/gdpedia/titles/tab/dark-star"],
            )
    assert result.exit_code == 0
    assert not any(tmp_path.glob("*.cho"))


# ---------------------------------------------------------------------------
# File output
# ---------------------------------------------------------------------------


def test_output_file_written_with_flag(tmp_path):
    out_file = tmp_path / "song.cho"
    with patch("tab2pro.cli.get_adapter", return_value=_mock_adapter()):
        result = CliRunner().invoke(
            main,
            ["-o", str(out_file), "http://www.rukind.com/gdpedia/titles/tab/dark-star"],
        )
    assert result.exit_code == 0
    assert out_file.exists()
    assert "{title: Dark Star}" in out_file.read_text()


def test_default_filename_derived_from_artist_and_title(tmp_path):
    with patch("tab2pro.cli.get_adapter", return_value=_mock_adapter()):
        with CliRunner().isolated_filesystem(temp_dir=tmp_path):
            result = CliRunner().invoke(
                main, ["http://www.rukind.com/gdpedia/titles/tab/dark-star"]
            )
    assert result.exit_code == 0
    assert "grateful-dead-dark-star.cho" in result.output


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_unsupported_site_exits_nonzero():
    with patch(
        "tab2pro.cli.get_adapter",
        side_effect=UnsupportedSiteError("https://nosite.com/song"),
    ):
        result = CliRunner().invoke(main, ["--stdout", "https://nosite.com/song"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_fetch_error_exits_nonzero():
    adapter = MagicMock()
    adapter.scrape.side_effect = FetchError("http://example.com", 404)
    with patch("tab2pro.cli.get_adapter", return_value=adapter):
        result = CliRunner().invoke(
            main, ["--stdout", "http://www.rukind.com/gdpedia/titles/tab/dark-star"]
        )
    assert result.exit_code != 0
    assert "404" in result.output


def test_fetch_error_403_suggests_browser_flag():
    adapter = MagicMock()
    adapter.scrape.side_effect = FetchError("http://example.com", 403)
    with patch("tab2pro.cli.get_adapter", return_value=adapter):
        result = CliRunner().invoke(main, ["--stdout", "http://example.com"])
    assert result.exit_code != 0
    assert "--browser" in result.output


def test_parse_error_exits_nonzero():
    adapter = MagicMock()
    adapter.scrape.side_effect = ParseError("http://example.com", "bad html")
    with patch("tab2pro.cli.get_adapter", return_value=adapter):
        result = CliRunner().invoke(
            main, ["--stdout", "http://www.rukind.com/gdpedia/titles/tab/dark-star"]
        )
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# --version flag
# ---------------------------------------------------------------------------


def test_version_flag_sets_adapter_version():
    adapter = MagicMock()
    adapter.scrape.return_value = _make_song()
    adapter.version = 1  # attribute exists so hasattr() returns True
    with patch("tab2pro.cli.get_adapter", return_value=adapter):
        CliRunner().invoke(
            main,
            ["--stdout", "--version", "2", "http://www.dylanchords.com/song"],
        )
    assert adapter.version == 2


def test_version_flag_not_applied_to_adapters_without_version():
    # Adapters without a 'version' attribute are not touched
    adapter = MagicMock(spec=["scrape"])  # only 'scrape', no 'version'
    adapter.scrape.return_value = _make_song()
    with patch("tab2pro.cli.get_adapter", return_value=adapter):
        result = CliRunner().invoke(
            main,
            ["--stdout", "--version", "3", "http://www.rukind.com/gdpedia/titles/tab/dark-star"],
        )
    # Should not raise — just ignored
    assert result.exit_code == 0
