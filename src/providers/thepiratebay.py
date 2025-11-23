"""ThePirateBay search provider."""

from typing import List
from datetime import datetime
from models.torrent import Torrent
from models.category import Category
from providers.base import SearchProvider, SearchProviderInfo, SearchProviderSafetyStatus


class ThePirateBayProvider(SearchProvider):
    """ThePirateBay torrent search provider using apibay.org API."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="thepiratebay",
            name="ThePirateBay",
            url="https://thepiratebay.org",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.UNSAFE,
            safety_reason="Many malware reports due to inadequate moderation",
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search ThePirateBay for torrents."""
        cat_index = self._get_category_index(category)
        url = f"https://apibay.org/q.php?q={query}&cat={cat_index}"
        
        try:
            data = self._get_json(url)
            
            if not isinstance(data, list):
                return []
            
            torrents = []
            for item in data:
                torrent = self._parse_torrent(item)
                if torrent:
                    torrents.append(torrent)
            
            return torrents
        except Exception as e:
            print(f"ThePirateBay search error: {e}")
            return []
    
    def _parse_torrent(self, data: dict) -> Torrent:
        """Parse torrent data from API response."""
        try:
            name = data.get('name', '')
            
            # API returns "No results returned" as a torrent name
            if name == "No results returned":
                return None
            
            info_hash = data.get('info_hash', '')
            if not info_hash:
                return None
            
            # Parse size
            size_bytes = int(data.get('size', 0))
            size = self._format_size(size_bytes)
            
            # Parse seeders and peers
            seeders = int(data.get('seeders', 0))
            peers = int(data.get('leechers', 0))
            
            # Parse upload date
            upload_timestamp = int(data.get('added', 0))
            upload_date = self._format_date(upload_timestamp)
            
            # Parse category
            cat_index = int(data.get('category', 0))
            torrent_category = self._get_category_from_index(cat_index)
            
            # Build description URL
            torrent_id = data.get('id', '')
            description_url = f"{self.info.url}/description.php?id={torrent_id}"
            
            return Torrent(
                name=name,
                size=size,
                seeders=seeders,
                peers=peers,
                provider_id=self.info.id,
                provider_name=self.info.name,
                upload_date=upload_date,
                description_url=description_url,
                info_hash=info_hash,
                category=torrent_category,
            )
        except Exception as e:
            print(f"Error parsing torrent: {e}")
            return None
    
    def _get_category_index(self, category: Category) -> int:
        """Get ThePirateBay category index."""
        mapping = {
            Category.ALL: 0,
            Category.ANIME: 0,
            Category.APPS: 300,
            Category.BOOKS: 601,
            Category.GAMES: 400,
            Category.MOVIES: 200,
            Category.SERIES: 200,
            Category.MUSIC: 101,
            Category.PORN: 500,
            Category.OTHER: 600,
        }
        return mapping.get(category, 0)
    
    def _get_category_from_index(self, index: int) -> Category:
        """Get category from ThePirateBay index."""
        if 300 <= index <= 399:
            return Category.APPS
        elif index == 601:
            return Category.BOOKS
        elif 400 <= index <= 499:
            return Category.GAMES
        elif index in [201, 202, 204, 207, 209, 210, 211]:
            return Category.MOVIES
        elif 100 <= index <= 199:
            return Category.MUSIC
        elif 500 <= index <= 599:
            return Category.PORN
        elif index in [205, 208, 212]:
            return Category.SERIES
        else:
            return Category.OTHER
    
    def _format_size(self, bytes_size: int) -> str:
        """Format size in bytes to human readable."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} PB"
    
    def _format_date(self, timestamp: int) -> str:
        """Format Unix timestamp to date string."""
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d')
        except:
            return 'Unknown'
