"""EZTV search provider using the JSON API."""

import re
from datetime import datetime
from typing import List
from models.torrent import Torrent
from models.category import Category
from providers.base import SearchProvider, SearchProviderInfo, SearchProviderSafetyStatus


class EztvProvider(SearchProvider):
    """EZTV torrent search provider (specializes in TV Series).
    
    Uses the EZTV JSON API at /api/get-torrents since the HTML pages
    are behind Cloudflare protection.
    """
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="eztv",
            name="Eztv",
            url="https://eztv1.xyz",
            specialized_category=Category.TV,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
            language="English",
        )
    
    def search(self, query: str, category: Category, page: int = 1) -> List[Torrent]:
        """Search EZTV for torrents using the JSON API.
        
        The API doesn't support text search directly, so we fetch
        multiple pages and filter results client-side by query terms.
        """
        query_terms = query.lower().split()
        if not query_terms:
            return []
        
        torrents = []
        # Fetch multiple API pages and filter client-side
        # Each API page has up to 100 results; scan enough to find matches
        max_api_pages = 15
        results_per_page = 100
        
        for api_page in range(1, max_api_pages + 1):
            url = f"{self.info.url}/api/get-torrents?limit={results_per_page}&page={api_page}"
            
            try:
                data = self._get_json(url)
                if not data:
                    break
                
                api_torrents = data.get('torrents', [])
                if not api_torrents:
                    break
                
                for t_data in api_torrents:
                    title = t_data.get('title', '')
                    if not title:
                        continue
                    
                    # Client-side filter: all query terms must appear in the title
                    title_lower = title.lower()
                    if not all(term in title_lower for term in query_terms):
                        continue
                    
                    # Extract magnet
                    magnet_uri = t_data.get('magnet_url', '')
                    if not magnet_uri:
                        # Construct from hash if available
                        info_hash = t_data.get('hash', '')
                        if info_hash:
                            magnet_uri = f"magnet:?xt=urn:btih:{info_hash}&dn={title}"
                    
                    if not magnet_uri:
                        continue
                    
                    # Size
                    try:
                        size_bytes = int(t_data.get('size_bytes', 0) or 0)
                    except (ValueError, TypeError):
                        size_bytes = 0
                    size = self._format_size(size_bytes) if size_bytes else 'Unknown'
                    
                    # Seeds / Peers
                    try:
                        seeds = int(t_data.get('seeds', 0) or 0)
                    except (ValueError, TypeError):
                        seeds = 0
                    try:
                        peers = int(t_data.get('peers', 0) or 0)
                    except (ValueError, TypeError):
                        peers = 0
                    
                    # Date
                    date_unix = t_data.get('date_released_unix', 0)
                    upload_date = 'Unknown'
                    if date_unix:
                        try:
                            upload_date = datetime.fromtimestamp(int(date_unix)).strftime('%Y-%m-%d')
                        except (ValueError, OSError):
                            pass
                    
                    # Description URL
                    torrent_id = t_data.get('id', '')
                    desc_url = f"{self.info.url}/ep/{torrent_id}" if torrent_id else self.info.url
                    
                    torrent = Torrent(
                        name=title,
                        size=size,
                        seeders=seeds,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date=upload_date,
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.TV,
                    )
                    torrents.append(torrent)
                
                # Stop early if we already have enough results
                if len(torrents) >= 40:
                    break
                    
                # Stop if this was the last page of results
                total = data.get('torrents_count', 0)
                if api_page * results_per_page >= total:
                    break
                    
            except Exception as e:
                print(f"EZTV API page {api_page} error: {e}")
                break
        
        return torrents
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes into human-readable size string."""
        if size_bytes <= 0:
            return 'Unknown'
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        for unit in units:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"
