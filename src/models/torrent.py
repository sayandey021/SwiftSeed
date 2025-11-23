"""Torrent data model."""

from dataclasses import dataclass
from typing import Optional
from models.category import Category


# List of trackers to use in magnet links
TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://tracker.openbittorrent.com:6969/announce",
    "udp://exodus.desync.com:6969/announce",
    "udp://open.demonii.com:1337/announce",
    "udp://tracker.tiny-vps.com:6969/announce",
    "udp://tracker.moeking.me:6969/announce",
    "udp://ipv4.tracker.harry.lu:80/announce",
    "udp://explodie.org:6969/announce",
]


@dataclass
class Torrent:
    """Represents a torrent result."""
    
    name: str
    size: str
    seeders: int
    peers: int
    provider_id: str
    provider_name: str
    upload_date: str
    description_url: str
    magnet_uri: Optional[str] = None
    info_hash: Optional[str] = None
    category: Optional[Category] = None
    bookmarked: bool = False
    
    def get_magnet_uri(self) -> str:
        """Get the magnet URI for this torrent."""
        if self.magnet_uri:
            return self.magnet_uri
        
        if self.info_hash:
            # Build magnet URI from info hash
            trackers_str = "&tr=".join(TRACKERS)
            return f"magnet:?xt=urn:btih:{self.info_hash}&tr={trackers_str}"
        
        return ""
    
    def is_nsfw(self) -> bool:
        """Check if torrent is NSFW."""
        if self.category:
            return self.category.is_nsfw
        return True  # Default to NSFW if category unknown
    
    def is_dead(self) -> bool:
        """Check if torrent is dead (no seeders or peers)."""
        return self.seeders == 0 and self.peers == 0
    
    def __str__(self):
        return f"{self.name} ({self.size}) - {self.seeders}S/{self.peers}P"
