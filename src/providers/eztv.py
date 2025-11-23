"""EZTV search provider."""

from typing import List
from bs4 import BeautifulSoup
from models.torrent import Torrent
from models.category import Category
from providers.base import SearchProvider, SearchProviderInfo, SearchProviderSafetyStatus


class EztvProvider(SearchProvider):
    """EZTV torrent search provider (specializes in TV Series)."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="eztv",
            name="Eztv",
            url="https://eztvx.to",
            specialized_category=Category.TV,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search EZTV for torrents."""
        url = f"{self.info.url}/search/{query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('tr.forum_header_border')
            
            torrents = []
            for row in rows:
                try:
                    name_cell = row.select_one('td.forum_thread_post a.epinfo')
                    if not name_cell:
                        continue
                    
                    name = name_cell.get_text(strip=True)
                    desc_url = self.info.url + name_cell.get('href', '')
                    
                    magnet_link = row.select_one('a.magnet')
                    magnet_uri = magnet_link.get('href', '') if magnet_link else ''
                    
                    size_cell = row.select_one('td:nth-child(4)')
                    size = size_cell.get_text(strip=True) if size_cell else 'Unknown'
                    
                    seeds_cell = row.select_one('td.forum_thread_post font[color="green"]')
                    seeds = int(seeds_cell.get_text(strip=True)) if seeds_cell else 0
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeds,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.TV,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"EZTV search error: {e}")
            return []
