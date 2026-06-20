"""SubsPlease search provider.

SubsPlease is a fansub group that releases weekly simulcast anime in
480p, 720p, and 1080p. They provide a public JSON search API at:
  https://subsplease.org/api/?f=search&tz=UTC&s={query}

The search is a "snowflake"-style partial match on show titles.
Each search result entry contains:
  - show:      Full show name
  - episode:   Episode number
  - time:      Air date (MM/DD/YY)
  - downloads: List of {res, magnet} dicts (one per resolution)
  - page:      URL slug for the show page

We expand each (episode × resolution) into its own Torrent row so the
user can choose the quality they want.
"""

import urllib.parse
from datetime import datetime
from typing import List

from models.category import Category
from models.torrent import Torrent
from providers.base import SearchProvider, SearchProviderInfo, SearchProviderSafetyStatus


class SubsPleaseProvider(SearchProvider):
    """SubsPlease fansub – weekly simulcast anime at 480p / 720p / 1080p."""

    BASE_URL = "https://subsplease.org"
    API_URL = f"{BASE_URL}/api/"

    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="subsplease",
            name="SubsPlease",
            url=self.BASE_URL,
            specialized_category=Category.ANIME,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
            language="English",
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search(self, query: str, category: Category, page: int = 1) -> List[Torrent]:
        """Search SubsPlease for anime episodes."""
        params = urllib.parse.urlencode({"f": "search", "tz": "UTC", "s": query})
        url = f"{self.API_URL}?{params}"

        try:
            data = self._get_json(url)
        except Exception as exc:
            print(f"SubsPlease search error: {exc}")
            return []

        if not data:
            return []

        torrents: List[Torrent] = []
        for _episode_key, entry in data.items():
            try:
                for torrent in self._parse_entry(entry):
                    torrents.append(torrent)
            except Exception as exc:
                print(f"SubsPlease parse error for entry: {exc}")
                continue

        return torrents

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_entry(self, entry: dict) -> List[Torrent]:
        """Convert one API entry (one episode) into a list of Torrents.

        Each download resolution (480p / 720p / 1080p) becomes its own
        Torrent so the user can pick the quality they prefer.
        """
        show: str = entry.get("show", "Unknown")
        episode: str = entry.get("episode", "?")
        time_str: str = entry.get("time", "")
        page_slug: str = entry.get("page", "")
        downloads: list = entry.get("downloads", [])

        upload_date = self._parse_date(time_str)
        description_url = (
            f"{self.BASE_URL}/shows/{page_slug}/" if page_slug else self.BASE_URL
        )

        torrents = []
        for dl in downloads:
            res: str = dl.get("res", "?")
            magnet: str = dl.get("magnet", "")

            if not magnet:
                continue

            # Build human-readable title: "[SubsPlease] Show Name - Ep (Res)"
            name = f"[SubsPlease] {show} - {episode} ({res}p)"

            # Derive file size from the xl= parameter in the magnet URI
            size = self._size_from_magnet(magnet)

            torrents.append(
                Torrent(
                    name=name,
                    size=size,
                    # SubsPlease API does not expose seeder/peer counts.
                    # Use -1 so the UI shows "N/A" instead of treating the
                    # torrent as dead (0 seeders).
                    seeders=-1,
                    peers=-1,
                    provider_id=self.info.id,
                    provider_name=self.info.name,
                    upload_date=upload_date,
                    description_url=description_url,
                    magnet_uri=magnet,
                    category=Category.ANIME,
                )
            )

        return torrents

    @staticmethod
    def _parse_date(time_str: str) -> str:
        """Parse SubsPlease date format 'MM/DD/YY' → 'YYYY-MM-DD'."""
        if not time_str:
            return "Unknown"
        try:
            dt = datetime.strptime(time_str, "%m/%d/%y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return time_str

    @staticmethod
    def _size_from_magnet(magnet: str) -> str:
        """Extract and format the xl= (exact length in bytes) from a magnet URI."""
        try:
            parsed = urllib.parse.urlparse(magnet)
            qs = urllib.parse.parse_qs(parsed.query)
            xl_values = qs.get("xl")
            if xl_values:
                size_bytes = int(xl_values[0])
                return _format_bytes(size_bytes)
        except Exception:
            pass
        return "Unknown"


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _format_bytes(num: int) -> str:
    """Convert bytes to a human-readable size string."""
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(num) < 1024.0:
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PiB"
