"""TorrentsCSV search provider."""

from typing import List
from models.torrent import Torrent
from models.category import Category
from providers.base import SearchProvider, SearchProviderInfo, SearchProviderSafetyStatus


class TorrentsCSVProvider(SearchProvider):
    """TorrentsCSV.com API search provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="torrentscsv",
            name="TorrentsCSV",
            url="https://torrents-csv.com",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search TorrentsCSV for torrents."""
        url = f"https://torrents-csv.com/service/search?q={query}"
        
        try:
            data = self._get_json(url)
            
            if not isinstance(data, dict):
                return []
            
            torrents_data = data.get('torrents', [])
            
            torrents = []
            for item in torrents_data:
                torrent = self._parse_torrent(item)
                if torrent:
                    torrents.append(torrent)
            
            return torrents
        except Exception as e:
            print(f"TorrentsCSV search error: {e}")
            return []
    
    def _parse_torrent(self, data: dict) -> Torrent:
        """Parse torrent data from API response."""
        try:
            name = data.get('name', '')
            if not name:
                return None
            
            info_hash = data.get('infohash', '')
            if not info_hash:
                return None
            
            # Parse size
            size_bytes = int(data.get('size_bytes', 0))
            size = self._format_size(size_bytes)
            
            # Parse seeders and peers
            seeders = int(data.get('seeders', 0))
            peers = int(data.get('leechers', 0))
            
            # Upload date
            upload_date = data.get('created_unix', 'Unknown')
            if upload_date != 'Unknown':
                upload_date = self._format_date(int(upload_date))
            
            # TorrentsCSV doesn't provide category
            description_url = f"{self.info.url}/#/search/{name}"
            
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
                category=None,  # TorrentsCSV doesn't provide categories
            )
        except Exception as e:
            print(f"Error parsing TorrentsCSV torrent: {e}")
            return None
    
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
            from datetime import datetime
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d')
        except:
            return 'Unknown'
