"""Search providers for torrent sources."""

from .base import SearchProvider, SearchProviderInfo, SearchProviderSafetyStatus
from .thepiratebay import ThePirateBayProvider
from .nyaa import NyaaProvider
from .leet import LeetProvider
from .torrents_csv import TorrentsCSVProvider
from .yts import YtsProvider
from .eztv import EztvProvider
from .additional import (
    AnimeToshoProvider,
    KnabenProvider,
    LimeTorrentsProvider,
    MyPornClubProvider,
    SukebeiProvider,
    TheRarBgProvider,
    TokyoToshokanProvider,
    TorrentDownloadsProvider,
    UlndexProvider,
    XXXClubProvider,
)

__all__ = [
    'SearchProvider',
    'SearchProviderInfo',
    'SearchProviderSafetyStatus',
    'ThePirateBayProvider',
    'NyaaProvider',
    'LeetProvider',
    'TorrentsCSVProvider',
    'YtsProvider',
    'EztvProvider',
]


def get_all_providers():
    """Get all available search providers."""
    return [
        # Working providers (enabled by default)
        LeetProvider(),  # 1337x
        NyaaProvider(),  # Anime
        TorrentsCSVProvider(),  # All
        YtsProvider(),  # Movies
        EztvProvider(),  # TV Series
        
        # Additional providers (disabled by default, some need implementation)
        ThePirateBayProvider(),  # All - Unsafe
        AnimeToshoProvider(),  # Anime
        KnabenProvider(),  # All
        LimeTorrentsProvider(),  # All - Unsafe
        MyPornClubProvider(),  # Porn
        SukebeiProvider(),  # Porn
        TheRarBgProvider(),  # All - Unsafe
        TokyoToshokanProvider(),  # Anime
        TorrentDownloadsProvider(),  # All
        UlndexProvider(),  # All
        XXXClubProvider(),  # Porn
    ]
