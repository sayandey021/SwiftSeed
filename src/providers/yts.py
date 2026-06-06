"""Yts search provider."""

from typing import List
from models.torrent import Torrent
from models.category import Category
from providers.base import SearchProvider, SearchProviderInfo, SearchProviderSafetyStatus


class YtsProvider(SearchProvider):
    """YTS torrent search provider (specializes in Movies)."""
    
    # Try multiple API endpoints
    API_ENDPOINTS = [
        "https://yts.rs/api/v2/list_movies.json",
        "https://yts.mx/api/v2/list_movies.json",
        "https://yts.cool/api/v2/list_movies.json",
        "https://yts.torrentbay.st/api/v2/list_movies.json",
        "https://yts.do/api/v2/list_movies.json",
    ]
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="yts",
            name="YTS",
            url="https://yts.rs",
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
                data = self._get_json(url, timeout=3)
                if data and 'data' in data and data['data'].get('movies'):
                    break
            except:
                continue
        
        movies = []
        if data and 'data' in data and data['data'].get('movies'):
            movies = data['data']['movies']
        else:
            # Fallback to scraping yts.rs HTML if APIs are dead/blocked
            import urllib.parse
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://yts.rs/browse-movies/{encoded_query}/all/all/0/latest/0/all"
            try:
                html = self._get(search_url)
                if html:
                    import re, json
                    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html)
                    if m:
                        next_data = json.loads(m.group(1))
                        movies = next_data.get('props', {}).get('pageProps', {}).get('movies', []) or []
            except Exception as e:
                print(f"Error scraping yts.rs HTML: {e}")
                
        if not movies:
            return []
            
        torrents = []
        
        for movie in movies:
            # YTS provides multiple torrents per movie (different qualities)
            movie_torrents = movie.get('torrents', [])
            
            for torrent in movie_torrents:
                name = f"{movie.get('title', 'Unknown')} ({movie.get('year', 'Unknown')}) [{torrent.get('quality', 'Unknown')}]"
                
                # Construct magnet URI from hash
                hash_val = torrent.get('hash', '')
                magnet_uri = ''
                if hash_val:
                    import urllib.parse
                    encoded_title = urllib.parse.quote(movie.get('title', ''))
                    magnet_uri = f"magnet:?xt=urn:btih:{hash_val}&dn={encoded_title}"
                
                t = Torrent(
                    name=name,
                    size=torrent.get('size', 'Unknown'),
                    seeders=torrent.get('seeds', 0),
                    peers=torrent.get('peers', 0),
                    provider_id=self.info.id,
                    provider_name=self.info.name,
                    upload_date=movie.get('date_uploaded', 'Unknown'),
                    description_url=movie.get('url', self.info.url).replace('yts.mx', 'yts.rs'),
                    magnet_uri=magnet_uri,
                    category=Category.MOVIES,
                )
                torrents.append(t)
        
        return torrents
