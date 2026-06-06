from typing import List
from src.providers.base import SearchProvider, SearchProviderInfo, SearchProviderSafetyStatus
from src.models.category import Category
from src.models.torrent import Torrent

class ExttoProvider(SearchProvider):
    """Extto.org provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="extto",
            name="Extto",
            url="https://extto.org",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
        )

    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Extto."""
        from urllib.parse import quote
        
        url = f"{self.info.url}/browse/?q={quote(query)}"
        
        try:
            self._ensure_proxy()
            html = self._get(url)
            if not html:
                return []
                
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.find('table', class_='search-table')
            if not table:
                return []
                
            tbody = table.find('tbody')
            if not tbody:
                return []
                
            torrents = []
            rows = tbody.find_all('tr')
            
            for row in rows:
                try:
                    cols = row.find_all('td')
                    if len(cols) < 6:
                        continue
                        
                    title_a = cols[0].find('a', href=lambda h: h and '/post-detail/' in h)
                    if not title_a:
                        continue
                        
                    name = title_a.get_text(strip=True)
                    desc_url = title_a['href']
                    if not desc_url.startswith('http'):
                        desc_url = self.info.url + desc_url
                        
                    magnet_a = cols[0].find('a', href=lambda h: h and h.startswith('magnet:'))
                    magnet_uri = magnet_a['href'] if magnet_a else ''
                    
                    size = cols[1].get_text(strip=True).replace('\xa0', ' ')
                    upload_date = cols[2].get_text(strip=True)
                    
                    seeders_str = cols[4].get_text(strip=True)
                    leechers_str = cols[5].get_text(strip=True)
                    
                    seeders = int(''.join(filter(str.isdigit, seeders_str))) if any(c.isdigit() for c in seeders_str) else 0
                    peers = int(''.join(filter(str.isdigit, leechers_str))) if any(c.isdigit() for c in leechers_str) else 0
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeders,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date=upload_date,
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except Exception:
                    continue
                    
            return torrents
            
        except Exception as e:
            print(f"Extto search error: {e}")
            return []
