"""Yts search provider."""

from typing import List
from models.torrent import Torrent
from models.category import Category
from providers.base import SearchProvider, SearchProviderInfo, SearchProviderSafetyStatus


class YtsProvider(SearchProvider):
    """YTS torrent search provider (specializes in Movies)."""
    
    # Try multiple API endpoints
    API_ENDPOINTS = [
        "https://yts.mx/api/v2/list_movies.json",
        "https://yts.torrentbay.st/api/v2/list_movies.json",
        "https://yts.rs/api/v2/list_movies.json",
    ]
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="yts",
            name="Yts",
            url="https://yts.mx",
            specialized_category=Category.MOVIES,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
            language="English",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search YTS for torrents."""
        
        data = None
        for api_base in self.API_ENDPOINTS:
            url = f"{api_base}?query_term={query}&limit=50"
            try:
                data = self._get_json(url)
                if data and 'data' in data and data['data'].get('movies'):
                    break
            except:
                continue
        
        if not data or 'data' not in data or not data['data'].get('movies'):
            return []
        
        torrents = []
        movies = data['data']['movies'] or []
        
        for movie in movies:
            # YTS provides multiple torrents per movie (different qualities)
            movie_torrents = movie.get('torrents', [])
            
            for torrent in movie_torrents:
                name = f"{movie.get('title', 'Unknown')} ({movie.get('year', 'Unknown')}) [{torrent.get('quality', 'Unknown')}]"
                
                # Construct magnet URI from hash
                hash_val = torrent.get('hash', '')
                magnet_uri = ''
                if hash_val:
                    magnet_uri = f"magnet:?xt=urn:btih:{hash_val}&dn={movie.get('title', '')}"
                
                t = Torrent(
                    name=name,
                    size=torrent.get('size', 'Unknown'),
                    seeders=torrent.get('seeds', 0),
                    peers=torrent.get('peers', 0),
                    provider_id=self.info.id,
                    provider_name=self.info.name,
                    upload_date=movie.get('date_uploaded', 'Unknown'),
                    description_url=movie.get('url', self.info.url),
                    magnet_uri=magnet_uri,
                    category=Category.MOVIES,
                )
                torrents.append(t)
        
        return torrents
