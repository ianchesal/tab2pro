import click


@click.command()
@click.argument("url")
@click.option("-o", "--output", "output_path", default=None, metavar="PATH",
              help="Output file path (default: <artist>-<title>.cho)")
@click.option("--stdout", is_flag=True, default=False,
              help="Print to stdout instead of writing a file.")
@click.option("--browser", is_flag=True, default=False,
              help="Use Playwright headless browser (fallback for 403s).")
@click.option("--version", "song_version", default=1, show_default=True,
              help="For sites with multiple song versions, pick version N.")
def main(url: str, output_path: str | None, stdout: bool, browser: bool, song_version: int) -> None:
    """Convert a chord tab page to ChordPro format.

    \b
    Supported sites:
      - tabs.ultimate-guitar.com
      - rukind.com
      - dylanchords.com
    """
    raise NotImplementedError("CLI not yet implemented")
