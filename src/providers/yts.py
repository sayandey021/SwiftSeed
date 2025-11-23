"""Yts search provider."""

from typing import List
from models.torrent import Torrent
from models.category import Category
from providers.base import SearchProvider, SearchProviderInfo, SearchProviderSafetyStatus


class YtsProvider(SearchProvider):
    """YTS torrent search provider (specializes in Movies)."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="yts",
            name="Yts",
            url="https://yts.mx",
            specialized_category=Category.MOVIES,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search YTS for torrents."""
        url = f"{self.info.url}/api/v2/list_movies.json?query_term={query}&limit=50"
        
        try:
            data = self._get_json(url)
            
            if not data or 'data' not in data or 'movies' not in data['data']:
                return []
            
            torrents = []
            movies = data['data']['movies'] or []
            
            for movie in movies:
                # YTS provides multiple torrents per movie (different qualities)
                movie_torrents = movie.get('torrents', [])
                
                for torrent in movie_torrents:
                    name = f"{movie.get('title', 'Unknown')} ({movie.get('year', 'Unknown')}) [{torrent.get('quality', 'Unknown')}]"
                    
                    t = Torrent(
                        name=name,
                        size=torrent.get('size', 'Unknown'),
                        seeders=torrent.get('seeds', 0),
                        peers=torrent.get('peers', 0),
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date=movie.get('date_uploaded', 'Unknown'),
                        description_url=movie.get('url', self.info.url),
                        magnet_uri=torrent.get('url', ''),
                        category=Category.MOVIES,
                    )
                    torrents.append(t)
            
            return torrents
        except Exception as e:
            print(f"YTS search error: {e}")
            return []
