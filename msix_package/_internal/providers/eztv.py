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
            url="https://eztv1.xyz",
            specialized_category=Category.TV,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
            language="English",
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
                    
                    # Extract size from title attribute which contains it in parentheses
                    # e.g., "Episode Name [eztv] (1.32 GB)"
                    size = 'Unknown'
                    title_attr = name_cell.get('title', '')
                    if title_attr and '(' in title_attr and ')' in title_attr:
                        # Extract the size from parentheses at the end
                        import re
                        size_match = re.search(r'\((\d+\.?\d*\s*(?:GB|MB|KB|TB))\)\s*$', title_attr, re.IGNORECASE)
                        if size_match:
                            size = size_match.group(1)
                    
                    # Fallback: try to get size from table cells based on column count
                    if size == 'Unknown':
                        cells = row.find_all('td')
                        if len(cells) >= 6:
                            # First row has 6 cells, size is at index 3
                            size_cell = cells[3] if len(cells) > 3 else None
                        elif len(cells) >= 5:
                            # Other rows have 5 cells, size is at index 2
                            size_cell = cells[2] if len(cells) > 2 else None
                        else:
                            size_cell = None
                        
                        if size_cell:
                            raw_size = size_cell.get_text(strip=True)
                            # Validate it looks like a size (contains MB, GB, etc.)
                            if any(unit in raw_size.upper() for unit in ['MB', 'GB', 'KB', 'TB']):
                                size = raw_size
                    
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
