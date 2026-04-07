"""1337x search provider."""

from typing import List
from bs4 import BeautifulSoup
from models.torrent import Torrent
from models.category import Category
from providers.base import SearchProvider, SearchProviderInfo, SearchProviderSafetyStatus


class LeetProvider(SearchProvider):
    """1337x.to torrent search provider."""
    
    def __init__(self):
        super().__init__()
        self.mirrors = [
            "https://www.1377x.to",
            "https://1377x.to",
            "https://1337xx.to",
            "https://1337x.to",
            "https://1337x.st",
            "https://x1337x.ws",
            "https://x1337x.eu",
        ]
        self._current_mirror = self.mirrors[0]
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="1337x",
            name="1337x",
            url=self._current_mirror,
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            safety_reason="Often blocked by ISP - enable manually if you use VPN",
            enabled_by_default=False,
            language="Multi",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search 1337x for torrents."""
        # Map our category to 1337x's URL category parameter
        cat_map = {
            Category.MOVIES: "Movies",
            Category.SERIES: "TV",
            Category.TV: "TV",
            Category.GAMES: "Games",
            Category.MUSIC: "Music",
            Category.APPS: "Apps",
            Category.ANIME: "Anime",
            Category.BOOKS: "Books",
            Category.PORN: "XXX",
            Category.OTHER: "Other",
        }
        
        cat_slug = cat_map.get(category)
        
        # Loop through mirrors until one works
        for mirror in self.mirrors:
            self._current_mirror = mirror
            
            # Using /category-search/ if a category is specified
            if cat_slug:
                url = f"{self.info.url}/category-search/{query}/{cat_slug}/1/"
            else:
                url = f"{self.info.url}/search/{query}/1/"
            
            try:
                html = self._get(url)
                if not html:
                    continue
                
                soup = BeautifulSoup(html, 'html.parser')
                table = soup.select_one('table.table-list tbody')
                
                if not table:
                    continue
                
                torrents = []
                for row in table.find_all('tr'):
                    torrent = self._parse_row(row)
                    if torrent:
                        torrents.append(torrent)
                
                if torrents:
                    return torrents
            except Exception as e:
                print(f"1337x search error on {mirror}: {e}")
                
        return []
    
    def _parse_row(self, row) -> Torrent:
        """Parse a table row into a Torrent object."""
        try:
            # Get name and URL
            name_cell = row.select_one('td.name')
            if not name_cell:
                return None
            
            name_links = name_cell.find_all('a')
            if len(name_links) < 2:
                return None
            
            name = name_links[1].get_text(strip=True)
            torrent_path = name_links[1].get('href', '')
            description_url = f"{self.info.url}{torrent_path}"
            
            # Get seeders
            seeders_cell = row.select_one('td.seeds')
            seeders = int(seeders_cell.get_text(strip=True)) if seeders_cell else 0
            
            # Get leechers (peers)
            peers_cell = row.select_one('td.leeches')
            peers = int(peers_cell.get_text(strip=True)) if peers_cell else 0
            
            # Get size
            size_cells = row.find_all('td')
            size = 'Unknown'
            upload_date = 'Unknown'
            
            # Size and date are in specific columns
            if len(size_cells) >= 5:
                size = size_cells[4].get_text(strip=True)
            
            # We don't have magnet directly from search page
            # For now, we'll skip magnet and require clicking through
            # In a full implementation, we'd fetch the detail page
            
            return Torrent(
                name=name,
                size=size,
                seeders=seeders,
                peers=peers,
                provider_id=self.info.id,
                provider_name=self.info.name,
                upload_date=upload_date,
                description_url=description_url,
                magnet_uri="",  # Would need to fetch from detail page
                category=self._guess_category(name),
            )
        except Exception as e:
            print(f"Error parsing 1337x row: {e}")
            return None
    
    def _guess_category(self, name: str) -> Category:
        """Guess category from torrent name."""
        name_lower = name.lower()
        
        if any(term in name_lower for term in ['s01', 's02', 'season', 'episode']):
            return Category.SERIES
        elif any(term in name_lower for term in ['1080p', '720p', 'bluray', 'webrip']):
            return Category.MOVIES
        elif any(term in name_lower for term in ['anime', 'subbed', 'dubbed']):
            return Category.ANIME
        elif any(term in name_lower for term in ['pc', 'game', 'repack']):
            return Category.GAMES
        elif any(term in name_lower for term in ['epub', 'pdf', 'mobi']):
            return Category.BOOKS
        elif any(term in name_lower for term in ['album', 'flac', 'mp3']):
            return Category.MUSIC
        else:
            return Category.OTHER
