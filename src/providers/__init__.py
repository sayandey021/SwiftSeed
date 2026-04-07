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
    MyPornClubProvider,
    SukebeiProvider,
    TokyoToshokanProvider,
    IDopeProvider,
    BlueRomsProvider,
    LinuxTrackerProvider,
    PluginTorrentProvider,
    VSTTorrentzProvider,
    VSTorrentProvider,
    XXXClubProvider,
    YouplexTorrentsProvider,
    RarbgDumpProvider,
    SnowflProvider,
    ExtraTorrentProvider,
    LeetxProvider,
    # New providers
    TorLockProvider,
    GloTorrentsProvider,
    TorrentDownloadsProvider,
    ZooqleProvider,
    Torrentz2Provider,
    LimeTorrentsProvider2,
    RuTrackerProvider,
    TorrentFunkProvider,
    DemonoidProvider,
    MagnetDLProvider,
    YifyProvider,
    # Legal providers (working with XML API!)
    AcademicTorrentsProvider,
    # KickAss Torrents
    KickAssTorrentsProvider,
    # Russian / New requested
    NNMClubProvider,
    KinozalProvider,
    # Games
    ByRutorProvider,
    FitGirlProvider,
    # Adult
    ZeroMagnetProvider,
    ApacheTorrentProvider,
    AnirenaProvider,
    ACGRipProvider,
    BigFanGroupProvider,
    CpasbienProvider,
    CrackingPatchingProvider,
    EHentaiProvider,
    TorrentMacProvider,
    FreeJavTorrentProvider,
    PiratesParadiseProvider,
    MagnetCatProvider,
    GamesTorrentsProvider,
    SkidrowRepackProvider,
    FTUAppsProvider,
    CroTorrentsProvider,
    PlazaPCGamesProvider,
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
        # === WORKING PROVIDERS (enabled by default) ===
        TorrentsCSVProvider(),  # All - API-based, safe (Verified Working)
        ThePirateBayProvider(),  # All - API-based, works
        KnabenProvider(),  # All - Best aggregator
        RarbgDumpProvider(),  # All - RARBG Archive
        AcademicTorrentsProvider(),  # Legal - Academic content (XML API)
        AnimeToshoProvider(),  # Anime - Working
        TokyoToshokanProvider(),  # Anime - Working
        AnirenaProvider(),  # Anime - Anirena
        ACGRipProvider(),  # Anime - ACG.RIP
        BigFanGroupProvider(),  # Anime - BigFanGroup (Russian)
        NNMClubProvider(),  # Russian - Verified accessible
        CpasbienProvider(),  # French - Movies, Series, Music
        PiratesParadiseProvider(),  # Movies & TV - Clean site, no ads
        MagnetCatProvider(),  # General - Magnet search engine
        
        # === GENERAL TORRENT SITES (disabled by default) ===
        KickAssTorrentsProvider(),  # KickAss - Working via kickass.cm
        LeetxProvider(),  # 1337x - Often blocked
        ExtraTorrentProvider(),  # ExtraTorrent - Often blocked
        TorLockProvider(),  # TorLock - Verified torrents
        GloTorrentsProvider(),  # GloTorrents - Has ads
        TorrentDownloadsProvider(),  # TorrentDownloads - May be blocked
        ZooqleProvider(),  # Zooqle - Often down
        Torrentz2Provider(),  # Torrentz2 - Meta-search
        LimeTorrentsProvider2(),  # LimeTorrents - Has popups
        TorrentFunkProvider(),  # TorrentFunk
        DemonoidProvider(),  # Demonoid - Classic
        MagnetDLProvider(),  # MagnetDL - Direct magnets
        KinozalProvider(),  # Kinozal - Russian Movies

        
        # === REQUIRES JS / BLOCKED ===
        SnowflProvider(),  # Snowfl - Requires JS
        RuTrackerProvider(),  # RuTracker - Requires login
        # YouplexTorrentsProvider(),  # Requires JavaScript
        # IDopeProvider(), # Blocked in many regions
        
        # === MOVIES ===
        YifyProvider(),  # YIFY/YTS - Movies API
        ApacheTorrentProvider(),  # Apache Torrent - Movies/Series
        
        # === ANIME ===
        NyaaProvider(),  # Anime - Best for anime
        # AnimeToshoProvider(),  # Moved to working
        # TokyoToshokanProvider(),  # Moved to working
        
        # === TV SERIES ===
        EztvProvider(),  # TV Series

        # === GAMES ===
        FitGirlProvider(),  # Games - FitGirl Repacks (Very Popular)
        ByRutorProvider(),  # Games - Russian repacks
        BlueRomsProvider(), # Gaming/ROMs
        LinuxTrackerProvider(), # Linux ISOs
        PluginTorrentProvider(), # Audio Plugins
        VSTTorrentzProvider(), # Audio Plugins
        VSTorrentProvider(), # Audio Plugins
        CrackingPatchingProvider(),  # Software - Cracks (disabled by default)
        TorrentMacProvider(),  # Mac Software - Cracked apps (disabled by default)
        GamesTorrentsProvider(),  # Games - Spanish (PC, PS3, Xbox, etc)
        SkidrowRepackProvider(),  # Games - PC Repacks (English)
        CroTorrentsProvider(),  # Games - PC game torrents (CroTorrents)
        PlazaPCGamesProvider(),  # Games - PLAZA PC game releases
        FTUAppsProvider(),  # Apps - Multilingual pre-activated software
        # === ADULT (at the bottom) ===
        ZeroMagnetProvider(),  # Porn - 0Magnet (13mag.net)
        MyPornClubProvider(),  # Porn
        SukebeiProvider(),  # Porn
        XXXClubProvider(),  # Porn
        EHentaiProvider(),  # Porn - Hentai
        FreeJavTorrentProvider(),  # Porn - JAV
    ]
