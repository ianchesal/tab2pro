class Tab2ProError(Exception):
    """Base exception for tab2pro."""


class FetchError(Tab2ProError):
    """Raised when an HTTP request fails."""

    def __init__(self, url: str, status_code: int):
        self.url = url
        self.status_code = status_code
        super().__init__(f"HTTP {status_code} fetching {url}")


class ParseError(Tab2ProError):
    """Raised when expected content cannot be extracted from a page."""

    def __init__(self, url: str, reason: str):
        self.url = url
        self.reason = reason
        super().__init__(f"Parse error for {url}: {reason}")


class UnsupportedSiteError(Tab2ProError):
    """Raised when no adapter matches the given URL."""

    def __init__(self, url: str):
        self.url = url
        super().__init__(f"No adapter found for URL: {url}")
