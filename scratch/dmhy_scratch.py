from typing import List
from src.providers.base import SearchProvider, SearchProviderInfo, SearchProviderSafetyStatus
from src.models.category import Category
from src.models.torrent import Torrent

class DmhyProvider(SearchProvider):
    """share.dmhy.org provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="dmhy",
            name="DMHY",
            url="https://share.dmhy.org",
            specialized_category=Category.ANIME,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
            language="Chinese",
        )

    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search DMHY."""
        from urllib.parse import quote
        
        url = f"{self.info.url}/topics/list?keyword={quote(query)}"
        
        try:
            self._ensure_proxy()
            html = self._get(url)
            if not html:
                return []
                
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.find('table', id='topic_list')
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
                    if len(cols) < 7:
                        continue
                        
                    title_td = cols[2]
                    name = title_td.get_text(separator=' ', strip=True)
                    if not name:
                        continue
                        
                    title_a = title_td.find('a', target='_blank')
                    desc_url = title_a['href'] if title_a else ''
                    if desc_url and not desc_url.startswith('http'):
                        desc_url = self.info.url + desc_url
                        
                    magnet_a = cols[3].find('a', href=lambda h: h and h.startswith('magnet:'))
                    magnet_uri = magnet_a['href'] if magnet_a else ''
                    
                    # DMHY sometimes repeats the date in a hidden span
                    upload_date_raw = cols[0].get_text(separator='|', strip=True)
                    upload_date = upload_date_raw.split('|')[0].strip()
                    
                    size = cols[4].get_text(strip=True)
                    
                    seeders_str = cols[5].get_text(strip=True)
                    leechers_str = cols[6].get_text(strip=True)
                    
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
                        category=Category.ANIME,
                    )
                    torrents.append(t)
                except Exception:
                    continue
                    
            return torrents
            
        except Exception as e:
            print(f"DMHY search error: {e}")
            return []
