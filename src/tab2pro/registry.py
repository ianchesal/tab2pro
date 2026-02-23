from .adapters.base import SiteAdapter
from .adapters.ultimate_guitar import UltimateGuitarAdapter
from .adapters.rukind import RukindAdapter
from .adapters.dylanchords import DylanchordsAdapter
from .exceptions import UnsupportedSiteError

_ADAPTERS: list[type[SiteAdapter]] = [
    UltimateGuitarAdapter,
    RukindAdapter,
    DylanchordsAdapter,
]


def get_adapter(url: str) -> SiteAdapter:
    """Return an instantiated adapter for the given URL.

    Raises UnsupportedSiteError if no adapter matches.
    """
    for cls in _ADAPTERS:
        if cls.can_handle(url):
            return cls()
    raise UnsupportedSiteError(url)
