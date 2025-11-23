"""Nyaa search provider."""

from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
from models.torrent import Torrent
from models.category import Category
from providers.base import SearchProvider, SearchProviderInfo, SearchProviderSafetyStatus


class NyaaProvider(SearchProvider):
    """Nyaa.si torrent search provider (specializes in Anime)."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="nyaasi",
            name="Nyaa",
            url="https://nyaa.si",
            specialized_category=Category.ANIME,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Nyaa for torrents."""
        # Nyaa specializes in anime
        url = f"{self.info.url}/?f=0&c=1_0&q={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.select_one('table.torrent-list > tbody')
            
            if not table:
                return []
            
            torrents = []
            for row in table.find_all('tr'):
                torrent = self._parse_row(row)
                if torrent:
                    torrents.append(torrent)
            
            return torrents
        except Exception as e:
            print(f"Nyaa search error: {e}")
            return []
    
    def _parse_row(self, row) -> Torrent:
        """Parse a table row into a Torrent object."""
        try:
            # Get name and description URL
            name_cell = row.select_one('td:nth-child(2)')
            if not name_cell:
                return None
            
            name_link = name_cell.select_one('a:nth-child(2)')
            if not name_link:
                return None
            
            name = name_link.get_text(strip=True)
            desc_path = name_link.get('href', '')
            description_url = f"{self.info.url}{desc_path}"
            
            # Get magnet link
            magnet_cell = row.select_one('td:nth-child(3)')
            if not magnet_cell:
                return None
            
            magnet_link = magnet_cell.select_one('a:nth-child(2)')
            if not magnet_link:
                return None
            
            magnet_uri = magnet_link.get('href', '')
            
            # Get size
            size_cell = row.select_one('td:nth-child(4)')
            size = size_cell.get_text(strip=True) if size_cell else 'Unknown'
            
            # Get upload date
            date_cell = row.select_one('td:nth-child(5)')
            upload_date = 'Unknown'
            if date_cell:
                timestamp = date_cell.get('data-timestamp', '')
                if timestamp:
                    upload_date = self._format_date(int(timestamp))
            
            # Get seeders and peers
            seeders_cell = row.select_one('td:nth-child(6)')
            seeders = int(seeders_cell.get_text(strip=True)) if seeders_cell else 0
            
            peers_cell = row.select_one('td:nth-child(7)')
            peers = int(peers_cell.get_text(strip=True)) if peers_cell else 0
            
            return Torrent(
                name=name,
                size=size,
                seeders=seeders,
                peers=peers,
                provider_id=self.info.id,
                provider_name=self.info.name,
                upload_date=upload_date,
                description_url=description_url,
                magnet_uri=magnet_uri,
                category=Category.ANIME,
            )
        except Exception as e:
            print(f"Error parsing Nyaa row: {e}")
            return None
    
    def _format_date(self, timestamp: int) -> str:
        """Format Unix timestamp to date string."""
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d')
        except:
            return 'Unknown'
