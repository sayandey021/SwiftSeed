"""Placeholder providers for additional torrent sites."""

from typing import List, Optional
from bs4 import BeautifulSoup
from models.torrent import Torrent
from models.category import Category
from providers.base import SearchProvider, SearchProviderInfo, SearchProviderSafetyStatus


class AnimeToshoProvider(SearchProvider):
    """AnimeTosho provider - anime torrents with DDL mirrors."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="animetosho",
            name="AnimeTosho",
            url="https://animetosho.org",
            specialized_category=Category.ANIME,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,  # Good anime source
            language="English",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search AnimeTosho."""
        import re
        url = f"{self.info.url}/search?q={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # AnimeTosho uses divs for entries
            entries = soup.select('div.home_list_entry, div.entry')
            
            for entry in entries:
                try:
                    # Get title
                    title_link = entry.select_one('a.link, div.link a')
                    if not title_link:
                        continue
                    
                    name = title_link.get_text(strip=True)
                    href = title_link.get('href', '')
                    desc_url = self.info.url + href if not href.startswith('http') else href
                    
                    # Get magnet link
                    magnet = entry.select_one('a[href^="magnet:"]')
                    magnet_uri = magnet.get('href', '') if magnet else ''
                    
                    # Get size
                    size_elem = entry.select_one('div.size, span.size')
                    size = size_elem.get_text(strip=True) if size_elem else 'Unknown'
                    
                    # Get seeds/peers
                    seeds = 0
                    peers = 0
                    
                    # Try to find the stats span (usually has color style and title with stats)
                    # It's often inside div.links
                    stats_span = entry.select_one('span[title*="Seeders"]')
                    
                    if stats_span:
                        title_text = stats_span.get('title', '')
                        # Format: "Seeders: 398 / Leechers: 15"
                        s_match = re.search(r'Seeders:\s*(\d+)', title_text)
                        if s_match:
                            seeds = int(s_match.group(1))
                        
                        l_match = re.search(r'Leechers:\s*(\d+)', title_text)
                        if l_match:
                            peers = int(l_match.group(1))
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeds,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.ANIME,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"AnimeTosho search error: {e}")
            return []


class KnabenProvider(SearchProvider):
    """Knaben provider - aggregates results from multiple torrent sites."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="knaben",
            name="Knaben",
            url="https://knaben.org",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
            language="Multi",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Knaben for torrents."""
        url = f"{self.info.url}/search/{query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('tr')
            
            torrents = []
            for row in rows:
                try:
                    cols = row.find_all('td')
                    if len(cols) < 6:
                        continue
                    
                    # Find title link - can be to external sites
                    title_link = None
                    for a in row.find_all('a'):
                        href = a.get('href', '')
                        if '/torrent/' in href or 'torrent' in href.lower():
                            title_link = a
                            break
                    
                    if not title_link:
                        # Try first link in second column
                        title_link = cols[1].find('a')
                    
                    if not title_link:
                        continue
                    
                    name = title_link.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue
                        
                    desc_url = title_link.get('href', '')
                    
                    # Magnet link - Try direct magnet first
                    magnet = row.select_one('a[href^="magnet:"]')
                    magnet_uri = magnet.get('href', '') if magnet else ''
                    
                    # If no direct magnet, try to extract infohash from URL
                    if not magnet_uri:
                        import re
                        # Try to find infohash pattern in any href
                        for a in row.find_all('a'):
                            href = a.get('href', '')
                            # Look for 40 character hex hash
                            hash_match = re.search(r'([a-fA-F0-9]{40})', href)
                            if hash_match:
                                infohash = hash_match.group(1)
                                trackers = [
                                    "udp://tracker.opentrackr.org:1337/announce",
                                    "udp://open.stealth.si:80/announce",
                                    "udp://tracker.openbittorrent.com:6969/announce",
                                ]
                                tracker_str = "&tr=".join(trackers)
                                magnet_uri = f"magnet:?xt=urn:btih:{infohash}&dn={name}&tr={tracker_str}"
                                break
                    
                    # Size (column 2)
                    size = cols[2].get_text(strip=True) if len(cols) > 2 else 'Unknown'
                    
                    # Seeds (column 4)
                    seeds = 0
                    if len(cols) > 4:
                        seeds_text = cols[4].get_text(strip=True).replace(',', '')
                        seeds = int(seeds_text) if seeds_text.isdigit() else 0
                    
                    # Leeches (column 5)
                    peers = 0
                    if len(cols) > 5:
                        peers_text = cols[5].get_text(strip=True).replace(',', '')
                        peers = int(peers_text) if peers_text.isdigit() else 0
                    
                    # Date (column 3)
                    upload_date = cols[3].get_text(strip=True) if len(cols) > 3 else 'Unknown'
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeds,
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
            print(f"Knaben search error: {e}")
            return []


class LimeTorrentsProvider(SearchProvider):
    """LimeTorrents provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="limetorrents",
            name="Lime Torrents",
            url="https://www.limetorrents.lol",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.UNSAFE,
            safety_reason="May contain malicious ads and popups",
            enabled_by_default=False,
            language="Multi",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search LimeTorrents."""
        url = f"{self.info.url}/search/all/{query}/seeds/1/"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            # LimeTorrents uses table with class 'table2'
            rows = soup.select('table.table2 tr')
            
            torrents = []
            for row in rows[1:]:  # Skip header
                try:
                    cols = row.find_all('td')
                    if len(cols) < 6:
                        continue
                    
                    # Title in first column
                    title_div = cols[0].select_one('div.tt-name a:nth-child(2)')
                    if not title_div:
                        continue
                    
                    name = title_div.get_text(strip=True)
                    desc_url = title_div.get('href', '')
                    if desc_url and not desc_url.startswith('http'):
                        desc_url = self.info.url + desc_url
                    
                    # Size in 3rd column
                    size = cols[2].get_text(strip=True)
                    
                    # Seeds in 4th column
                    seeds_text = cols[3].get_text(strip=True).replace(',', '')
                    seeds = int(seeds_text) if seeds_text.isdigit() else 0
                    
                    # Leeches in 5th column
                    peers_text = cols[4].get_text(strip=True).replace(',', '')
                    peers = int(peers_text) if peers_text.isdigit() else 0
                    
                    # Get magnet from the torrent hash link
                    hash_link = cols[0].select_one('a.csprite_dl14')
                    magnet_uri = ''
                    if hash_link:
                        href = hash_link.get('href', '')
                        if 'magnet:' in href:
                            magnet_uri = href
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeds,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"LimeTorrents search error: {e}")
            return []


class MyPornClubProvider(SearchProvider):
    """MyPornClub provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="mypornclub",
            name="MyPornClub",
            url="https://myporn.club",
            specialized_category=Category.PORN,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search MyPornClub."""
        from urllib.parse import quote
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Correct URL pattern: /s/{query}
        url = f"{self.info.url}/s/{quote(query)}"
        
        try:
            html = self._get(url)
            if not html:
                print("MyPornClub: Empty response from search")
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            pending_torrents = []  # Torrents that need magnet fetching
            
            # Results are in .torrent_element containers
            results = soup.select('.torrent_element')
            print(f"MyPornClub: Found {len(results)} results")
            
            # Limit to first 20 for speed (need to fetch detail pages for magnets)
            for result in results[:20]:
                try:
                    # Find title link (a.tdn with href starting with /t/)
                    title_link = result.select_one('a.tdn[href^="/t/"]:not(.linkadd)')
                    if not title_link:
                        # Fallback to any link with /t/
                        title_link = result.select_one('a[href^="/t/"]')
                    
                    if not title_link:
                        continue
                    
                    name = title_link.get_text(strip=True)
                    if not name or len(name) < 5:
                        continue
                    
                    desc_path = title_link.get('href', '')
                    desc_url = f"{self.info.url}{desc_path}"
                    
                    # Try to get uploader time from .linkadd
                    upload_date = 'Unknown'
                    time_link = result.select_one('a.linkadd')
                    if time_link:
                        upload_date = time_link.get_text(strip=True)
                    
                    t = Torrent(
                        name=name,
                        size='Unknown',
                        seeders=0,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date=upload_date,
                        description_url=desc_url,
                        magnet_uri='',  # Will be fetched
                        category=Category.PORN,
                    )
                    pending_torrents.append(t)
                except Exception:
                    continue
            
            # Fetch magnet links in parallel
            if pending_torrents:
                self._fetch_magnets_parallel(pending_torrents)
            
            # Filter out torrents without magnet links
            torrents = [t for t in pending_torrents if t.magnet_uri]
            
            print(f"MyPornClub: Returning {len(torrents)} results with magnets")
            return torrents
        except Exception as e:
            print(f"MyPornClub search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _fetch_magnets_parallel(self, torrents: List[Torrent]):
        """Fetch magnet links from detail pages in parallel."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import re
        
        def fetch_detail(torrent: Torrent):
            try:
                detail_html = self._get(torrent.description_url, timeout=10)
                if not detail_html:
                    return
                
                detail_soup = BeautifulSoup(detail_html, 'html.parser')
                
                # Find magnet link
                magnet_elem = detail_soup.select_one('a[href^="magnet:"]')
                if magnet_elem:
                    torrent.magnet_uri = magnet_elem.get('href', '')
                
                # Extract seeders
                seeders_elem = detail_soup.select_one('.teiv_seeders')
                if seeders_elem:
                    seeders_text = seeders_elem.get_text(strip=True)
                    if seeders_text.isdigit():
                        torrent.seeders = int(seeders_text)
                
                # Extract leechers/peers
                leechers_elem = detail_soup.select_one('.teiv_leechers')
                if leechers_elem:
                    leechers_text = leechers_elem.get_text(strip=True)
                    if leechers_text.isdigit():
                        torrent.peers = int(leechers_text)
                
                # Try to extract size from detail page
                size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:GB|MB|KB|TB|GiB|MiB|Gb|Mb))', detail_html, re.IGNORECASE)
                if size_match:
                    torrent.size = size_match.group(1)
                    
            except Exception as e:
                print(f"MyPornClub: Detail fetch error: {e}")
        
        # Fetch in parallel with 5 workers
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_detail, t) for t in torrents]
            for future in as_completed(futures, timeout=30):
                try:
                    future.result()
                except:
                    pass


class SukebeiProvider(SearchProvider):
    """Sukebei (Nyaa for adult content) provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="sukebei",
            name="Sukebei",
            url="https://sukebei.nyaa.si",
            specialized_category=Category.PORN,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Sukebei (Nyaa adult version)."""
        # Same structure as Nyaa.si
        url = f"{self.info.url}/?f=0&c=0_0&q={query}"
        
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
                try:
                    # Get name and description URL (column 2)
                    name_cell = row.select_one('td:nth-child(2)')
                    if not name_cell:
                        continue
                    
                    # Sukebei has links: first is category, second is the torrent name
                    name_link = name_cell.select_one('a:nth-child(2)') or name_cell.select_one('a')
                    if not name_link:
                        continue
                    
                    name = name_link.get_text(strip=True)
                    desc_path = name_link.get('href', '')
                    description_url = f"{self.info.url}{desc_path}"
                    
                    # Get magnet link (column 3)
                    magnet_cell = row.select_one('td:nth-child(3)')
                    if not magnet_cell:
                        continue
                    
                    magnet_link = magnet_cell.select_one('a[href^="magnet:"]')
                    if not magnet_link:
                        continue
                    
                    magnet_uri = magnet_link.get('href', '')
                    
                    # Get size (column 4)
                    size_cell = row.select_one('td:nth-child(4)')
                    size = size_cell.get_text(strip=True) if size_cell else 'Unknown'
                    
                    # Get upload date (column 5)
                    date_cell = row.select_one('td:nth-child(5)')
                    upload_date = 'Unknown'
                    if date_cell:
                        timestamp = date_cell.get('data-timestamp', '')
                        if timestamp:
                            try:
                                from datetime import datetime
                                dt = datetime.fromtimestamp(int(timestamp))
                                upload_date = dt.strftime('%Y-%m-%d')
                            except:
                                upload_date = date_cell.get_text(strip=True)
                    
                    # Get seeders and peers (columns 6 and 7)
                    seeders_cell = row.select_one('td:nth-child(6)')
                    seeders = int(seeders_cell.get_text(strip=True)) if seeders_cell else 0
                    
                    peers_cell = row.select_one('td:nth-child(7)')
                    peers = int(peers_cell.get_text(strip=True)) if peers_cell else 0
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeders,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date=upload_date,
                        description_url=description_url,
                        magnet_uri=magnet_uri,
                        category=Category.PORN,
                    )
                    torrents.append(t)
                except Exception:
                    continue
            
            return torrents
        except Exception as e:
            print(f"Sukebei search error: {e}")
            return []


class TokyoToshokanProvider(SearchProvider):
    """Tokyo Toshokan provider - Japanese torrent tracker for anime."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="tokyotoshokan",
            name="Tokyo Toshokan",
            url="https://www.tokyotosho.info",
            specialized_category=Category.ANIME,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,  # Good anime source
            language="Japanese",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Tokyo Toshokan."""
        import re
        url = f"{self.info.url}/search.php?terms={query}&type=1"  # type=1 for anime
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Tokyo Toshokan results are split across two rows
            # We iterate through all rows and process them
            rows = soup.select('tr')
            
            i = 0
            while i < len(rows):
                row = rows[i]
                
                # Check for the top row which contains the title (td.desc-top)
                desc_top = row.select_one('td.desc-top')
                if not desc_top:
                    i += 1
                    continue
                    
                try:
                    # --- Parse Top Row (Title & Magnet) ---
                    links = desc_top.find_all('a')
                    name = "Unknown"
                    magnet_uri = ""
                    desc_url = ""
                    
                    for link in links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        
                        if href.startswith('magnet:'):
                            magnet_uri = href
                        elif text: 
                            # If the link has text, it's likely the title link
                            name = text
                            if href.startswith('http'):
                                desc_url = href
                            else:
                                desc_url = f"{self.info.url}/{href.lstrip('/')}"
                    
                    # If we couldn't find a name, skip
                    if name == "Unknown":
                        i += 1
                        continue

                    # --- Parse Bottom Row (Size & Stats) ---
                    # The stats are usually in the next row
                    size = "Unknown"
                    seeds = 0
                    peers = 0
                    
                    if i + 1 < len(rows):
                        next_row = rows[i+1]
                        
                        # Size is in td.desc-bot
                        desc_bot = next_row.select_one('td.desc-bot')
                        if desc_bot:
                            bot_text = desc_bot.get_text(strip=True)
                            # Matches: Size: 4.12GB
                            size_match = re.search(r'Size:\s*([0-9.]+\s*[A-Za-z]+)', bot_text)
                            if size_match:
                                size = size_match.group(1)
                        
                        # Stats are in td.stats
                        stats_td = next_row.select_one('td.stats')
                        if stats_td:
                            stats_text = stats_td.get_text(strip=True)
                            # Text example: S:16L:1C:1161...
                            s_match = re.search(r'S:\s*(\d+)', stats_text)
                            if s_match:
                                seeds = int(s_match.group(1))
                            
                            l_match = re.search(r'L:\s*(\d+)', stats_text)
                            if l_match:
                                peers = int(l_match.group(1))
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeds,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.ANIME,
                    )
                    torrents.append(t)
                    
                    # Advance index: we processed row i and peeked at i+1. 
                    # If i+1 was the stats row (which it should be), we might want to skip it in the main loop to avoid reprocessing.
                    # Since the stats row generally *doesn't* have td.desc-top, it would be skipped by the `if not desc_top` check anyway.
                    # But jumping 1 is safer/faster.
                    i += 1 
                    
                except Exception:
                    # If something breaks, just move to next
                    pass
                
                i += 1
            
            return torrents
        except Exception as e:
            print(f"Tokyo Toshokan search error: {e}")
            return []


class KickassTorrentsProvider(SearchProvider):
    """Kickass Torrents provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="kickasstorrents",
            name="Kickass Torrents",
            url="https://kickass.torrentbay.st",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Kickass Torrents."""
        url = f"{self.info.url}/usearch/{query}/"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('tr.odd, tr.even')
            
            torrents = []
            for row in rows:
                try:
                    # Title
                    title_cell = row.select_one('a.cellMainLink')
                    if not title_cell:
                        continue
                    
                    name = title_cell.get_text(strip=True)
                    desc_url = self.info.url + title_cell.get('href', '')
                    
                    # Magnet
                    magnet_link = row.select_one('a[title="Torrent magnet link"]')
                    magnet_uri = magnet_link.get('href', '') if magnet_link else ''
                    
                    # Size
                    size_cell = row.select_one('td:nth-child(2)')
                    size = size_cell.get_text(strip=True) if size_cell else 'Unknown'
                    
                    # Seeds
                    seeds_cell = row.select_one('td:nth-child(4)')
                    seeds = int(seeds_cell.get_text(strip=True)) if seeds_cell else 0
                    
                    # Peers
                    peers_cell = row.select_one('td:nth-child(5)')
                    peers = int(peers_cell.get_text(strip=True)) if peers_cell else 0
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeds,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"Kickass search error: {e}")
            return []


class TorrentGalaxyProvider(SearchProvider):
    """TorrentGalaxy provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="torrentgalaxy",
            name="TorrentGalaxy",
            url="https://en.torrentgalaxy-official.is",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search TorrentGalaxy."""
        url = f"{self.info.url}/torrents.php?search={query}&sort=seeders&order=desc"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            # TGX usually has rows with class 'tgxtablerow'
            rows = soup.select('div.tgxtable div.tgxtablerow')
            
            torrents = []
            for row in rows:
                try:
                    # Title
                    title_link = row.select_one('a[href^="/torrent/"]')
                    if not title_link:
                        continue
                        
                    name = title_link.get_text(strip=True)
                    desc_url = self.info.url + title_link.get('href', '')
                    
                    # Magnet
                    magnet_link = row.select_one('a[href^="magnet:"]')
                    magnet_uri = magnet_link.get('href', '') if magnet_link else ''
                    
                    # Size (often in a span with style or class)
                    # This is tricky without seeing HTML, but usually it's one of the cells
                    cells = row.select('div.tgxtablecell')
                    if len(cells) < 5:
                        continue
                        
                    size = cells[2].get_text(strip=True)
                    
                    # Seeds/Peers
                    seeds = 0
                    peers = 0
                    try:
                        seeds_color = row.select_one('font[color="green"]')
                        if seeds_color:
                            seeds = int(seeds_color.get_text(strip=True))
                            
                        peers_color = row.select_one('font[color="#ff0000"]')
                        if peers_color:
                            peers = int(peers_color.get_text(strip=True))
                    except:
                        pass
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeds,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"TorrentGalaxy search error: {e}")
            return []


class IDopeProvider(SearchProvider):
    """iDope provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="idope",
            name="iDope",
            url="https://idope.se",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search iDope."""
        url = f"{self.info.url}/torrent-list/{query}/"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # iDope uses div.resultdiv for results container
            # Each result has div.resultrow
            items = soup.select('div.resultrow')
            
            # If no resultrow, try alternative selectors
            if not items:
                items = soup.select('div.result')
            
            torrents = []
            for item in items:
                try:
                    # Title - usually in a link
                    title_elem = item.select_one('div.resultdivtop a, div.torrent_name a, a.title')
                    if not title_elem:
                        # Try any link in the item
                        title_elem = item.find('a')
                    
                    if not title_elem:
                        continue
                        
                    name = title_elem.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue
                        
                    href = title_elem.get('href', '')
                    desc_url = href if href.startswith('http') else self.info.url + href
                    
                    # Try to find infohash in the href or data attribute
                    # iDope URLs often contain the infohash: /torrent/{infohash}/name
                    infohash = ''
                    import re
                    hash_match = re.search(r'/torrent/([a-fA-F0-9]{40})/', href)
                    if hash_match:
                        infohash = hash_match.group(1)
                    else:
                        # Try data-id attribute
                        infohash = item.get('data-id', '') or item.get('data-hash', '')
                    
                    # Construct magnet URI from infohash
                    magnet_uri = ''
                    if infohash:
                        magnet_uri = f"magnet:?xt=urn:btih:{infohash}&dn={name}"
                    
                    # Size
                    size = 'Unknown'
                    size_elem = item.select_one('div.resultdivbotton, div.size, span.size')
                    if size_elem:
                        size_text = size_elem.get_text(strip=True)
                        # Extract size pattern
                        size_match = re.search(r'(\d+(\.\d+)?\s*(GB|MB|KB|TB))', size_text, re.IGNORECASE)
                        if size_match:
                            size = size_match.group(1)
                    
                    # Seeds
                    seeds = 0
                    seeds_elem = item.select_one('div.resultdivbottonseed, span.seed, div.seed')
                    if seeds_elem:
                        seeds_text = seeds_elem.get_text(strip=True).replace(',', '')
                        if seeds_text.isdigit():
                            seeds = int(seeds_text)
                    
                    # If we have no magnet and no infohash, skip this result
                    # as it won't be useful without download capability
                    if not magnet_uri:
                        continue
                    
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
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"iDope search error: {e}")
            return []


class MagnetCatProvider(SearchProvider):
    """MagnetCat provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="magnetcat",
            name="MagnetCat",
            url="https://magnetcatcat.com",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search MagnetCat."""
        url = f"{self.info.url}/search?q={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('table#magnet-table tr')
            
            torrents = []
            for row in rows:
                try:
                    # Skip header
                    if row.find('th'):
                        continue
                        
                    cols = row.find_all('td')
                    if len(cols) < 4:
                        continue
                        
                    # Title
                    title_link = cols[0].find('a')
                    if not title_link:
                        continue
                        
                    name = title_link.get_text(strip=True)
                    desc_url = self.info.url + title_link.get('href', '')
                    
                    # Magnet
                    magnet_link = cols[0].select_one('a[href^="magnet:"]')
                    magnet_uri = magnet_link.get('href', '') if magnet_link else ''
                    
                    # Size - validate and format
                    size_raw = cols[1].get_text(strip=True)
                    import re as re_inner
                    size_match = re_inner.search(r'(\d+(?:[.,]\d+)?)\s*(GB|GiB|MB|MiB|KB|KiB|TB|TiB)', size_raw, re_inner.I)
                    if size_match:
                        try:
                            num_val = float(size_match.group(1).replace(',', '.'))
                            unit = size_match.group(2)
                            if num_val == int(num_val):
                                size = f"{int(num_val)} {unit}"
                            else:
                                size = f"{num_val:.2f} {unit}"
                        except:
                            size = size_raw if size_raw else 'Unknown'
                    else:
                        size = size_raw if size_raw else 'Unknown'
                    
                    # Seeds
                    seeds = int(cols[2].get_text(strip=True))
                    
                    # Peers
                    peers = int(cols[3].get_text(strip=True))
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeds,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"MagnetCat search error: {e}")
            return []


class ApacheTorrentProvider(SearchProvider):
    """ApacheTorrent provider - movies and series."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="apachetorrent",
            name="Apache Torrent",
            url="https://apachetorrent.com",
            specialized_category=Category.MOVIES,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
            language="Portuguese",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Apache Torrent."""
        import re
        url = f"{self.info.url}/index.php?s={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Find results in div.capaname
            items = soup.select('div.capaname')
            
            # Limit to first 8 items to balance performance and results
            for item in items[:8]:
                try:
                    # Get detail URL
                    link_tag = item.find('a')
                    if not link_tag:
                        continue
                        
                    desc_url = link_tag.get('href', '')
                    if not desc_url:
                        continue
                     
                    if not desc_url.startswith('http'):
                        desc_url = f"{self.info.url}/{desc_url.lstrip('/')}"
                        
                    # Get title
                    title_tag = item.find('h2') or item.find('h3') or item.select_one('div.titulo')
                    if title_tag:
                        name_text = title_tag.get_text(separator=' ', strip=True)
                    else:
                        name_text = item.get_text(strip=True)
                        
                    name = re.sub(r'\s+', ' ', name_text).strip()
                    if not name:
                        name = "Unknown Title"
                    
                    # Fetch details
                    detail_html = self._get(desc_url)
                    if not detail_html:
                        continue
                        
                    detail_soup = BeautifulSoup(detail_html, 'html.parser')
                    
                    # Get magnet
                    magnet_link = detail_soup.select_one('a[href^="magnet:"]')
                    magnet_uri = magnet_link.get('href', '').strip() if magnet_link else ''
                    
                    if not magnet_uri:
                        continue 
                    
                    # Get size
                    text_content = detail_soup.get_text(separator=' ', strip=True)
                    size = "Unknown"
                    size_match = re.search(r'Tamanho\s*:\s*([\d\.]+\s*[GMK]B)', text_content, re.IGNORECASE)
                    if size_match:
                        size = size_match.group(1)
                    else: 
                         size_match = re.search(r'(\d+(\.\d+)?\s*(GB|MB|KB))', text_content)
                         if size_match:
                             size = size_match.group(1)

                    # Date
                    upload_date = "Unknown"
                    date_match = re.search(r'Data de publicação\s*:\s*(.*?)(?:\s+Categorias|\s*\||<|$)', text_content, re.IGNORECASE)
                    if date_match:
                        upload_date = date_match.group(1).strip()

                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=0, # Unknown
                        peers=0,   # Unknown
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date=upload_date,
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.MOVIES,
                    )
                    torrents.append(t)
                    
                except Exception as e:
                    continue
            
            return torrents
        except Exception as e:
            print(f"ApacheTorrent search error: {e}")
            return []


class BlueRomsProvider(SearchProvider):
    """BlueRoms provider (Gaming ROMs and related)."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="blueroms",
            name="BlueRoms",
            url="https://www.blueroms.ws",
            specialized_category=Category.OTHER,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search BlueRoms."""
        url = f"{self.info.url}/?s={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.select('article.post')
            
            torrents = []
            for article in articles:
                try:
                    title_link = article.select_one('h2.entry-title a')
                    if not title_link:
                        continue
                        
                    name = title_link.get_text(strip=True)
                    desc_url = title_link.get('href', '')
                    
                    # BlueRoms doesn't show magnet in search, user needs to visit page
                    magnet_uri = ''
                    
                    t = Torrent(
                        name=name,
                        size='Unknown',
                        seeders=0,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.OTHER,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"BlueRoms search error: {e}")
            return []


class LinuxTrackerProvider(SearchProvider):
    """LinuxTracker provider (Linux distributions)."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="linuxtracker",
            name="LinuxTracker",
            url="https://linuxtracker.org/index.php",
            specialized_category=Category.OTHER,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search LinuxTracker."""
        url = f"{self.info.url}?page=torrents&search={query}&active=1"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('table.lista tr')
            
            torrents = []
            for row in rows[1:]:  # Skip header
                try:
                    cols = row.find_all('td')
                    if len(cols) < 7:
                        continue
                        
                    title_link = cols[1].find('a')
                    if not title_link:
                        continue
                        
                    name = title_link.get_text(strip=True)
                    desc_url = "https://linuxtracker.org/" + title_link.get('href', '')
                    
                    # Size - try to find the column with actual size (GB/MB pattern)
                    size = 'Unknown'
                    import re
                    for col_idx in [3, 4, 2, 5]:  # Try multiple columns
                        if col_idx < len(cols):
                            col_text = cols[col_idx].get_text(strip=True)
                            # Check if it looks like a size (has GB/MB/KB/TB)
                            if re.search(r'\d+(?:\.\d+)?\s*(?:GB|MB|KB|TB|GiB|MiB|KiB)', col_text, re.I):
                                size = col_text
                                break
                    
                    # Seeds/Peers - find the correct columns with numeric values
                    seeds = 0
                    peers = 0
                    for i in range(len(cols) - 2, 3, -1):  # Start from end, go backwards
                        col_text = cols[i].get_text(strip=True)
                        if col_text.isdigit():
                            if seeds == 0:
                                seeds = int(col_text)
                            elif peers == 0:
                                peers = int(col_text)
                                break
                    
                    # Magnet - LinuxTracker usually requires visiting the page
                    magnet_uri = ''
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeds,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.OTHER,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"LinuxTracker search error: {e}")
            return []


class PluginTorrentProvider(SearchProvider):
    """PluginTorrent provider (Audio plugins/VST)."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="plugintorrent",
            name="PluginTorrent",
            url="https://plugintorrent.com",
            specialized_category=Category.OTHER,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search PluginTorrent."""
        import re
        url = f"{self.info.url}/?s={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.select('article')
            
            torrents = []
            # Limit to first 15 results for speed (each requires a detail page fetch)
            for article in articles[:15]:
                try:
                    title_link = article.select_one('h2.entry-title a, h2 a, h3 a')
                    if not title_link:
                        continue
                        
                    name = title_link.get_text(strip=True)
                    desc_url = title_link.get('href', '')
                    
                    if not desc_url:
                        continue
                    
                    # Fetch detail page to get magnet link
                    detail_html = self._get(desc_url)
                    if not detail_html:
                        continue
                    
                    detail_soup = BeautifulSoup(detail_html, 'html.parser')
                    
                    # Find magnet link
                    magnet_elem = detail_soup.select_one('a[href^="magnet:"]')
                    if not magnet_elem:
                        continue  # Skip results without magnet links
                    
                    magnet_uri = magnet_elem.get('href', '')
                    
                    # Try to extract size from page content
                    size = 'Unknown'
                    page_text = detail_soup.get_text(separator=' ', strip=True)
                    # Look for size patterns like "1.5 GB", "500 MB"
                    size_match = re.search(r'(\d+(?:\.\d+)?)\s*(GB|MB|TB|KB|GiB|MiB)', page_text, re.IGNORECASE)
                    if size_match:
                        size = f"{size_match.group(1)} {size_match.group(2).upper()}"
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=0,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.OTHER,
                    )
                    torrents.append(t)
                except Exception:
                    continue
            
            return torrents
        except Exception as e:
            print(f"PluginTorrent search error: {e}")
            return []


class VSTTorrentzProvider(SearchProvider):
    """VSTTorrentz provider (Audio plugins/VST)."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="vsttorrentz",
            name="VSTTorrentz",
            url="https://vsttorrentz.net",
            specialized_category=Category.OTHER,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search VSTTorrentz."""
        import re
        from urllib.parse import urlparse, parse_qs, unquote
        url = f"{self.info.url}/?s={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.select('article')
            
            torrents = []
            # Limit to first 12 results for speed
            for article in articles[:12]:
                try:
                    title_link = article.select_one('.entry-title a, h2 a, h3 a')
                    if not title_link:
                        continue
                        
                    name = title_link.get_text(strip=True)
                    desc_url = title_link.get('href', '')
                    
                    if not desc_url:
                        continue
                    
                    # Fetch detail page to get magnet link
                    detail_html = self._get(desc_url)
                    if not detail_html:
                        continue
                    
                    detail_soup = BeautifulSoup(detail_html, 'html.parser')
                    
                    magnet_uri = ''
                    
                    # Method 1: Direct magnet link
                    magnet_elem = detail_soup.select_one('a[href^="magnet:"]')
                    if magnet_elem:
                        magnet_uri = magnet_elem.get('href', '')
                    
                    # Method 2: Magnet in gateway URL (freemusicplugins.com?file=magnet:...)
                    if not magnet_uri:
                        all_links = detail_soup.select('a[href]')
                        for link in all_links:
                            href = link.get('href', '')
                            # Check for gateway URLs with magnet in 'file' parameter
                            if 'file=magnet' in href or 'fallback=magnet' in href:
                                parsed = urlparse(href)
                                params = parse_qs(parsed.query)
                                # Try 'file' then 'fallback' parameter
                                for param in ['file', 'fallback']:
                                    if param in params:
                                        value = unquote(params[param][0])
                                        if value.startswith('magnet:'):
                                            magnet_uri = value
                                            break
                                if magnet_uri:
                                    break
                    
                    # Method 3: Direct .torrent file link
                    if not magnet_uri:
                        torrent_link = detail_soup.select_one('a[href$=".torrent"]')
                        if torrent_link:
                            magnet_uri = torrent_link.get('href', '')
                    
                    if not magnet_uri:
                        continue  # Skip results without download links
                    
                    # Try to extract size from page content
                    size = 'Unknown'
                    page_text = detail_soup.get_text(separator=' ', strip=True)
                    size_match = re.search(r'(\d+(?:\.\d+)?)\s*(GB|MB|TB|KB|GiB|MiB)', page_text, re.IGNORECASE)
                    if size_match:
                        size = f"{size_match.group(1)} {size_match.group(2).upper()}"
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=0,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.OTHER,
                    )
                    torrents.append(t)
                except Exception:
                    continue
            
            return torrents
        except Exception as e:
            print(f"VSTTorrentz search error: {e}")
            return []


class VSTorrentProvider(SearchProvider):
    """VSTorrent provider (Audio plugins/VST)."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="vstorrent",
            name="VSTorrent",
            url="https://vstorrent.org",
            specialized_category=Category.OTHER,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search VSTorrent."""
        import re
        url = f"{self.info.url}/?s={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.select('article, .post')
            
            torrents = []
            # Limit to first 15 results for speed (each requires a detail page fetch)
            for article in articles[:15]:
                try:
                    title_link = article.select_one('.entry-title a, h2 a, h3 a, a.title')
                    if not title_link:
                        continue
                        
                    name = title_link.get_text(strip=True)
                    desc_url = title_link.get('href', '')
                    
                    if not desc_url:
                        continue
                    
                    # Fetch detail page to get magnet link
                    detail_html = self._get(desc_url)
                    if not detail_html:
                        continue
                    
                    detail_soup = BeautifulSoup(detail_html, 'html.parser')
                    
                    # Find magnet link
                    magnet_elem = detail_soup.select_one('a[href^="magnet:"]')
                    if not magnet_elem:
                        continue  # Skip results without magnet links
                    
                    magnet_uri = magnet_elem.get('href', '')
                    
                    # Try to extract size from page content
                    size = 'Unknown'
                    page_text = detail_soup.get_text(separator=' ', strip=True)
                    # Look for size patterns like "1.5 GB", "500 MB"
                    size_match = re.search(r'(\d+(?:\.\d+)?)\s*(GB|MB|TB|KB|GiB|MiB)', page_text, re.IGNORECASE)
                    if size_match:
                        size = f"{size_match.group(1)} {size_match.group(2).upper()}"
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=0,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.OTHER,
                    )
                    torrents.append(t)
                except Exception:
                    continue
            
            return torrents
        except Exception as e:
            print(f"VSTorrent search error: {e}")
            return []


class SolidTorrentsProvider(SearchProvider):
    """SolidTorrents provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="solidtorrents",
            name="SolidTorrents",
            url="https://solidtorrents.eu",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search SolidTorrents."""
        url = f"{self.info.url}/search?q={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            
            torrents = []
            
            # SolidTorrents uses h3 for titles
            # Structure: Container -> [Title Section (h3), Info Section, Action Section (Magnet)]
            items = soup.find_all('h3')
            
            for item in items:
                try:
                    name = item.get_text(strip=True)
                    if not name:
                        continue
                        
                    # Find container by going up
                    # Usually h3 -> div -> div (content) -> div (card/row)
                    container = item
                    magnet_uri = ''
                    
                    # Go up up to 5 levels to find a container that has a magnet link
                    found_magnet = False
                    curr = item
                    for _ in range(5):
                        if not curr.parent:
                            break
                        curr = curr.parent
                        magnet_elem = curr.select_one('a[href^="magnet:"]')
                        if magnet_elem:
                            magnet_uri = magnet_elem.get('href', '')
                            container = curr
                            found_magnet = True
                            break
                    
                    if not found_magnet:
                        continue
                        
                    # Description URL (usually the h3 is inside a link or has a link nearby)
                    desc_url = ''
                    link = item.find_parent('a') or item.find('a')
                    if link:
                        desc_url = link.get('href', '')
                    else:
                        # Try to find a link in the container that contains /view/ or /torrent/
                        link = container.select_one('a[href*="/view/"]') or container.select_one('a[href*="/torrent/"]')
                        if link:
                            desc_url = link.get('href', '')
                            
                    if desc_url and not desc_url.startswith('http'):
                        desc_url = self.info.url + desc_url
                        
                    # Stats
                    size = 'Unknown'
                    seeds = 0
                    peers = 0
                    
                    # Parse text content of container for stats
                    text = container.get_text(separator=' ', strip=True)
                    
                    # Size (e.g. 2.5 GB)
                    import re
                    size_match = re.search(r'(\d+(\.\d+)?\s*(GB|MB|KB|TB))', text, re.IGNORECASE)
                    if size_match:
                        size = size_match.group(1)
                    
                    # Seeds/Peers
                    # Look for numbers that might be seeds/peers
                    # Often they are in specific classes or colors, but we can't rely on that without seeing HTML
                    # Let's try to find numbers in the stats section
                    # SolidTorrents often has: Size | Date | Seeds | Leechers
                    # We can try to find all numbers and guess
                    numbers = re.findall(r'\b\d+\b', text)
                    if len(numbers) >= 2:
                        # This is risky, but better than nothing. 
                        # Usually seeds are the first integer after size/date
                        pass
                        
                    # Try to find elements with specific classes if possible
                    # But for now, let's rely on the fact that we found the item
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeds, # Hard to extract reliably without exact HTML
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"SolidTorrents search error: {e}")
            return []


class XXXClubProvider(SearchProvider):
    """XXXClub provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="xxxclub",
            name="XXXClub",
            url="https://xxxclub.to",
            specialized_category=Category.PORN,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search XXXClub."""
        from urllib.parse import quote
        url = f"{self.info.url}/torrents/search/all/{quote(query)}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Results are in ul.tsearch li (skip first li which is header)
            results = soup.select('ul.tsearch li')
            
            for result in results[1:]:  # Skip header row
                try:
                    # Get title link with details URL
                    title_link = result.select_one('a[href^="/torrents/details/"]')
                    if not title_link:
                        continue
                    
                    name = title_link.get_text(strip=True)
                    desc_path = title_link.get('href', '')
                    description_url = f"{self.info.url}{desc_path}"
                    
                    # Get info hash from the link's id attribute (e.g., #ib694d0194...)
                    link_id = title_link.get('id', '')
                    info_hash = ''
                    if link_id.startswith('#i'):
                        info_hash = link_id[2:]  # Remove '#i' prefix
                    elif link_id.startswith('i'):
                        info_hash = link_id[1:]  # Remove 'i' prefix
                    
                    # Construct magnet URI
                    magnet_uri = ''
                    if info_hash and len(info_hash) == 40:
                        magnet_uri = f"magnet:?xt=urn:btih:{info_hash}&dn={quote(name)}"
                    
                    # Get size
                    size_elem = result.select_one('span.siz')
                    size = size_elem.get_text(strip=True) if size_elem else 'Unknown'
                    
                    # Get seeders
                    seeders_elem = result.select_one('span.see')
                    seeders = 0
                    if seeders_elem:
                        try:
                            seeders = int(seeders_elem.get_text(strip=True))
                        except:
                            pass
                    
                    # Get leechers
                    leechers_elem = result.select_one('span.lee')
                    leechers = 0
                    if leechers_elem:
                        try:
                            leechers = int(leechers_elem.get_text(strip=True))
                        except:
                            pass
                    
                    # Get upload date
                    date_elem = result.select_one('span.adde')
                    upload_date = date_elem.get_text(strip=True) if date_elem else 'Unknown'
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeders,
                        peers=leechers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date=upload_date,
                        description_url=description_url,
                        magnet_uri=magnet_uri,
                        category=Category.PORN,
                    )
                    torrents.append(t)
                except Exception:
                    continue
            
            return torrents
        except Exception as e:
            print(f"XXXClub search error: {e}")
            return []


class YouplexTorrentsProvider(SearchProvider):
    """Youplex Torrents provider - working aggregator."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="youplextorrents",
            name="Youplex Torrents",
            url="https://torrents.youplex.site",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            safety_reason="Requires JavaScript - may not work",
            enabled_by_default=False,
            language="Multi",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Youplex Torrents."""
        url = f"{self.info.url}/?search={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Find all magnet links and work backwards
            for magnet in soup.select('a[href^="magnet:"]'):
                try:
                    magnet_uri = magnet.get('href', '')
                    
                    # Find container
                    row = magnet.find_parent('tr') or magnet.find_parent('div')
                    if not row:
                        continue
                    
                    # Find name
                    name_elem = row.select_one('a[href*="torrent"]') or row.find('a')
                    name = name_elem.get_text(strip=True) if name_elem else 'Unknown'
                    
                    # Extract size, seeds from text
                    import re
                    text = row.get_text(separator=' ', strip=True)
                    
                    size_match = re.search(r'(\d+(\.\d+)?\s*(GB|MB|KB|TB))', text, re.IGNORECASE)
                    size = size_match.group(1) if size_match else 'Unknown'
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=0,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=self.info.url,
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"Youplex search error: {e}")
            return []




class RarbgDumpProvider(SearchProvider):
    """RarbgDump provider - RARBG database dump."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="rarbgdump",
            name="RARBG Dump",
            url="https://rarbgdump.com",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
            language="Multi",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search RARBG Dump."""
        import re
        url = f"{self.info.url}/search/{query}/"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # RarbgDump uses magnet links with dn= parameter containing the name
            magnets = soup.select('a[href^="magnet:"]')
            
            for magnet in magnets:
                try:
                    magnet_uri = magnet.get('href', '')
                    
                    # Extract name from dn= parameter in magnet URI
                    dn_match = re.search(r'dn=([^&]+)', magnet_uri)
                    if dn_match:
                        name = dn_match.group(1).replace('+', ' ').replace('%20', ' ')
                        # URL decode
                        from urllib.parse import unquote
                        name = unquote(name)
                    else:
                        continue  # Skip if no name
                    
                    # Try to find size from parent container
                    size = 'Unknown'
                    # Fix: Find the specific row for this torrent instead of going up 5 levels
                    # Going up 5 levels often hits the main table/container, causing find() to match the first result's size for everyone
                    row = magnet.find_parent('tr')
                    
                    # If not a table row provided, try grandparent (likely container of the item)
                    if not row and magnet.parent and magnet.parent.parent:
                        row = magnet.parent.parent
                    
                    if row:
                        text = row.get_text(separator=' ', strip=True)
                        size_match = re.search(r'(\d+(\.\d+)?\s*(GB|MB|KB|TB))', text, re.IGNORECASE)
                        if size_match:
                            size = size_match.group(1)
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=-1,  # -1 indicates unknown (archive data)
                        peers=-1,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=self.info.url,
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"RARBG Dump search error: {e}")
            return []


class SnowflProvider(SearchProvider):
    """Snowfl provider - torrent meta-search."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="snowfl",
            name="Snowfl",
            url="https://snowfl.com",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,  # Requires JavaScript typically
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Snowfl - note: may require API access."""
        # Snowfl typically requires JavaScript, return empty for now
        return []


class ExtraTorrentProvider(SearchProvider):
    """ExtraTorrent provider with multiple mirror fallback support."""
    
    # List of known ExtraTorrent mirrors (ordered by reliability)
    MIRRORS = [
        "https://ext.to",
        "https://extratorrent.st", 
        "https://extratorrents.ch",
        "https://extratorrent.si",
        "https://extratorrent.is",
        "https://extratorrent.unblockit.mov",
    ]
    
    def __init__(self):
        super().__init__()
        self._working_mirror = None
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="extratorrent",
            name="ExtraTorrent",
            url=self._working_mirror or self.MIRRORS[0],
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.UNSAFE,
            safety_reason="Often blocked by ISP - use VPN for best results",
            enabled_by_default=False,  # Often blocked
        )
    
    def _try_mirror(self, mirror: str, query: str) -> str:
        """Try to fetch search results from a specific mirror."""
        import re
        from urllib.parse import quote
        
        # Different mirrors may have different search URL patterns
        search_patterns = [
            f"{mirror}/search/?search={quote(query)}",
            f"{mirror}/?search={quote(query)}",
            f"{mirror}/search/{quote(query)}/",
            f"{mirror}/search?q={quote(query)}",
        ]
        
        for url in search_patterns:
            try:
                html = self._get(url, timeout=10)
                if html and len(html) > 1000:  # Basic validation
                    # Check if it looks like a valid search results page
                    if 'magnet:' in html or 'torrent' in html.lower():
                        return html
            except:
                continue
        return None
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search ExtraTorrent using multiple mirrors."""
        import re
        from urllib.parse import unquote
        
        html = None
        working_mirror = None
        
        # Try each mirror until one works
        for mirror in self.MIRRORS:
            try:
                html = self._try_mirror(mirror, query)
                if html:
                    working_mirror = mirror
                    self._working_mirror = mirror
                    print(f"ExtraTorrent: Using mirror {mirror}")
                    break
            except Exception as e:
                print(f"ExtraTorrent mirror {mirror} failed: {e}")
                continue
        
        if not html:
            print("ExtraTorrent: All mirrors failed")
            return []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            seen_magnets = set()  # Avoid duplicates
            
            # Method 1: Find magnet links and work backwards to find info
            for magnet in soup.select('a[href^="magnet:"]'):
                try:
                    magnet_uri = magnet.get('href', '')
                    if not magnet_uri or magnet_uri in seen_magnets:
                        continue
                    seen_magnets.add(magnet_uri)
                    
                    # Extract name from magnet dn= parameter as fallback
                    dn_match = re.search(r'dn=([^&]+)', magnet_uri)
                    magnet_name = unquote(dn_match.group(1).replace('+', ' ')) if dn_match else None
                    
                    # Try to find the containing row/container
                    row = magnet.find_parent('tr')
                    if not row:
                        row = magnet.find_parent('div', class_=re.compile(r'(row|item|result|torrent)', re.I))
                    if not row:
                        row = magnet.find_parent('li')
                    
                    name = 'Unknown'
                    size = 'Unknown'
                    seeders = 0
                    leechers = 0
                    
                    if row:
                        # Try different name selectors
                        name_elem = (
                            row.select_one('a.title') or
                            row.select_one('a[href*="/torrent/"]') or
                            row.select_one('td:first-child a') or
                            row.select_one('.torrent-name, .name, .title') or
                            row.select_one('a[title]')
                        )
                        if name_elem:
                            name = name_elem.get('title') or name_elem.get_text(strip=True)
                        
                        text = row.get_text(separator=' ', strip=True)
                        
                        # Extract size
                        size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:GB|MB|KB|TB|GiB|MiB|KiB))', text, re.IGNORECASE)
                        if size_match:
                            size = size_match.group(1)
                        
                        # Extract seeders/leechers - look for green/red numbers or S/L labels
                        # Pattern: "123 S" or "S: 123" or just numbers in seed/leech columns
                        seed_match = re.search(r'(?:S(?:eed(?:er)?s?)?[:\s]*)?(\d+)\s*(?:S|seed)', text, re.IGNORECASE)
                        if seed_match:
                            seeders = int(seed_match.group(1))
                        else:
                            # Try finding numbers that could be seeds
                            cols = row.find_all('td')
                            if len(cols) >= 4:
                                try:
                                    # Typically: Name, Size, Seeds, Leechers or similar
                                    seeders = int(cols[-2].get_text(strip=True).replace(',', ''))
                                    leechers = int(cols[-1].get_text(strip=True).replace(',', ''))
                                except:
                                    pass
                    
                    # Use magnet name as fallback
                    if name == 'Unknown' and magnet_name:
                        name = magnet_name
                    
                    # Skip if we still don't have a name
                    if name == 'Unknown':
                        continue
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeders,
                        peers=leechers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=working_mirror or self.MIRRORS[0],
                        magnet_uri=magnet_uri,
                        category=category if category != Category.ALL else Category.ALL,
            language="Multi",
                    )
                    torrents.append(t)
                except Exception as e:
                    continue
            
            # Method 2: If no magnets found, try looking for torrent links
            if not torrents:
                for link in soup.select('a[href*="/torrent/"]'):
                    try:
                        name = link.get_text(strip=True)
                        if not name or len(name) < 3:
                            continue
                        
                        href = link.get('href', '')
                        desc_url = href if href.startswith('http') else (working_mirror + href)
                        
                        # Try to get details from parent row
                        row = link.find_parent('tr') or link.find_parent('div')
                        size = 'Unknown'
                        if row:
                            text = row.get_text(separator=' ')
                            size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:GB|MB|KB|TB))', text, re.IGNORECASE)
                            if size_match:
                                size = size_match.group(1)
                        
                        t = Torrent(
                            name=name,
                            size=size,
                            seeders=-1,  # Unknown - would need to fetch detail page
                            peers=-1,
                            provider_id=self.info.id,
                            provider_name=self.info.name,
                            upload_date='Unknown',
                            description_url=desc_url,
                            magnet_uri='',  # Would need detail page
                            category=category if category != Category.ALL else Category.ALL,
                        )
                        torrents.append(t)
                    except:
                        continue
            
            print(f"ExtraTorrent: Found {len(torrents)} results")
            return torrents
            
        except Exception as e:
            print(f"ExtraTorrent search error: {e}")
            import traceback
            traceback.print_exc()
            return []


class LeetxProvider(SearchProvider):
    """1337x provider (often blocked)."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="1337x",
            name="1337x",
            url="https://1337x.to",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.UNSAFE,
            safety_reason="May have aggressive ads",
            enabled_by_default=False,  # Often blocked by ISPs
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search 1337x."""
        url = f"{self.info.url}/search/{query}/1/"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # 1337x lists results by row, need to get detail page for magnet
            rows = soup.select('tr')
            
            for row in rows:
                try:
                    name_link = row.select_one('a[href*="/torrent/"]')
                    if not name_link:
                        continue
                    
                    name = name_link.get_text(strip=True)
                    desc_url = self.info.url + name_link.get('href', '')
                    
                    # Get size and seeds from columns
                    cols = row.find_all('td')
                    if len(cols) < 5:
                        continue
                    
                    seeds = 0
                    peers = 0
                    size = 'Unknown'
                    
                    try:
                        seeds = int(cols[1].get_text(strip=True))
                        peers = int(cols[2].get_text(strip=True))
                        size = cols[4].get_text(strip=True).split('\n')[0]
                    except:
                        pass
                    
                    # Note: 1337x requires visiting detail page for magnet
                    # For now, we'll skip magnet and let user click through
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeds,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri='',  # Would need to fetch detail page
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"1337x search error: {e}")
            return []


class TorLockProvider(SearchProvider):
    """TorLock provider - verified torrents."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="torlock",
            name="TorLock",
            url="https://www.torlock.com",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search TorLock."""
        import re
        url = f"{self.info.url}/all/torrents/{query}.html"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            rows = soup.select('tr')
            for row in rows:
                try:
                    link = row.select_one('a[href*="/torrent/"]')
                    if not link:
                        continue
                    
                    name = link.get_text(strip=True)
                    desc_url = self.info.url + link.get('href', '')
                    
                    cols = row.find_all('td')
                    size = cols[2].get_text(strip=True) if len(cols) > 2 else 'Unknown'
                    seeds = 0
                    peers = 0
                    try:
                        seeds = int(cols[3].get_text(strip=True)) if len(cols) > 3 else 0
                        peers = int(cols[4].get_text(strip=True)) if len(cols) > 4 else 0
                    except:
                        pass
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeds,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri='',
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"TorLock search error: {e}")
            return []


class GloTorrentsProvider(SearchProvider):
    """GloTorrents provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="glotorrents",
            name="GloTorrents",
            url="https://glodls.to",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.UNSAFE,
            safety_reason="May have aggressive ads",
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search GloTorrents."""
        import re
        url = f"{self.info.url}/search_results.php?search={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            for magnet in soup.select('a[href^="magnet:"]'):
                try:
                    magnet_uri = magnet.get('href', '')
                    
                    dn_match = re.search(r'dn=([^&]+)', magnet_uri)
                    if dn_match:
                        from urllib.parse import unquote
                        name = unquote(dn_match.group(1).replace('+', ' '))
                    else:
                        continue
                    
                    t = Torrent(
                        name=name,
                        size='Unknown',
                        seeders=0,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=self.info.url,
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"GloTorrents search error: {e}")
            return []


class TorrentDownloadsProvider(SearchProvider):
    """TorrentDownloads provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="torrentdownloads",
            name="TorrentDownloads",
            url="https://www.torrentdownloads.pro",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.UNSAFE,
            safety_reason="May be blocked",
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search TorrentDownloads."""
        url = f"{self.info.url}/search/?search={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            rows = soup.select('div.grey_bar, tr')
            for row in rows:
                try:
                    link = row.select_one('a[href*="/torrent/"]')
                    if not link:
                        continue
                    
                    name = link.get_text(strip=True)
                    desc_url = self.info.url + link.get('href', '')
                    
                    t = Torrent(
                        name=name,
                        size='Unknown',
                        seeders=0,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri='',
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"TorrentDownloads search error: {e}")
            return []


class ZooqleProvider(SearchProvider):
    """Zooqle provider (often down)."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="zooqle",
            name="Zooqle",
            url="https://zooqle.com",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            safety_reason="Site may be offline",
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Zooqle."""
        url = f"{self.info.url}/search?q={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            for row in soup.select('tr'):
                try:
                    link = row.select_one('a[href*="/"]')
                    magnet = row.select_one('a[href^="magnet:"]')
                    
                    if not link:
                        continue
                    
                    name = link.get_text(strip=True)
                    magnet_uri = magnet.get('href', '') if magnet else ''
                    
                    t = Torrent(
                        name=name,
                        size='Unknown',
                        seeders=0,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=self.info.url,
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"Zooqle search error: {e}")
            return []


class Torrentz2Provider(SearchProvider):
    """Torrentz2 meta-search provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="torrentz2",
            name="Torrentz2",
            url="https://torrentz2.nz",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Torrentz2."""
        import re
        url = f"{self.info.url}/search?q={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            for item in soup.select('dl, div.result'):
                try:
                    link = item.select_one('a')
                    if not link:
                        continue
                    
                    name = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    # Try to extract hash from URL
                    hash_match = re.search(r'([a-fA-F0-9]{40})', href)
                    magnet_uri = ''
                    if hash_match:
                        infohash = hash_match.group(1)
                        magnet_uri = f"magnet:?xt=urn:btih:{infohash}&dn={name}"
                    
                    t = Torrent(
                        name=name,
                        size='Unknown',
                        seeders=0,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=self.info.url + href,
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"Torrentz2 search error: {e}")
            return []


class LimeTorrentsProvider2(SearchProvider):
    """LimeTorrents provider with multiple mirror support."""
    
    # List of known mirrors to try
    MIRRORS = [
        "https://www.limetorrents.pro",
        "https://www.limetorrents.lol",
        "https://limetorrents.unblockit.black",
        "https://www.limetorrents.to",
        "https://limetorrent.cc",
        "https://limetorrents.co",
        "https://limetor.com",
    ]
    
    working_mirror = None
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="limetorrents",
            name="LimeTorrents",
            url="https://www.limetorrents.pro",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.UNSAFE,
            safety_reason="May have popups",
            enabled_by_default=False,
        )
    
    def _check_mirror(self, mirror, query):
        """Check if a mirror is working."""
        try:
            url = f"{mirror}/search/all/{query}//1"
            resp = self.session.get(url, timeout=10, verify=False)
            if resp.status_code == 200 and len(resp.content) > 5000:
                return mirror, resp.text
        except:
            pass
        return None, None
    
    def search(self, query: str, category: Category, page: int = 1) -> List[Torrent]:
        """Search LimeTorrents with mirror racing."""
        import re
        import concurrent.futures
        
        html = None
        active_mirror = None
        
        # Try cached working mirror first
        if self.working_mirror:
            try:
                url = f"{self.working_mirror}/search/all/{query}//{page}"
                html = self._get(url, timeout=8)
                if html and len(html) > 5000:
                    active_mirror = self.working_mirror
                else:
                    self.working_mirror = None
            except:
                self.working_mirror = None
        
        # If no working mirror, race all mirrors
        if not active_mirror:
            with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
                future_to_mirror = {executor.submit(self._check_mirror, m, query): m for m in self.MIRRORS}
                
                for future in concurrent.futures.as_completed(future_to_mirror):
                    mirror, result_html = future.result()
                    if result_html:
                        self.working_mirror = mirror
                        active_mirror = mirror
                        if page > 1:
                            try:
                                html = self._get(f"{mirror}/search/all/{query}//{page}", timeout=8)
                            except:
                                html = None
                        else:
                            html = result_html
                        break
        
        if not html:
            print("LimeTorrents: No working mirror found")
            return []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            pending_magnets = []
            
            # Skip first 5 rows (header/navigation)
            rows = soup.find_all('tr')[5:]
            
            for row in rows:
                try:
                    cols = row.find_all('td')
                    if len(cols) < 5:
                        continue
                    
                    # Name - from first column, last link
                    name_links = cols[0].find_all('a')
                    if not name_links:
                        continue
                    
                    name = cols[0].get_text(strip=True)
                    detail_url = active_mirror + name_links[-1].get('href', '')
                    
                    # Date and Category - from second column
                    date_cat = cols[1].get_text(strip=True)
                    date_parts = date_cat.split('-')
                    date = date_parts[0].strip() if date_parts else 'Unknown'
                    cat = date_cat.split('in')[-1].strip() if 'in' in date_cat else ''
                    
                    # Size - from third column
                    size = cols[2].get_text(strip=True)
                    
                    # Seeders and Leechers
                    try:
                        seeders = int(cols[3].get_text(strip=True).replace(',', ''))
                    except:
                        seeders = 0
                    
                    try:
                        peers = int(cols[4].get_text(strip=True).replace(',', ''))
                    except:
                        peers = 0
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeders,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date=date,
                        description_url=detail_url,
                        magnet_uri='',  # Will fetch from detail page
                        category=Category.ALL,
                    )
                    torrents.append(t)
                    pending_magnets.append((len(torrents) - 1, detail_url))
                    
                except Exception as e:
                    continue
            
            # Fetch magnet links from detail pages (first 15 only)
            if pending_magnets:
                self._fetch_magnets(torrents, pending_magnets[:15])
            
            print(f"LimeTorrents: Found {len(torrents)} results from {active_mirror}")
            return torrents
            
        except Exception as e:
            print(f"LimeTorrents search error: {e}")
            return []
    
    def _fetch_magnets(self, torrents, pending):
        """Fetch magnet links from detail pages in parallel."""
        import concurrent.futures
        import re
        
        def fetch_one(idx, url):
            try:
                html = self._get(url, timeout=8)
                if not html:
                    return idx, None
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find magnet link - LimeTorrents uses class="csprite_dltorrent"
                links = soup.find_all('a', class_='csprite_dltorrent')
                for link in links:
                    href = link.get('href', '')
                    if href.startswith('magnet:'):
                        return idx, href
                
                # Fallback: find any magnet link
                magnet = soup.select_one('a[href^="magnet:"]')
                if magnet:
                    return idx, magnet.get('href', '')
                    
            except:
                pass
            return idx, None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_one, idx, url) for idx, url in pending]
            for future in concurrent.futures.as_completed(futures):
                idx, magnet = future.result()
                if magnet:
                    torrents[idx].magnet_uri = magnet


class RuTrackerProvider(SearchProvider):
    """RuTracker provider (Russian, often blocked)."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="rutracker",
            name="RuTracker",
            url="https://rutracker.org",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            safety_reason="May be blocked, requires registration",
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search RuTracker - returns empty as requires login."""
        # RuTracker requires login to search
        return []


class BTSceneProvider(SearchProvider):
    """BTScene provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="btscene",
            name="BTScene",
            url="https://btscene.eu",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.UNSAFE,
            safety_reason="May have ads",
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search BTScene."""
        url = f"{self.info.url}/?q={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            for magnet in soup.select('a[href^="magnet:"]'):
                try:
                    import re
                    magnet_uri = magnet.get('href', '')
                    
                    dn_match = re.search(r'dn=([^&]+)', magnet_uri)
                    if dn_match:
                        from urllib.parse import unquote
                        name = unquote(dn_match.group(1).replace('+', ' '))
                    else:
                        continue
                    
                    t = Torrent(
                        name=name,
                        size='Unknown',
                        seeders=0,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=self.info.url,
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"BTScene search error: {e}")
            return []


class TorrentFunkProvider(SearchProvider):
    """TorrentFunk provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="torrentfunk",
            name="TorrentFunk",
            url="https://www.torrentfunk.com",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search TorrentFunk."""
        url = f"{self.info.url}/all/torrents/{query}.html"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            rows = soup.select('tr.tmain, tr.tlight')
            for row in rows:
                try:
                    link = row.select_one('a.torrent')
                    if not link:
                        continue
                    
                    name = link.get_text(strip=True)
                    desc_url = self.info.url + link.get('href', '')
                    
                    cols = row.find_all('td')
                    size = cols[1].get_text(strip=True) if len(cols) > 1 else 'Unknown'
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=0,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri='',
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"TorrentFunk search error: {e}")
            return []


class DemonoidProvider(SearchProvider):
    """Demonoid provider (classic tracker)."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="demonoid",
            name="Demonoid",
            url="https://www.demonoid.is",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            safety_reason="Classic tracker, may be down",
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Demonoid."""
        url = f"{self.info.url}/files/?query={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            for row in soup.select('tr'):
                try:
                    link = row.select_one('a[href*="/files/details/"]')
                    if not link:
                        continue
                    
                    name = link.get_text(strip=True)
                    desc_url = self.info.url + link.get('href', '')
                    
                    t = Torrent(
                        name=name,
                        size='Unknown',
                        seeders=0,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri='',
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            return []



class IsoHuntProvider(SearchProvider):
    """isoHunt provider (clone)."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="isohunt",
            name="isoHunt",
            url="https://isohunts.to",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.UNSAFE,
            safety_reason="Site requires JavaScript - Magnet links not accessible without browser automation",
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search isoHunt."""
        url = f"{self.info.url}/torrents/?ihq={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Find the main listings table
            tables = soup.find_all('table')
            if not tables:
                return []
                
            # Usually the relevant table is one of the first few
            rows = tables[0].find_all('tr')
            if not rows and len(tables) > 1:
                rows = tables[1].find_all('tr')
            
            if not rows:
                return []
            
            for row in rows[1:]: # Skip header
                try:
                    cols = row.find_all('td')
                    if len(cols) < 6:
                        continue
                    
                    # Title and Link (Col 1 - index 1)
                    # Relaxed selector: just get the first link in the second column
                    link_tag = cols[1].find('a')
                    if not link_tag:
                        # Try finding inside a div or spans
                        link_tag = cols[1].select_one('a')
                    
                    if not link_tag:
                        continue
                        
                    name = link_tag.get_text(strip=True)
                    rel_href = link_tag.get('href', '')
                    if not rel_href: continue
                    
                    # Proper URL joining
                    from urllib.parse import urljoin
                    desc_url = urljoin(self.info.url + '/', rel_href)
                    
                    # Size (Col 5 - index 5)
                    size = cols[5].get_text(strip=True)
                    
                    # Seeds (Col 6 - index 6)
                    # "08191" might be formatting issue. Just extract first number.
                    s_text = cols[6].get_text(strip=True)
                    
                    # Clean up weird spacing/newlines
                    s_cleaned = "".join(s_text.split())
                    
                    # Heuristic: if it looks like "019" it might be smashed 0 19
                    # Let's just try to grab digits.
                    seeders = 0
                    peers = 0
                    
                    import re
                    # Try to separate by space if possible
                    nums = re.findall(r'\d+', s_text)
                    if nums:
                        seeders = int(nums[0])
                    
                    # Peers/Leech (Col 7 - index 7)
                    if len(cols) > 7:
                        l_text = cols[7].get_text(strip=True)
                        p_nums = re.findall(r'\d+', l_text)
                        if p_nums:
                            peers = int(p_nums[0])
                    
                    # Fetch magnet (still needed as list doesn't have it)
                    magnet_uri = ""
                    try:
                         # Timeout short to avoid hanging
                         detail_html = self._get(desc_url)
                         if detail_html:
                             d_soup = BeautifulSoup(detail_html, 'html.parser')
                             # Look for magnet link
                             mag_link = d_soup.select_one('a[href^="magnet:"]')
                             if mag_link:
                                 magnet_uri = mag_link['href']
                                 
                                 # Also try to get accurate seeds/size from detail page if possible?
                                 # Usually detail page is better.
                    except:
                        pass
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeders,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except Exception as e:
                    continue
            
            return torrents
        except Exception as e:
            print(f"isoHunt search error: {e}")
            return []


class MagnetDLProvider(SearchProvider):
    """MagnetDL provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="magnetdl",
            name="MagnetDL",
            url="https://magnetdl.pro",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search MagnetDL."""
        import re
        # MagnetDL Pro uses search parameter
        url = f"{self.info.url}/search?q={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            for row in soup.select('tr'):
                try:
                    # Debug
                    # if len(torrents) == 0: print(row.prettify()[:500])
                    
                    # MagnetDL Pro Column Mapping:
                    # 0: Magnet
                    # 1: Name
                    # 2: Age
                    # 3: Category
                    # 4: Size
                    # 5: Seeds
                    # 6: Leechers
                    
                    magnet = row.select_one('a[href^="magnet:"]')
                    if not magnet:
                        continue
                    
                    magnet_uri = magnet.get('href', '')
                    
                    cols = row.find_all('td')
                    if len(cols) < 7:
                        continue

                    # Name in col 1 - Text appears to be outside the anchor tag or requires full cell text
                    name = cols[1].get_text(strip=True)
                    if not name:
                        name = 'Unknown'
                    
                    # Size - extract just the size value, not extra text
                    size_raw = cols[4].get_text(strip=True)
                    size = 'Unknown'
                    
                    # Try to extract standard size pattern (e.g., "1.5 GB", "75GB")
                    size_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(GB|MB|KB|TB|GiB|MiB|B)', size_raw, re.I)
                    if size_match:
                        # Extract number and unit separately to format decimal places
                        num_part = size_match.group(1).replace(',', '.')
                        unit = size_match.group(2)
                        try:
                            num_val = float(num_part)
                            # Limit to 2 decimal places for clean display
                            if num_val == int(num_val):
                                size = f"{int(num_val)} {unit}"
                            else:
                                size = f"{num_val:.2f} {unit}"
                        except:
                            size = size_match.group(0).strip()
                    else:
                        # Try to extract just numeric value (may be raw bytes or missing unit)
                        num_match = re.search(r'^([\d.,]+)$', size_raw.strip())
                        if num_match:
                            try:
                                # Parse the numeric value
                                num_str = num_match.group(1).replace(',', '.')
                                num_val = float(num_str)
                                
                                # If value is large enough to be bytes, convert
                                if num_val > 1073741824:  # > 1GB in bytes
                                    size = f"{num_val / 1073741824:.2f} GB"
                                elif num_val > 1048576:  # > 1MB in bytes
                                    size = f"{num_val / 1048576:.2f} MB"
                                elif num_val > 1024:  # > 1KB in bytes
                                    size = f"{num_val / 1024:.2f} KB"
                                elif num_val > 100:
                                    # Likely already in GB, just add unit
                                    size = f"{num_val:.0f} GB"
                                else:
                                    # Likely already in GB with decimals
                                    size = f"{num_val:.2f} GB"
                            except:
                                size = size_raw if size_raw else 'Unknown'
                        else:
                            size = size_raw if size_raw else 'Unknown'
                    
                    seeds = 0
                    peers = 0
                    try:
                        seeds = int(cols[5].get_text(strip=True))
                        peers = int(cols[6].get_text(strip=True))
                    except:
                        pass
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeds,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=self.info.url,
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"MagnetDL search error: {e}")
            return []


class YifyProvider(SearchProvider):
    """YIFY/YTS provider for movies."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="yify",
            name="YIFY Movies",
            url="https://yts.mx",
            specialized_category=Category.MOVIES,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search YIFY/YTS via API."""
        url = f"{self.info.url}/api/v2/list_movies.json?query_term={query}"
        
        try:
            data = self._get_json(url)
            if not data or data.get('status') != 'ok':
                return []
            
            movies = data.get('data', {}).get('movies', [])
            torrents = []
            
            for movie in movies:
                try:
                    title = movie.get('title', 'Unknown')
                    year = movie.get('year', '')
                    
                    for torrent in movie.get('torrents', []):
                        quality = torrent.get('quality', '')
                        size = torrent.get('size', 'Unknown')
                        seeds = torrent.get('seeds', 0)
                        peers = torrent.get('peers', 0)
                        hash_val = torrent.get('hash', '')
                        
                        name = f"{title} ({year}) [{quality}]"
                        magnet_uri = f"magnet:?xt=urn:btih:{hash_val}&dn={name}"
                        
                        t = Torrent(
                            name=name,
                            size=size,
                            seeders=seeds,
                            peers=peers,
                            provider_id=self.info.id,
                            provider_name=self.info.name,
                            upload_date='Unknown',
                            description_url=movie.get('url', self.info.url),
                            magnet_uri=magnet_uri,
                            category=Category.MOVIES,
                        )
                        torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"YIFY search error: {e}")
            return []


class BitSearchProvider(SearchProvider):
    """BitSearch meta-search provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="bitsearch",
            name="BitSearch",
            url="https://bitsearch.to",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search BitSearch."""
        import re
        url = f"{self.info.url}/search?q={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            for item in soup.select('li.search-result, div.search-result'):
                try:
                    link = item.select_one('a.title, h5 a')
                    magnet = item.select_one('a[href^="magnet:"]')
                    
                    if not link:
                        continue
                    
                    name = link.get_text(strip=True)
                    magnet_uri = magnet.get('href', '') if magnet else ''
                    
                    # Extract size
                    text = item.get_text(separator=' ')
                    size_match = re.search(r'(\d+(\.\d+)?\s*(GB|MB|KB|TB))', text, re.IGNORECASE)
                    size = size_match.group(1) if size_match else 'Unknown'
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=0,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=self.info.url,
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"BitSearch search error: {e}")
            return []


class AcademicTorrentsProvider(SearchProvider):
    """Academic Torrents - Legal academic/scientific content."""
    
    # Cache for the database (updated once per session)
    _cached_items = None
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="academictorrents",
            name="Academic Torrents",
            url="https://academictorrents.com",
            specialized_category=Category.OTHER,
            safety_status=SearchProviderSafetyStatus.SAFE,
            safety_reason="Legal academic content",
            enabled_by_default=True,
        )
    
    import threading
    _cache_lock = threading.Lock()

    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Academic Torrents using their XML database API with caching."""
        import xml.etree.ElementTree as ET
        import os
        import time
        import requests
        
        def log(msg):
            try:
                with open("academic_debug.log", "a") as f:
                    f.write(f"{msg}\n")
            except: pass
            
        log(f"Search started for query: '{query}'")
        
        # Access the class-level cache
        cls = self.__class__
        
        # Thread-safe cache initialization
        with cls._cache_lock:
            if cls._cached_items is None:
                for attempt in range(3):
                    try:
                        log(f"Downloading database.xml (Attempt {attempt+1})...")
                        print(f"Academic Torrents: Downloading database.xml (Attempt {attempt+1})...")
                        # Use the official database XML
                        xml_url = f"{self.info.url}/database.xml"
                        
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Accept": "application/xml,text/xml,*/*",
                        }
                        
                        response = self.session.get(xml_url, headers=headers, timeout=60, verify=False)
                        
                        if response.status_code != 200:
                            log(f"Failed to fetch database. Status: {response.status_code}")
                            print(f"Academic Torrents: Failed to fetch database. Status: {response.status_code}")
                            time.sleep(2)
                            continue
                        
                        # Parse XML
                        log(f"Parsing XML content length: {len(response.content)}")
                        root = ET.fromstring(response.content)
                        
                        items = []
                        # Pre-process all items
                        for item in root.findall('.//item'):
                            try:
                                title_elem = item.find('title')
                                if title_elem is None: continue
                                title = title_elem.text or ''
                                
                                infohash_elem = item.find('infohash')
                                if infohash_elem is None: continue
                                infohash = infohash_elem.text or ''
                                
                                size_elem = item.find('size')
                                size_bytes = int(size_elem.text) if size_elem is not None and size_elem.text else 0
                                
                                link_elem = item.find('link')
                                desc_url = link_elem.text if link_elem is not None else f"{self.info.url}/details/{infohash}"
                                
                                desc_elem = item.find('description')
                                description = desc_elem.text if desc_elem is not None else ""
                                
                                items.append({
                                    'title': title,
                                    'infohash': infohash,
                                    'size_bytes': size_bytes,
                                    'desc_url': desc_url,
                                    'description': description
                                })
                            except:
                                continue
                        
                        cls._cached_items = items
                        log(f"Cached {len(items)} items")
                        print(f"Academic Torrents: Cached {len(items)} items")
                        break # Success
                        
                    except Exception as e:
                        log(f"Cache error: {e}")
                        print(f"Academic Torrents cache error: {e}")
                        time.sleep(2)
                
                # If still None after retries
                if cls._cached_items is None:
                     return []
        
        # Perform search on cached items
        if not cls._cached_items:
            log("Cache is empty after attempt")
            return []
            
        torrents = []
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        try:
            for item in cls._cached_items:
                title = item['title']
                description = item.get('description', '') or ''
                
                # Client-side search: check title OR description
                searchable_text = (title + " " + description).lower()
                if not all(term in searchable_text for term in query_terms):
                    continue
                
                # Format size
                size_bytes = item['size_bytes']
                if size_bytes > 1073741824:
                    size = f"{size_bytes / 1073741824:.2f} GB"
                elif size_bytes > 1048576:
                    size = f"{size_bytes / 1048576:.2f} MB"
                elif size_bytes > 1024:
                    size = f"{size_bytes / 1024:.2f} KB"
                else:
                    size = f"{size_bytes} B" if size_bytes > 0 else "Unknown"
                    
                # Build magnet
                infohash = item['infohash']
                trackers = [
                    "udp://tracker.opentrackr.org:1337/announce",
                    "udp://open.stealth.si:80/announce",
                ]
                tracker_str = "&tr=".join(trackers)
                magnet_uri = f"magnet:?xt=urn:btih:{infohash}&dn={title}&tr={tracker_str}"
                
                t = Torrent(
                    name=title,
                    size=size,
                    seeders=-1,  # -1 indicates unknown/academic (not dead)
                    peers=-1,
                    provider_id=self.info.id,
                    provider_name=self.info.name,
                    upload_date='Unknown',
                    description_url=item['desc_url'],
                    magnet_uri=magnet_uri,
                    info_hash=infohash,
                    category=Category.OTHER,
                )
                torrents.append(t)
                
                if len(torrents) >= 50:
                    break
            
            log(f"Found {len(torrents)} matches for '{query}'")
            return torrents
        except Exception as e:
            log(f"Search processing error: {e}")
            print(f"Academic Torrents search processing error: {e}")
            return []


class InternetArchiveProvider(SearchProvider):
    """Internet Archive - Legal public domain content."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="internetarchive",
            name="Internet Archive",
            url="https://archive.org",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            safety_reason="Legal public domain content",
            enabled_by_default=True,  # Legal and working!
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Internet Archive via API."""
        import re
        url = f"{self.info.url}/advancedsearch.php?q={query}&fl[]=identifier,title,format,item_size&output=json&rows=50"
        
        try:
            data = self._get_json(url)
            if not data:
                return []
            
            docs = data.get('response', {}).get('docs', [])
            torrents = []
            
            for doc in docs:
                try:
                    identifier = doc.get('identifier', '')
                    title = doc.get('title', identifier)
                    
                    # Internet Archive provides torrents for items
                    # Magnet link can be constructed from identifier
                    download_url = f"{self.info.url}/download/{identifier}/{identifier}_archive.torrent"
                    desc_url = f"{self.info.url}/details/{identifier}"
                    
                    # Get size
                    size_bytes = doc.get('item_size', 0)
                    if size_bytes:
                        if size_bytes > 1073741824:
                            size = f"{size_bytes / 1073741824:.2f} GB"
                        elif size_bytes > 1048576:
                            size = f"{size_bytes / 1048576:.2f} MB"
                        else:
                            size = f"{size_bytes / 1024:.2f} KB"
                    else:
                        size = 'Unknown'
                    
                    t = Torrent(
                        name=title if isinstance(title, str) else title[0] if title else identifier,
                        size=size,
                        seeders=0,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=download_url,  # Use .torrent URL as magnet URI (Aria2 handles it)
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"Internet Archive search error: {e}")
            return []


class LibreProvider(SearchProvider):
    """Libre.fm - Open source and free content."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="libre",
            name="Libre Content",
            url="https://libre.fm",
            specialized_category=Category.MUSIC,
            safety_status=SearchProviderSafetyStatus.SAFE,
            safety_reason="Free/Libre content",
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Libre.fm - placeholder for legal music."""
        return []


class KickAssTorrentsProvider(SearchProvider):
    """KickAss Torrents (KAT) provider with multiple mirrors.
    
    Based on Torrent-Api-py implementation (https://github.com/Ryuk-me/Torrent-Api-py)
    which uses https://kickasstorrents.to as the primary source.
    """
    
    # Updated mirrors - kickass.cm verified working December 2024
    MIRRORS = [
        "https://kickass.cm",           # VERIFIED WORKING - returns results
        "https://kickasstorrents.to",   # Primary - used by Torrent-Api-py
        "https://kickass.sx",
        "https://kat.am",
        "https://kickass.ws",
        "https://kickasstorrents.ws",
        "https://kkat.net",
        "https://thekat.info",
        "https://katcr.to",
        "https://kat.rip",
        "https://kickasstorrents.bz",
        "https://kickasshydra.net",
        "https://kickass.torrentbay.to",
        "https://kickass.torrentbay.st",
    ]
    
    working_mirror = None
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="kickasstorrents",
            name="KickAss Torrents",
            url="https://kickasstorrents.to",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.UNSAFE,
            safety_reason="May have aggressive ads",
            enabled_by_default=True,
        )
    
    def _check_mirror(self, mirror, query):
        """Check if a mirror is working by performing a quick search."""
        try:
            url = f"{mirror}/usearch/{query}/"
            # Fast timeout for check
            # Use improved headers to look like a browser
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Connection": "keep-alive"
            }
            resp = self.session.get(url, headers=headers, timeout=10, verify=False)
            print(f"DEBUG: Mirror {mirror} returned {resp.status_code}, len={len(resp.content)}")
            if resp.status_code == 200 and len(resp.content) > 5000:
                # Basic check for 'Not Found' or blocking pages
                if "No torrents found" in resp.text:
                    # Valid page but no results, maybe query issue? Still 'working'
                    return mirror, resp.text
                return mirror, resp.text
        except Exception as e:
            print(f"DEBUG: Mirror {mirror} failed: {e}")
            pass
        return None, None

    def search(self, query: str, category: Category, page: int = 1) -> List[Torrent]:
        """Search KickAss Torrents using parallel mirror racing."""
        import re
        import concurrent.futures
        
        html = None
        active_mirror = None
        
        # 1. Try cached working mirror first
        if self.working_mirror:
            try:
                url = f"{self.working_mirror}/usearch/{query}/{page}/"
                html = self._get(url, timeout=8)
                if html and len(html) > 5000:
                    active_mirror = self.working_mirror
                else:
                    self.working_mirror = None # Reset
            except:
                self.working_mirror = None
        
        # 2. If no working mirror, RACE all mirrors
        if not active_mirror:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_mirror = {executor.submit(self._check_mirror, m, query): m for m in self.MIRRORS}
                
                for future in concurrent.futures.as_completed(future_to_mirror):
                    mirror, result_html = future.result()
                    if result_html:
                        self.working_mirror = mirror
                        active_mirror = mirror
                        if page > 1:
                            # Re-fetch correct page
                            try:
                                html = self._get(f"{mirror}/usearch/{query}/{page}/", timeout=8)
                            except:
                                html = None
                        else:
                            html = result_html
                        break
            
            if not active_mirror:
                return []

        # 3. Parse Results from the Winning Mirror
        soup = BeautifulSoup(html, 'html.parser')
        torrents = []
        
        try:
            rows = soup.select('tr.odd, tr.even, tr[id^="torrent"], table.data tr:not(.firstr)')
            
            # List of items needing magnet fetch: (index_in_torrents, desc_url)
            pending_magnets = []
            
            for row in rows:
                try:
                    # Title
                    title_link = row.select_one('a.cellMainLink, a.torrentname, td.torrentnameCell a, a[href*="/torrent/"]')
                    if not title_link: continue
                    
                    name = title_link.get_text(strip=True)
                    href = title_link.get('href', '')
                    # Use official URL for display, regardless of which mirror scraped it
                    desc_url = self.info.url + href if not href.startswith('http') else href
                    
                    # Magnet
                    magnet_uri = ''
                    magnet = row.select_one('a[href^="magnet:"]')
                    if magnet:
                        magnet_uri = magnet.get('href', '')
                    else:
                        # Backup: InfoHash -> Magnet
                        for a in row.find_all('a'):
                            link_href = a.get('href', '')
                            # Look for 40 char hex hash
                            hash_match = re.search(r'([a-fA-F0-9]{40})', link_href or '')
                            if hash_match:
                                infohash = hash_match.group(1)
                                from urllib.parse import quote
                                encoded_name = quote(name)
                                trackers = [
                                    "udp://tracker.opentrackr.org:1337/announce",
                                    "udp://open.stealth.si:80/announce",
                                    "udp://tracker.openbittorrent.com:80/announce",
                                    "udp://tracker.torrent.eu.org:451/announce",
                                    "udp://explodie.org:6969/announce",
                                    "udp://tracker.moeking.me:6969/announce",
                                    "udp://p4p.arenabg.com:1337/announce",
                                    "udp://9.rarbg.me:2970/announce",
                                    "udp://9.rarbg.to:2710/announce",
                                    "udp://tracker.tiny-vps.com:6969/announce",
                                ]
                                tr_params = "".join([f"&tr={quote(t)}" for t in trackers])
                                magnet_uri = f"magnet:?xt=urn:btih:{infohash}&dn={encoded_name}{tr_params}"
                                break
                    
                    # Stats - Using column indices like Torrent-Api-py:
                    # col[1]=size, col[2]=uploader, col[3]=date, col[4]=seeders, col[5]=leechers
                    cols = row.find_all('td')
                    size = 'Unknown'
                    seeds = 0
                    peers = 0
                    upload_date = 'Unknown'
                    
                    # Try column-based extraction (Torrent-Api-py approach)
                    if len(cols) >= 6:
                        size = cols[1].get_text(strip=True) if len(cols) > 1 else 'Unknown'
                        upload_date = cols[3].get_text(strip=True) if len(cols) > 3 else 'Unknown'
                        try:
                            seeds = int(cols[4].get_text(strip=True).replace(',', ''))
                        except:
                            seeds = 0
                        try:
                            peers = int(cols[5].get_text(strip=True).replace(',', ''))
                        except:
                            peers = 0
                    else:
                        # Fallback: search by class/pattern
                        for col in cols:
                            text = col.get_text(strip=True)
                            if re.search(r'\d+(\.\d+)?\s*(GB|MB|KB|TB)', text, re.IGNORECASE):
                                size = text
                            if col.get('class') and 'green' in str(col.get('class')):
                                try: seeds = int(text.replace(',', ''))
                                except: pass
                            if col.get('class') and 'red' in str(col.get('class')):
                                try: peers = int(text.replace(',', ''))
                                except: pass

                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeds,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date=upload_date,
                        description_url=desc_url,
                        magnet_uri=magnet_uri, # May be empty initially
                        category=Category.ALL,
                    )
                    torrents.append(t)
                    
                    if not magnet_uri:
                        pending_magnets.append((len(torrents)-1, desc_url))
                        
                except: continue
            
            # 4. Parallel Batch Fetch for missing magnets (Limit 15 to be safe)
            if pending_magnets:
                to_fetch = pending_magnets[:15] # Fetch top 15 missing only
                
                def fetch_magnet(url):
                    try:
                        h = self._get(url, timeout=5)
                        if h:
                            s = BeautifulSoup(h, 'html.parser')
                            m = s.select_one('a[href^="magnet:"]')
                            return m['href'] if m else None
                    except: return None
                    return None

                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    future_to_idx = {executor.submit(fetch_magnet, url): idx for idx, url in to_fetch}
                    for future in concurrent.futures.as_completed(future_to_idx):
                        idx = future_to_idx[future]
                        mag = future.result()
                        if mag:
                            torrents[idx].magnet_uri = mag
                            
            return torrents
            
        except Exception as e:
            print(f"KickAss parsing error: {e}")
            return []




class NNMClubProvider(SearchProvider):
    """NNM-Club - Popular Russian tracker."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="nnmclub",
            name="NNM-Club",
            url="https://nnmclub.to",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,  # Confirmed accessible
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search NNM-Club."""
        # NNM uses cp1251, query needs to be encoded
        try:
            encoded_query = query.encode('cp1251').decode('latin1') # Hack to pass bytes
            # Actually requests handles param encoding if we pass dict, but here we construct URL
            # Let's trust requests to handle URL encoding
        except:
            encoded_query = query
        
        url = f"{self.info.url}/forum/tracker.php?nm={query}"
        
        try:
            r = self.session.get(url, verify=False, timeout=10)
            # manually set encoding
            if r.encoding == 'ISO-8859-1':
                r.encoding = 'windows-1251'
                
            soup = BeautifulSoup(r.text, 'html.parser')
            torrents = []
            
            # Rows are usually class prow1 or prow2
            rows = soup.select('tr.prow1, tr.prow2')
            
            for row in rows:
                try:

                    # Title matches viewtopic.php link
                    # The category link is usually first, we want the topic link
                    title_link = row.select_one('a[href^="viewtopic.php"]')
                    if not title_link:
                        # Fallback
                        title_link = row.select_one('a.genmed, a.gen')
                        if not title_link or 'tracker.php' in title_link.get('href', ''):
                             continue
                    
                    name = title_link.get_text(strip=True)
                    href = title_link.get('href', '')
                    # Fix relative path
                    if href.startswith('./'): href = href[2:]
                    desc_url = self.info.url + '/forum/' + href
                    
                    # Size - NNM-Club stores size in TD with class gensmall
                    # Format: raw_bytes human_readable (e.g., "4727476 4.51 MB")
                    import re
                    
                    def extract_int(elem):
                        if not elem: return 0
                        txt = elem.get_text(strip=True)
                        try:
                            m = re.search(r'\d+', txt)
                            return int(m.group(0)) if m else 0
                        except:
                            return 0

                    seed_span = row.select_one('.seedmed, .seed, b.seedmed') 
                    seeds = extract_int(seed_span)

                    leech_span = row.select_one('.leechmed, .leech, b.leechmed')
                    peers = extract_int(leech_span)
                    
                    # Size is in a td.gensmall containing <u>bytes</u> and human_readable
                    # The <u> tag contains size in bytes, we'll convert it to human-readable
                    size = 'Unknown'
                    tds = row.find_all('td')
                    for td in tds:
                        # Look for <u> tag with size in bytes
                        u_elem = td.find('u')
                        if u_elem:
                            try:
                                size_bytes = int(u_elem.get_text(strip=True))
                                # Convert to human-readable
                                if size_bytes > 1073741824:  # GB
                                    size = f"{size_bytes / 1073741824:.2f} GB"
                                elif size_bytes > 1048576:  # MB
                                    size = f"{size_bytes / 1048576:.2f} MB"
                                elif size_bytes > 1024:  # KB
                                    size = f"{size_bytes / 1024:.2f} KB"
                                else:
                                    size = f"{size_bytes} B"
                                # Only use first valid size (TD[5]), skip date TD
                                if 'gensmall' in str(td.get('class', [])) and 'title' in td.attrs:
                                    break
                            except:
                                pass
                    
                    # Magnet - NNM often requires login for magnet, or it's in a specific icon
                    # Sometimes there is a magnet link in the row
                    magnet = row.select_one('a[href^="magnet:"]')
                    magnet_uri = magnet.get('href', '') if magnet else ''
                    
                    # If no magnet, extracting from download ID if possible
                    # But without magnet, we can't download.
                    # We will try to find a magnet.
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeds,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            
            return torrents
        except Exception as e:
            print(f"NNM-Club search error: {e}")
            return []


class BTSearchProvider(SearchProvider):
    """BTSearch - BitTorrent Search Engine."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="btsearch",
            name="BTSearch",
            url="https://www.btsearch.love",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False, # Experimental
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        url = f"{self.info.url}/en/search?q={query}"
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Need to identify proper structure. 
            # Based on typical aggregator sites
            items = soup.select('div.search-item, div.result')
            
            for item in items:
                try:
                    name_el = item.select_one('h3 a, a.title')
                    if not name_el: continue
                    name = name_el.get_text(strip=True)
                    
                    magnet = item.select_one('a[href^="magnet:"]')
                    magnet_uri = magnet.get('href', '') if magnet else ''
                    
                    size_el = item.select_one('.size')
                    size = size_el.get_text(strip=True) if size_el else 'Unknown'
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=0,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=self.info.url,
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except:
                    continue
            return torrents
        except Exception as e:
            print(f"BTSearch search error: {e}")
            return []


class KinozalProvider(SearchProvider):
    """Kinozal.tv - Russian movie tracker."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="kinozal",
            name="Kinozal",
            url="https://kinozal.tv",
            specialized_category=Category.MOVIES,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        url = f"{self.info.url}/browse.php?s={query}"
        try:
            r = self.session.get(url, verify=False)
            if r.encoding == 'ISO-8859-1':
                r.encoding = 'windows-1251'
                
            soup = BeautifulSoup(r.text, 'html.parser')
            torrents = []
            
            rows = soup.select('tr.bg')
            for row in rows:
                try:
                    nametd = row.select_one('td.nam')
                    if not nametd: continue
                    
                    name = nametd.get_text(strip=True)
                    
                    # Size is usually index 3 or 4
                    cols = row.find_all('td')
                    size = cols[3].get_text(strip=True) if len(cols) > 3 else 'Unknown'
                    seeds = int(cols[4].get_text(strip=True)) if len(cols) > 4 else 0
                    
                    # Finding magnet logic requires detail page usually
                    # Placeholder
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeds,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=self.info.url,
                        magnet_uri='', # Requires detail scraping
                        category=Category.MOVIES,
                    )
                    torrents.append(t)
                except:
                    continue
            return torrents
        except Exception as e:
            print(f"Kinozal search error: {e}")
            return []


class RutrackerProvider(SearchProvider):
    """Rutracker - dummy provider (needs login)."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="rutracker_ru",
            name="RuTracker (RU)",
            url="https://rutracker.org",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            safety_reason="Requires Login",
            enabled_by_default=False,
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        return []


class ByRutorProvider(SearchProvider):
    """ByRutor - Russian game torrents site (Repacks, PC Games)."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="byrutor",
            name="ByRutor",
            url="https://byrutgame.org",
            specialized_category=Category.GAMES,
            safety_status=SearchProviderSafetyStatus.SAFE,
            safety_reason="Russian game repack site",
            enabled_by_default=True,  # Good games source
        )
    
    def search(self, query: str, category: Category, page: int = 1) -> List[Torrent]:
        """Search ByRutor for games."""
        import re
        from urllib.parse import quote
        
        # Use GET search (tested working)
        url = f"{self.info.url}/index.php?do=search&subaction=search&story={quote(query)}"
        
        try:
            html = self._get(url)
            if not html:
                print("ByRutor: No HTML response")
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Search results use a.search_res container
            results = soup.select('a.search_res')
            
            if not results:
                # Alternative: Try article entries
                results = soup.select('article.shortstory, div.shortstory')
            
            print(f"ByRutor: Found {len(results)} results")
            
            for result in results:
                try:
                    # Get the link (if it's an anchor, use it directly)
                    if result.name == 'a':
                        href = result.get('href', '')
                        # Get name from .search_res_title (correct selector)
                        name_elem = result.select_one('.search_res_title, div.search_res_title')
                        if not name_elem:
                            # Fallback: Try image alt text
                            img = result.select_one('img[alt]')
                            name = img.get('alt', 'Unknown') if img else 'Unknown'
                        else:
                            name = name_elem.get_text(strip=True)
                    else:
                        # It's a div/article, find the link inside
                        link = result.select_one('a[href*=".html"]')
                        if not link:
                            continue
                        href = link.get('href', '')
                        name = link.get_text(strip=True)
                    
                    if not href or name == 'Unknown':
                        continue
                    
                    # Make absolute URL
                    if not href.startswith('http'):
                        href = self.info.url + ('/' if not href.startswith('/') else '') + href
                    
                    # Get size from .search_res_sub span (second span contains size)
                    size = 'Unknown'
                    size_spans = result.select('.search_res_sub span')
                    if len(size_spans) >= 2:
                        size_text = size_spans[1].get_text(strip=True)
                        # Convert Russian size units to English
                        size = size_text.replace('ГБ', 'GB').replace('МБ', 'MB').replace('КБ', 'KB').replace('ТБ', 'TB')
                    
                    # ByRutor doesn't show seeders/leechers on search page
                    # We'll need to fetch detail page for torrent file
                    # For now, create the torrent with the detail page URL
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=-1,  # Unknown - site doesn't show this
                        peers=-1,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=href,
                        magnet_uri='',  # Will be fetched from detail page
                        category=Category.GAMES,
                    )
                    torrents.append(t)
                except Exception as e:
                    print(f"ByRutor: Error parsing result: {e}")
                    continue
            
            # Fetch torrent download URLs from detail pages (first 10 only to avoid slowdown)
            self._fetch_torrent_urls(torrents[:10])
            
            return torrents
            
        except Exception as e:
            print(f"ByRutor search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _fetch_torrent_urls(self, torrents: List[Torrent]):
        """Fetch torrent download URLs from detail pages."""
        import concurrent.futures
        
        def fetch_detail(torrent: Torrent):
            try:
                html = self._get(torrent.description_url, timeout=15)
                if not html:
                    return
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for download button (a.downld)
                download_link = soup.select_one('a.downld')
                if download_link:
                    download_url = download_link.get('href', '')
                    if download_url:
                        # Make absolute if needed
                        if not download_url.startswith('http'):
                            download_url = self.info.url + ('/' if not download_url.startswith('/') else '') + download_url
                        # Store torrent file URL as magnet_uri (SwiftSeed handles .torrent URLs)
                        torrent.magnet_uri = download_url
                
                # Try to extract more size info from detail page
                size_elem = soup.select_one('div.packagedownld span, span.size')
                if size_elem and torrent.size == 'Unknown':
                    size_text = size_elem.get_text(strip=True)
                    torrent.size = size_text.replace('ГБ', 'GB').replace('МБ', 'MB').replace('КБ', 'KB').replace('ТБ', 'TB')
                    
            except Exception as e:
                print(f"ByRutor: Error fetching detail page: {e}")
        
        # Fetch in parallel (max 5 concurrent)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(fetch_detail, torrents)


class FitGirlProvider(SearchProvider):
    """FitGirl Repacks - Popular game repack site with highly compressed games."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="fitgirl",
            name="FitGirl Repacks",
            url="https://fitgirl-repacks.site",
            specialized_category=Category.GAMES,
            safety_status=SearchProviderSafetyStatus.SAFE,
            safety_reason="Popular game repack site",
            enabled_by_default=True,  # Very popular for games
        )
    
    def search(self, query: str, category: Category, page: int = 1) -> List[Torrent]:
        """Search FitGirl Repacks for games."""
        import re
        from urllib.parse import quote
        
        # WordPress search pattern
        if page == 1:
            url = f"{self.info.url}/?s={quote(query)}"
        else:
            url = f"{self.info.url}/page/{page}/?s={quote(query)}"
        
        try:
            html = self._get(url)
            if not html:
                print("FitGirl: No HTML response")
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Search results are in article tags
            articles = soup.select('article, article.post')
            
            print(f"FitGirl: Found {len(articles)} articles")
            
            for article in articles:
                try:
                    # Get title and link from h1.entry-title a or h2.entry-title a
                    title_link = article.select_one('h1.entry-title a, h2.entry-title a, .entry-title a')
                    if not title_link:
                        continue
                    
                    name = title_link.get_text(strip=True)
                    href = title_link.get('href', '')
                    
                    if not name or not href:
                        continue
                    
                    # Get date if available
                    date_elem = article.select_one('time.entry-date, time')
                    upload_date = date_elem.get('datetime', 'Unknown')[:10] if date_elem else 'Unknown'
                    
                    # Try to extract size from article content
                    size = 'Unknown'
                    content = article.select_one('.entry-content, .entry-summary')
                    if content:
                        text = content.get_text()
                        # Look for "Repack Size:" or similar
                        size_match = re.search(r'Repack\s*Size[:\s~]+(\d+(?:\.\d+)?\s*(?:GB|MB|TB))', text, re.IGNORECASE)
                        if size_match:
                            size = size_match.group(1)
                        else:
                            # Try generic size pattern
                            size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:GB|MB|TB))', text, re.IGNORECASE)
                            if size_match:
                                size = size_match.group(1)
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=-1,  # FitGirl doesn't show seeders
                        peers=-1,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date=upload_date,
                        description_url=href,
                        magnet_uri='',  # Will fetch from detail page
                        category=Category.GAMES,
                    )
                    torrents.append(t)
                except Exception as e:
                    print(f"FitGirl: Error parsing article: {e}")
                    continue
            
            # Fetch magnet links from detail pages (first 10)
            self._fetch_magnet_links(torrents[:10])
            
            return torrents
            
        except Exception as e:
            print(f"FitGirl search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _fetch_magnet_links(self, torrents: List[Torrent]):
        """Fetch magnet links from detail pages."""
        import concurrent.futures
        import re
        
        def fetch_detail(torrent: Torrent):
            try:
                html = self._get(torrent.description_url, timeout=15)
                if not html:
                    return
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for magnet link
                magnet_link = soup.select_one('a[href^="magnet:"]')
                if magnet_link:
                    torrent.magnet_uri = magnet_link.get('href', '')
                    return
                
                # Alternative: Look in download mirrors section
                # Sometimes magnet links are in list items or divs
                content = soup.select_one('.entry-content, article')
                if content:
                    for link in content.find_all('a', href=True):
                        href = link.get('href', '')
                        if href.startswith('magnet:'):
                            torrent.magnet_uri = href
                            return
                
                # If no magnet found, try to find 1337x link and note it
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    if '1337x' in href or 'rutor' in href or 'rustorka' in href:
                        # Store the tracker link as description_url for on-demand fetch
                        torrent.description_url = href
                        break
                        
            except Exception as e:
                print(f"FitGirl: Error fetching detail page: {e}")
        
        # Fetch in parallel (max 5 concurrent)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(fetch_detail, torrents)


class ZeroMagnetProvider(SearchProvider):
    """0Magnet (0magnet.com) - Torrent sharing site with adult content."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="0magnet",
            name="0Magnet",
            url="https://0magnet.com",
            specialized_category=Category.PORN,
            safety_status=SearchProviderSafetyStatus.UNSAFE,
            safety_reason="Adult content site",
            enabled_by_default=False,  # NSFW, disabled by default
        )
    
    def search(self, query: str, category: Category, page: int = 1) -> List[Torrent]:
        """Search 0Magnet for torrents."""
        import re
        from urllib.parse import quote
        
        # Use 0magnet.com which has server-side search
        url = f"{self.info.url}/search?q={quote(query)}"
        
        try:
            html = self._get(url)
            if not html:
                print("0Magnet: No HTML response")
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Results are in table rows
            rows = soup.select('tr')
            
            print(f"0Magnet: Found {len(rows)} table rows")
            
            for row in rows:
                try:
                    # Skip header rows
                    if row.find('th'):
                        continue
                    
                    cells = row.find_all('td')
                    if len(cells) < 2:
                        continue
                    
                    # Get title from first cell (may contain link)
                    title_cell = cells[0]
                    title_link = title_cell.find('a')
                    if title_link:
                        title = title_link.get_text(strip=True)
                        href = title_link.get('href', '')
                    else:
                        title = title_cell.get_text(strip=True)
                        href = ''
                    
                    if not title:
                        continue
                    
                    # Get size from cell with class td-size or second cell
                    size = 'Unknown'
                    size_cell = row.select_one('.td-size, td:last-child')
                    if size_cell:
                        size_text = size_cell.get_text(strip=True)
                        if re.search(r'\d+', size_text):
                            size = size_text
                    
                    # Make absolute URL for detail page
                    if href and not href.startswith('http'):
                        href = self.info.url + ('/' if not href.startswith('/') else '') + href
                    
                    # Skip if no link
                    if not href:
                        continue
                    
                    t = Torrent(
                        name=title,
                        size=size,
                        seeders=-1,  # Not available on this site
                        peers=-1,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=href,
                        magnet_uri='',  # Will fetch from detail page
                        category=Category.PORN,
                    )
                    torrents.append(t)
                except Exception as e:
                    print(f"0Magnet: Error parsing row: {e}")
                    continue
            
            # Fetch magnet links from detail pages (first 15)
            self._fetch_magnet_links(torrents[:15])
            
            return torrents
            
        except Exception as e:
            print(f"0Magnet search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _fetch_magnet_links(self, torrents: List[Torrent]):
        """Fetch magnet links from detail pages."""
        import concurrent.futures
        import re
        
        def fetch_detail(torrent: Torrent):
            try:
                html = self._get(torrent.description_url, timeout=15)
                if not html:
                    return
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for magnet link in any link
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    if href.startswith('magnet:'):
                        torrent.magnet_uri = href
                        return
                
                # Try to find hash and construct magnet
                # Look for info_hash or hash in the page
                hash_match = re.search(r'btih[:/]([a-fA-F0-9]{40}|[a-fA-F0-9]{32})', html)
                if hash_match:
                    info_hash = hash_match.group(1)
                    torrent.magnet_uri = f"magnet:?xt=urn:btih:{info_hash}&dn={torrent.name}"
                    return
                    
                # Look for hash text
                hash_elem = soup.find(string=re.compile(r'[a-fA-F0-9]{40}'))
                if hash_elem:
                    info_hash = hash_elem.strip()
                    if len(info_hash) == 40:
                        torrent.magnet_uri = f"magnet:?xt=urn:btih:{info_hash}&dn={torrent.name}"
                        
            except Exception as e:
                print(f"0Magnet: Error fetching detail page: {e}")
        
        # Fetch in parallel (max 5 concurrent)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(fetch_detail, torrents)


class AnirenaProvider(SearchProvider):
    """AniRena provider - Anime torrents."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="anirena",
            name="AniRena",
            url="https://www.anirena.com",
            specialized_category=Category.ANIME,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
            language="Japanese",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search AniRena."""
        # Use provided search URL structure
        url = f"{self.info.url}/index.php?s={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Anirena uses div.full2 containing a table for each row
            divs = soup.select('div.full2')
            
            for div in divs:
                try:
                    # Skip header/search divs
                    if div.find('span', class_='torrents_type'): # Header
                        continue
                    if div.get('id', '').startswith('details'): # Hidden details
                        continue
                        
                    table = div.find('table')
                    if not table:
                        continue
                        
                    tr = table.find('tr')
                    if not tr:
                        continue
                    
                    cols = tr.find_all('td')
                    if len(cols) < 7:
                        continue
                        
                    # Title
                    title_div = cols[1].find('div')
                    if not title_div:
                        title_div = cols[1] # Fallback
                        
                    # Title is usually the 2nd link (first is Group) or the one with nohref/onClick
                    title_link = title_div.find('a', attrs={'nohref': True}) or title_div.find('a', attrs={'onClick': True})
                    
                    if not title_link:
                        # Fallback logic
                        links = title_div.find_all('a')
                        if len(links) > 1:
                            title_link = links[1]
                        elif links:
                            title_link = links[0]
                    
                    if not title_link:
                        continue
                        
                    name = title_link.get_text(strip=True)
                    if not name:
                        continue

                    # Magnet
                    magnet_link = cols[2].select_one('a[href^="magnet:"]')
                    magnet_uri = magnet_link.get('href', '') if magnet_link else ''
                    
                    if not magnet_uri:
                        continue

                    # Size
                    size = cols[3].get_text(strip=True)
                    
                    # Seeds
                    seeds = 0
                    seeds_text = cols[4].get_text(strip=True)
                    if seeds_text.isdigit():
                        seeds = int(seeds_text)
                        
                    # Leechers
                    peers = 0
                    peers_text = cols[5].get_text(strip=True)
                    if peers_text.isdigit():
                        peers = int(peers_text)
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeds,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=self.info.url,
                        magnet_uri=magnet_uri,
                        category=Category.ANIME,
                    )
                    torrents.append(t)
                except Exception:
                    continue
            
            return torrents
        except Exception as e:
            print(f"AniRena search error: {e}")
            return []


class ACGRipProvider(SearchProvider):
    """ACG.RIP provider - Anime torrents."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="acgrip",
            name="ACG.RIP",
            url="https://acg.rip",
            specialized_category=Category.ANIME,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
            language="Chinese",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search ACG.RIP."""
        url = f"{self.info.url}/?term={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            rows = soup.select('table.post-index tr')
            
            for row in rows:
                try:
                    # Skip header
                    if row.find('th'):
                        continue
                        
                    # Title
                    title_span = row.select_one('span.title a')
                    if not title_span:
                        continue
                        
                    name = title_span.get_text(strip=True)
                    desc_url = self.info.url + title_span.get('href', '')
                    
                    # Torrent/Magnet
                    # ACG.RIP provides .torrent links on the listing page
                    action_link = row.select_one('td.action a')
                    if not action_link:
                        continue
                        
                    torrent_href = action_link.get('href', '')
                    if not torrent_href:
                        continue
                        
                    magnet_uri = self.info.url + torrent_href if not torrent_href.startswith('http') else torrent_href
                    
                    # Size
                    size_td = row.select_one('td.size')
                    size = size_td.get_text(strip=True) if size_td else 'Unknown'
                    
                    # Date
                    date_time = row.select_one('td.date time')
                    upload_date = 'Unknown'
                    if date_time:
                        upload_date = date_time.get('datetime', 'Unknown')
                        # If datetime is a timestamp, we might want to convert it, but string is fine for now
                        # Or use text content
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=-1, # ACG.RIP doesn't show seeders on list
                        peers=-1,
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
            print(f"ACG.RIP search error: {e}")
            return []


class BigFanGroupProvider(SearchProvider):
    """BigFanGroup provider - Russian movie/series torrents."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="bigfangroup",
            name="BigFanGroup",
            url="https://bigfangroup.org",
            specialized_category=Category.MOVIES,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
            language="Russian",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search BigFanGroup."""
        import re
        from urllib.parse import quote
        
        url = f"{self.info.url}/browse.php?search={quote(query)}"
        
        try:
            html = self._get(url)
            if not html:
                print("BigFanGroup: No HTML returned")
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            seen_ids = set()  # Track seen torrent IDs to avoid duplicates
            
            # Find all rows in the results table
            rows = soup.select('table.embedded tr')
            print(f"BigFanGroup: Found {len(rows)} rows in table.embedded")
            
            for row in rows:
                try:
                    # Find title link
                    title_link = row.select_one('a[href^="details.php?id="]')
                    if not title_link:
                        continue
                    
                    # Skip rows without seeders link (these are header/nav rows)
                    seeders_link = row.select_one('a[href*="toseeders=1"]')
                    if not seeders_link:
                        continue
                    
                    # Get name from acronym title or text
                    acronym = title_link.select_one('acronym')
                    if acronym and acronym.get('title'):
                        name = acronym.get('title').strip()
                    elif acronym:
                        name = acronym.get_text(strip=True)
                    else:
                        # Fallback: get text from the b tag if present
                        b_tag = title_link.select_one('b')
                        if b_tag:
                            name = b_tag.get_text(strip=True)
                        else:
                            name = title_link.get_text(strip=True)
                    
                    # Skip if name is too long (likely grabbed navigation text)
                    if len(name) > 300:
                        continue
                    
                    # Limit display name length
                    if len(name) > 200:
                        name = name[:197] + "..."
                    
                    if not name:
                        continue
                    
                    # Get detail page URL for description
                    detail_href = title_link.get('href', '')
                    
                    # Extract torrent ID and skip if already seen
                    torrent_id = detail_href.split('id=')[-1] if 'id=' in detail_href else ''
                    if not torrent_id or torrent_id in seen_ids:
                        continue
                    seen_ids.add(torrent_id)
                    
                    desc_url = f"{self.info.url}/{detail_href}" if detail_href else self.info.url
                    
                    # Seeders
                    seeders_link = row.select_one('a[href*="toseeders=1"]')
                    seeders = 0
                    if seeders_link:
                        seeds_text = seeders_link.get_text(strip=True)
                        if seeds_text.isdigit():
                            seeders = int(seeds_text)
                    
                    # Leechers
                    leechers_link = row.select_one('a[href*="todlers=1"]')
                    leechers = 0
                    if leechers_link:
                        leech_text = leechers_link.get_text(strip=True)
                        if leech_text.isdigit():
                            leechers = int(leech_text)
                    
                    # Size - find cell with size pattern
                    size = 'Unknown'
                    cells = row.find_all('td')
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        if re.search(r'\d+(\.\d+)?\s*(GB|MB|KB|TB)', text, re.IGNORECASE):
                            size = text
                            break
                    
                    # Date - from time.png title
                    upload_date = 'Unknown'
                    time_img = row.select_one('img[src*="time"]')
                    if time_img and time_img.get('title'):
                        upload_date = time_img.get('title')[:10]  # First 10 chars
                    
                    # No magnet on search page - need to fetch from detail
                    # Store the download URL pattern
                    download_url = f"{self.info.url}/download.php?id={torrent_id}" if torrent_id else ''
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeders,
                        peers=leechers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date=upload_date,
                        description_url=desc_url,
                        magnet_uri=download_url,  # .torrent download URL
                        category=Category.MOVIES,
                    )
                    torrents.append(t)
                except Exception as ex:
                    print(f"BigFanGroup: Row parse error: {ex}")
                    continue
            
            print(f"BigFanGroup: Returning {len(torrents)} results")
            return torrents
        except Exception as e:
            print(f"BigFanGroup search error: {e}")
            return []


class CpasbienProvider(SearchProvider):
    """Cpasbien - French torrent site for movies, series, music, and software."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="cpasbien",
            name="Cpasbien",
            url="https://www1.cpasbien.to",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
            language="French",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Cpasbien for torrents."""
        import re
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Search URL pattern - cpasbien uses /search_torrent/QUERY.html
        url = f"{self.info.url}/search_torrent/{query}.html"
        
        try:
            html = self._get(url, timeout=15)
            
            if not html:
                print("Cpasbien: Empty response")
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Check for error page
            page_title = soup.title.string if soup.title else ''
            if '404' in page_title or '错误' in page_title or 'error' in page_title.lower():
                print(f"Cpasbien: Error page returned")
                return []
            
            # Find the results table - uses table.table-corps
            table = soup.select_one('table.table-corps, div.table_div table')
            
            if not table:
                print(f"Cpasbien: No results table found")
                return []
            
            rows = table.select('tr')
            print(f"Cpasbien: Found {len(rows)} rows")
            
            for row in rows:
                try:
                    # Title link - a.titre
                    title_link = row.select_one('a.titre')
                    if not title_link:
                        continue
                    
                    name = title_link.get('title', '') or title_link.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue
                    
                    href = title_link.get('href', '')
                    if not href:
                        continue
                    
                    # Build detail URL
                    if href.startswith('http'):
                        desc_url = href
                    else:
                        desc_url = f"{self.info.url}{href}" if href.startswith('/') else f"{self.info.url}/{href}"
                    
                    # Size - div.poid (French for weight/size)
                    size = 'Unknown'
                    size_elem = row.select_one('div.poid')
                    if size_elem:
                        size_text = size_elem.get_text(strip=True)
                        # Check if it's just a number (size in MB)
                        try:
                            size_mb = float(size_text.replace(',', '.'))
                            # Convert to appropriate unit
                            if size_mb >= 1024:
                                size = f"{size_mb / 1024:.2f} GB"
                            else:
                                size = f"{size_mb:.2f} MB"
                        except ValueError:
                            # Has units - convert French units: Go->GB, Mo->MB, Ko->KB
                            size = size_text.replace('Go', 'GB').replace('Mo', 'MB').replace('Ko', 'KB')
                    
                    # Seeders - div.up span.seed_ok
                    seeders = 0
                    seed_elem = row.select_one('div.up span.seed_ok, div.up')
                    if seed_elem:
                        seed_text = seed_elem.get_text(strip=True).replace(',', '')
                        if seed_text.isdigit():
                            seeders = int(seed_text)
                    
                    # Leechers - div.down
                    leechers = 0
                    leech_elem = row.select_one('div.down')
                    if leech_elem:
                        leech_text = leech_elem.get_text(strip=True).replace(',', '')
                        if leech_text.isdigit():
                            leechers = int(leech_text)
                    
                    # Determine category from name
                    torrent_category = Category.MOVIES  # Default for cpasbien
                    name_lower = name.lower()
                    if any(x in name_lower for x in ['series', 'saison', 's01', 's02', 'episode']):
                        torrent_category = Category.TV
                    elif any(x in name_lower for x in ['music', 'musique', 'album', 'mp3', 'flac']):
                        torrent_category = Category.MUSIC
                    elif any(x in name_lower for x in ['game', 'jeu', 'jeux']):
                        torrent_category = Category.GAMES
                    elif any(x in name_lower for x in ['logiciel', 'software', 'windows']):
                        torrent_category = Category.APPS
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeders,
                        peers=leechers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri='',  # Will be fetched from detail page
                        category=torrent_category,
                    )
                    torrents.append(t)
                except Exception as ex:
                    print(f"Cpasbien: Row parse error: {ex}")
                    continue
            
            # Fetch magnet links from detail pages (parallel)
            if torrents:
                self._fetch_magnet_links(torrents[:15])  # Limit to first 15
            
            print(f"Cpasbien: Returning {len(torrents)} results")
            return torrents
        except Exception as e:
            print(f"Cpasbien search error: {e}")
            return []
    
    def _fetch_magnet_links(self, torrents: List[Torrent]):
        """Fetch magnet links from detail pages."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def fetch_detail(torrent: Torrent):
            try:
                html = self._get(torrent.description_url, timeout=10)
                if not html:
                    return
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find magnet link
                magnet = soup.select_one('a[href^="magnet:"]')
                if magnet:
                    torrent.magnet_uri = magnet.get('href', '')
            except Exception as e:
                print(f"Cpasbien: Detail fetch error: {e}")
        
        # Fetch in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_detail, t) for t in torrents]
            for future in as_completed(futures, timeout=30):
                try:
                    future.result()
                except:
                    pass


class CrackingPatchingProvider(SearchProvider):
    """CrackingPatching - Software cracks and patches with magnet links."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="crackingpatching",
            name="CrackingPatching",
            url="https://crackingpatching.com",
            specialized_category=Category.APPS,
            safety_status=SearchProviderSafetyStatus.UNSAFE,
            safety_reason="Contains cracked software - use at your own risk",
            enabled_by_default=False,
            language="English",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search CrackingPatching for software."""
        import re
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # WordPress search URL
        url = f"{self.info.url}/?s={query}"
        
        try:
            html = self._get(url, timeout=15)
            
            if not html:
                print("CrackingPatching: Empty response")
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Find articles - WordPress structure
            articles = soup.select('article, .post, div[id^="post-"]')
            
            if not articles:
                print("CrackingPatching: No articles found")
                return []
            
            print(f"CrackingPatching: Found {len(articles)} articles")
            
            for article in articles[:20]:  # Limit to 20
                try:
                    # Title link
                    title_link = article.select_one('h1 a, h2 a, h3 a, .entry-title a')
                    if not title_link:
                        continue
                    
                    name = title_link.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue
                    
                    href = title_link.get('href', '')
                    if not href:
                        continue
                    
                    # Build URL
                    if href.startswith('http'):
                        desc_url = href
                    else:
                        desc_url = f"{self.info.url}{href}" if href.startswith('/') else f"{self.info.url}/{href}"
                    
                    t = Torrent(
                        name=name,
                        size='Unknown',  # Will try to extract from detail page
                        seeders=0,
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri='',  # Will be fetched from detail page
                        category=Category.APPS,
                    )
                    torrents.append(t)
                except Exception as ex:
                    print(f"CrackingPatching: Article parse error: {ex}")
                    continue
            
            # Fetch magnet links and sizes from detail pages
            if torrents:
                self._fetch_details(torrents[:15])
            
            # Filter out torrents without magnet links
            torrents = [t for t in torrents if t.magnet_uri]
            
            print(f"CrackingPatching: Returning {len(torrents)} results with magnets")
            return torrents
        except Exception as e:
            print(f"CrackingPatching search error: {e}")
            return []
    
    def _fetch_details(self, torrents: List[Torrent]):
        """Fetch magnet links and sizes from detail pages."""
        import re
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def fetch_detail(torrent: Torrent):
            try:
                html = self._get(torrent.description_url, timeout=10)
                if not html:
                    return
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find magnet link(s)
                magnets = soup.select('a[href^="magnet:"]')
                if magnets:
                    # Take the first magnet link
                    torrent.magnet_uri = magnets[0].get('href', '')
                
                # Try to extract size from page content
                content = soup.select_one('.entry-content, .post-content, article')
                if content:
                    text = content.get_text()
                    # Look for size patterns
                    size_match = re.search(r'(?:Size|Размер)[:\s]*(\d+(?:[.,]\d+)?\s*(?:GB|MB|KB|gb|mb))', text, re.IGNORECASE)
                    if size_match:
                        torrent.size = size_match.group(1)
                    else:
                        # Try general size pattern
                        size_match = re.search(r'(\d+(?:[.,]\d+)?\s*(?:GB|MB))', text, re.IGNORECASE)
                        if size_match:
                            torrent.size = size_match.group(1)
                
            except Exception as e:
                print(f"CrackingPatching: Detail fetch error: {e}")
        
        # Fetch in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_detail, t) for t in torrents]
            for future in as_completed(futures, timeout=30):
                try:
                    future.result()
                except:
                    pass
        
        print(f"CrackingPatching: Returning {len(torrents)} results with magnets")
        return [t for t in torrents if t.magnet_uri]


class EHentaiProvider(SearchProvider):
    """E-Hentai - Hentai doujinshi and manga."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="ehentai",
            name="E-Hentai",
            url="https://e-hentai.org",
            specialized_category=Category.PORN,
            safety_status=SearchProviderSafetyStatus.SAFE,
            safety_reason="Contains adult content",
            enabled_by_default=False,
            language="Multi",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search E-Hentai."""
        import re
        
        # Search on torrents.php
        url = f"{self.info.url}/torrents.php?search={query}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Results are in tables. Look for the main results table.
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) < 2:
                    continue
                
                # Check header to confirm it's the torrent table
                header_text = rows[0].get_text(strip=True).lower()
                if 'size' not in header_text or 'added' not in header_text:
                    continue
                
                for row in rows[1:]:
                    try:
                        cells = row.find_all('td')
                        if len(cells) < 6:
                            continue
                        
                        # Column structure on torrents.php:
                        # 0: Added
                        # 1: Name (link to download/popup) - we use this as "magnet"/download link
                        # 2: Gallery ID (link to gallery) - description URL
                        # 3: Size
                        # 4: Seeds
                        # 5: Leechers
                        # 6: Downloads
                        
                        # Name and Download Link
                        name_cell = cells[1]
                        name_link = name_cell.find('a')
                        if not name_link:
                            continue
                            
                        name = name_link.get_text(strip=True)
                        torrent_url = name_link.get('href', '')
                        if not torrent_url.startswith('http'):
                            torrent_url = self.info.url + torrent_url
                        
                        # Description URL (Gallery)
                        desc_cell = cells[2]
                        desc_link = desc_cell.find('a')
                        if desc_link:
                            desc_url = desc_link.get('href', '')
                        else:
                            desc_url = torrent_url
                        
                        # Size
                        size = cells[3].get_text(strip=True)
                        
                        # Seeds/Peers
                        try:
                            seeders = int(cells[4].get_text(strip=True))
                            leechers = int(cells[5].get_text(strip=True))
                        except:
                            seeders = 0
                            leechers = 0
                        
                        # Date
                        upload_date = cells[0].get_text(strip=True)
                        
                        t = Torrent(
                            name=name,
                            size=size,
                            seeders=seeders,
                            peers=leechers,
                            provider_id=self.info.id,
                            provider_name=self.info.name,
                            upload_date=upload_date,
                            description_url=desc_url,
                            magnet_uri=torrent_url, # Direct .torrent download link
                            category=Category.PORN,
                        )
                        torrents.append(t)
                    except Exception:
                        continue
                
                if torrents:
                    break
            
            return torrents
        except Exception as e:
            print(f"E-Hentai search error: {e}")
            return []
            
    def resolve_download(self, torrent: Torrent) -> Optional[str]:
        """Resolve E-Hentai download link/file."""
        import os
        import tempfile
        import time
        
        url = torrent.magnet_uri
        if not url:
            return None
            
        print(f"Resolving E-Hentai download for: {torrent.name}")
        print(f"DEBUG: Original URL: {url}")
        
        # If it's already a magnet, return it
        if url.startswith('magnet:'):
            return url
        
        def is_valid_torrent(content, content_type='', content_disposition=''):
            """Check if content is a valid torrent file."""
            if 'application/x-bittorrent' in content_type.lower():
                return True
            if 'filename=' in content_disposition and '.torrent' in content_disposition.lower():
                return True
            # Check bencoded structure
            if content.startswith(b'd'):
                # Basic check: starts with 'd' and contains 'info' key
                if b'info' in content[:500] or b'announce' in content[:200]:
                    return True
            return False
        
        def save_torrent(content, name_hint=''):
            """Save torrent content to temp file."""
            fd, path = tempfile.mkstemp(suffix='.torrent')
            with os.fdopen(fd, 'wb') as f:
                f.write(content)
            print(f"Saved torrent file to: {path}")
            return path
            
        # If it's the gallerytorrents.php link
        if 'gallerytorrents.php' in url or 'e-hentai.org' in url:
            try:
                # Ensure session headers are set
                self.session.headers.update({
                    'Referer': f"{self.info.url}/torrents.php",
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                })
                
                print(f"DEBUG: Fetching URL: {url}")
                resp = self.session.get(url, timeout=30, verify=False)
                print(f"DEBUG: Response status: {resp.status_code}, Content-Type: {resp.headers.get('Content-Type', 'Unknown')}")
                
                # Check for content disposition or type
                ct = resp.headers.get('Content-Type', '').lower()
                cd = resp.headers.get('Content-Disposition', '')
                
                # 1. Check if direct download worked
                if is_valid_torrent(resp.content, ct, cd):
                    print("Direct download worked!")
                    return save_torrent(resp.content)
                
                # 2. It's HTML (popup page). Parse it for download links.
                print("Got HTML response, parsing for download link...")
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                links = soup.find_all('a')
                print(f"DEBUG: Found {len(links)} links in popup")
                
                # If no links, try visiting gallery page first to set cookies
                if len(links) == 0 and torrent.description_url and 'e-hentai.org/g/' in torrent.description_url:
                    print(f"DEBUG: No links found. Body preview: {resp.text[:500]}")
                    print(f"DEBUG: Visiting gallery page first: {torrent.description_url}")
                    try:
                        self.session.get(torrent.description_url, timeout=30, verify=False)
                        time.sleep(0.5)
                        resp = self.session.get(url, timeout=30, verify=False)
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        links = soup.find_all('a')
                        print(f"DEBUG: Found {len(links)} links after visiting gallery")
                    except Exception as ex:
                        print(f"DEBUG: Gallery visit failed: {ex}")
                
                # Find the best download link
                download_links = []
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text().strip()
                    
                    # Skip empty or javascript links
                    if not href or href.startswith('javascript:') or href == '#':
                        continue
                    
                    # Score the link based on relevance
                    score = 0
                    text_lower = text.lower()
                    
                    # Links with torrent-related keywords
                    if '.torrent' in href.lower():
                        score += 10
                    if 'gallerytorrents.php' in href and ('t=' in href or 'gid=' in href):
                        score += 5
                    if 'personal' in text_lower:
                        score += 3
                    if 'download' in text_lower:
                        score += 2
                    if 'torrent' in text_lower:
                        score += 2
                    
                    # Avoid certain links
                    if 'redistribution' in text_lower and 'non' not in text_lower:
                        score -= 5
                    
                    if score > 0:
                        download_links.append((score, href, text))
                
                # Sort by score (highest first)
                download_links.sort(key=lambda x: x[0], reverse=True)
                
                print(f"DEBUG: Found {len(download_links)} potential download links")
                for score, href, text in download_links[:5]:  # Show top 5
                    print(f"  - Score {score}: '{text}' -> {href[:100]}")
                
                # Try each link in order of score
                for score, href, text in download_links:
                    # Construct full URL if needed
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            href = self.info.url + href
                        else:
                            href = self.info.url + '/' + href
                    
                    print(f"DEBUG: Trying download link: {href}")
                    time.sleep(0.5)  # Polite delay
                    
                    try:
                        dl_resp = self.session.get(href, timeout=30, verify=False)
                        print(f"DEBUG: Download response status: {dl_resp.status_code}, Content-Type: {dl_resp.headers.get('Content-Type', 'Unknown')}")
                        
                        if dl_resp.status_code == 200:
                            dl_ct = dl_resp.headers.get('Content-Type', '')
                            dl_cd = dl_resp.headers.get('Content-Disposition', '')
                            
                            if is_valid_torrent(dl_resp.content, dl_ct, dl_cd):
                                return save_torrent(dl_resp.content)
                            else:
                                print(f"DEBUG: Content is not a valid torrent file")
                                print(f"DEBUG: Content preview: {dl_resp.content[:100]}")
                        else:
                            print(f"DEBUG: Failed to download, status: {dl_resp.status_code}")
                    except Exception as dl_ex:
                        print(f"DEBUG: Download error: {dl_ex}")
                        continue
                
                print("Could not find a working download link")
                             
            except Exception as e:
                print(f"Error resolving E-Hentai: {e}")
                import traceback
                traceback.print_exc()
        
        # Return original URL if nothing worked (will be handled by TorrentManager)
        print(f"DEBUG: Returning original URL: {url}")
        return url


class TorrentMacProvider(SearchProvider):
    """TorrentMac - Mac software and applications torrents."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="torrentmac",
            name="TorrentMac",
            url="https://www.torrentmac.net",
            specialized_category=Category.APPS,
            safety_status=SearchProviderSafetyStatus.UNSAFE,
            safety_reason="Contains cracked Mac software - not all pages have torrent links",
            enabled_by_default=False,
            language="English",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search TorrentMac for Mac software torrents."""
        import re
        from urllib.parse import quote
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # WordPress-style search
        url = f"{self.info.url}/?s={quote(query)}"
        
        try:
            html = self._get(url, timeout=15)
            
            if not html:
                print("TorrentMac: Empty response")
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Find all article entries (WordPress theme)
            # Look for post containers with titles
            articles = soup.select('article, .post, div.content-inner article')
            
            if not articles:
                # Try alternative selectors
                articles = soup.select('h2.entry-title a, h3.entry-title a, .post-title a')
                
            print(f"TorrentMac: Found {len(articles)} articles/entries")
            
            for article in articles[:25]:  # Limit to 25 results
                try:
                    # Get title and URL
                    title_link = None
                    
                    # Check if article itself is the link
                    if article.name == 'a' and article.get('href'):
                        title_link = article
                    else:
                        # Find title link within article
                        title_link = article.select_one('h2.entry-title a, h3 a, h2 a, .post-title a, a.title')
                    
                    if not title_link:
                        continue
                    
                    name = title_link.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue
                    
                    href = title_link.get('href', '')
                    if not href:
                        continue
                    
                    # Build detail URL
                    if href.startswith('http'):
                        desc_url = href
                    else:
                        desc_url = f"{self.info.url}{href}" if href.startswith('/') else f"{self.info.url}/{href}"
                    
                    # Skip if not a torrentmac URL
                    if 'torrentmac.net' not in desc_url:
                        continue
                    
                    t = Torrent(
                        name=name,
                        size='Unknown',  # Will be updated from detail page
                        seeders=-1,  # Not shown on listing
                        peers=-1,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri='',  # Will be fetched from detail page
                        category=Category.APPS,
                    )
                    torrents.append(t)
                except Exception as ex:
                    print(f"TorrentMac: Article parse error: {ex}")
                    continue
            
            # Fetch torrent links from detail pages (parallel)
            if torrents:
                self._fetch_torrent_links(torrents[:15])  # Limit to first 15 for speed
            
            # Filter out torrents without download links
            torrents = [t for t in torrents if t.magnet_uri]
            
            print(f"TorrentMac: Returning {len(torrents)} results with torrent links")
            return torrents
        except Exception as e:
            print(f"TorrentMac search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _fetch_torrent_links(self, torrents: List[Torrent]):
        """Fetch torrent download links from detail pages."""
        import re
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def fetch_detail(torrent: Torrent):
            try:
                html = self._get(torrent.description_url, timeout=10)
                if not html:
                    return
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for .torrent file links
                # TorrentMac uses direct links like: /wp-content/uploads/tr_files/...torrent
                # We need to find links that END with .torrent, not just contain it
                all_links = soup.find_all('a', href=True)
                torrent_href = None
                
                for link in all_links:
                    href = link.get('href', '')
                    # Check if URL ends with .torrent (actual torrent file)
                    if href.endswith('.torrent'):
                        torrent_href = href
                        break
                
                if torrent_href:
                    if not torrent_href.startswith('http'):
                        torrent_href = f"{self.info.url}{torrent_href}" if torrent_href.startswith('/') else f"{self.info.url}/{torrent_href}"
                    torrent.magnet_uri = torrent_href  # Store torrent URL as magnet_uri
                    print(f"TorrentMac: Found torrent link for {torrent.name[:30]}...")
                
                # Try to extract size from page content
                content = soup.select_one('.entry-content, .post-content, article')
                if content:
                    text = content.get_text()
                    # Look for size patterns like "Size: 1.5 GB" or "1.5 GB"
                    size_match = re.search(r'(?:Size|Размер)[:\s]*([\d.,]+\s*(?:GB|MB|KB|TB))', text, re.IGNORECASE)
                    if size_match:
                        torrent.size = size_match.group(1).strip()
                    else:
                        # Try general size pattern
                        size_match = re.search(r'([\d.,]+\s*(?:GB|MB))', text)
                        if size_match:
                            torrent.size = size_match.group(1).strip()
                
            except Exception as e:
                print(f"TorrentMac: Detail fetch error for {torrent.name[:30]}: {e}")
        
        # Fetch in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_detail, t) for t in torrents]
            for future in as_completed(futures, timeout=30):
                try:
                    future.result()
                except Exception:
                    pass


class FreeJavTorrentProvider(SearchProvider):
    """FreeJavTorrent - Japanese adult video torrents."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="freejavtorrent",
            name="FreeJavTorrent",
            url="https://www.freejavtorrent.com",
            specialized_category=Category.PORN,
            safety_status=SearchProviderSafetyStatus.UNSAFE,
            safety_reason="Adult content - Japanese adult videos",
            enabled_by_default=False,
            language="English",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search FreeJavTorrent for JAV torrents."""
        import re
        from urllib.parse import quote
        
        url = f"{self.info.url}/?s={quote(query)}"
        
        try:
            html = self._get(url, timeout=15)
            
            if not html:
                print("FreeJavTorrent: Empty response")
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Find all torrent links - format: [SIZE] Title [CODE] (Studio) [tags]
            # Links look like: /cjod-484-hatano-yui-goto-65045.html
            links = soup.find_all('a', href=True)
            
            for link in links:
                try:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Skip non-content links
                    if not href or not text:
                        continue
                    
                    # Match detail page URLs (ending with -NUMBER.html)
                    match = re.search(r'-(\d+)\.html$', href)
                    if not match:
                        continue
                    
                    torrent_id = match.group(1)
                    
                    # Parse size from title [7.35 GB]
                    size_match = re.match(r'\[([\d.]+\s*(?:GB|MB|KB|TB))\]', text)
                    size = size_match.group(1) if size_match else 'Unknown'
                    
                    # Clean up name - remove size prefix
                    name = re.sub(r'^\[[\d.]+\s*(?:GB|MB|KB|TB)\]\s*', '', text).strip()
                    
                    # Skip if name is too short or is a category link
                    if len(name) < 10 or name.lower() in ['japanese movies', 'chinese movies']:
                        continue
                    
                    # Build download URL
                    download_url = f"{self.info.url}/dl.php?t={torrent_id}"
                    
                    # Build detail URL
                    if href.startswith('http'):
                        desc_url = href
                    else:
                        desc_url = f"{self.info.url}{href}" if href.startswith('/') else f"{self.info.url}/{href}"
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=-1,  # Not shown on site
                        peers=-1,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=download_url,  # Store download page URL, resolve later
                        category=Category.PORN,
                    )
                    
                    # Avoid duplicates
                    if not any(existing.name == t.name for existing in torrents):
                        torrents.append(t)
                        
                except Exception as ex:
                    continue
            
            print(f"FreeJavTorrent: Found {len(torrents)} results")
            return torrents[:50]  # Limit results
            
        except Exception as e:
            print(f"FreeJavTorrent search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def resolve_download(self, torrent: Torrent) -> Optional[str]:
        """Resolve download link by fetching the actual torrent file URL from download page."""
        import re
        import os
        import tempfile
        
        url = torrent.magnet_uri
        if not url:
            return None
        
        # If it's already a direct torrent URL
        if url.endswith('.torrent'):
            return url
        
        # If it's already a magnet link
        if url.startswith('magnet:'):
            return url
        
        # If it's a dl.php page, fetch the actual torrent
        if 'dl.php' in url:
            try:
                print(f"FreeJavTorrent: Resolving download from {url}")
                
                html = self._get(url, timeout=15)
                if not html:
                    return url
                
                # Find torrent URL in page
                torrent_urls = re.findall(r'https?://[^\s\'"]+\.torrent[^\s\'"]*', html)
                
                if torrent_urls:
                    torrent_url = torrent_urls[0]
                    # Clean up URL
                    torrent_url = torrent_url.split("'")[0].split('"')[0]
                    print(f"FreeJavTorrent: Found torrent URL: {torrent_url}")
                    
                    # Download the torrent file
                    torrent_content = self._get(torrent_url, timeout=30, return_bytes=True)
                    
                    if torrent_content and torrent_content.startswith(b'd'):
                        # Save to temp file
                        fd, path = tempfile.mkstemp(suffix='.torrent')
                        with os.fdopen(fd, 'wb') as f:
                            f.write(torrent_content)
                        print(f"FreeJavTorrent: Saved torrent file to: {path}")
                        return path
                    else:
                        print("FreeJavTorrent: Downloaded content is not a valid torrent")
                else:
                    print("FreeJavTorrent: No torrent URL found in download page")
                    
            except Exception as e:
                print(f"FreeJavTorrent resolve error: {e}")
                import traceback
                traceback.print_exc()
        
        return url
    
    def _get(self, url, timeout=15, return_bytes=False):
        """Custom GET method to handle bytes response."""
        try:
            import urllib3
            urllib3.disable_warnings()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            resp = self.session.get(url, headers=headers, timeout=timeout, verify=False)
            
            if resp.status_code == 200:
                if return_bytes:
                    return resp.content
                return resp.text
            return None
        except Exception as e:
            print(f"FreeJavTorrent GET error: {e}")
            return None


class PiratesParadiseProvider(SearchProvider):
    """Pirates Paradise - Clean torrent search site with Movies and TV."""
    
    # Common trackers for magnet links
    TRACKERS = [
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://tracker.openbittorrent.com:6969/announce",
        "udp://open.tracker.cl:1337/announce",
        "udp://tracker.torrent.eu.org:451/announce",
    ]
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="piratesparadise",
            name="Pirates Paradise",
            url="https://piratesparadise.org",
            specialized_category=None,  # General - Movies and TV
            safety_status=SearchProviderSafetyStatus.SAFE,
            safety_reason="Clean interface, no ads, movies and TV shows",
            enabled_by_default=True,
            language="English",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Pirates Paradise for torrents."""
        import re
        from urllib.parse import quote, urlencode
        
        url = f"{self.info.url}/search.php?q={quote(query)}"
        
        try:
            html = self._get(url, timeout=15)
            
            if not html:
                print("PiratesParadise: Empty response")
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Find all torrent links - format: /torrent/{info_hash}
            links = soup.find_all('a', href=True)
            
            for link in links:
                try:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Skip non-torrent links
                    if not href or '/torrent/' not in href:
                        continue
                    
                    # Skip pagination and other links
                    if not text or len(text) < 5:
                        continue
                    
                    # Extract info hash from URL
                    match = re.search(r'/torrent/([a-fA-F0-9]{40})', href)
                    if not match:
                        continue
                    
                    info_hash = match.group(1).lower()
                    
                    # Build magnet link directly from info hash
                    tracker_params = "&".join([f"tr={quote(t)}" for t in self.TRACKERS])
                    magnet = f"magnet:?xt=urn:btih:{info_hash}&{tracker_params}"
                    
                    # Build detail URL
                    if href.startswith('http'):
                        desc_url = href
                    else:
                        desc_url = f"{self.info.url}{href}" if href.startswith('/') else f"{self.info.url}/{href}"
                    
                    # Determine category from name
                    name = text.strip()
                    torrent_category = Category.MOVIES
                    name_lower = name.lower()
                    if any(x in name_lower for x in ['s0', 's1', 's2', 's3', 's4', 's5', 's6', 's7', 's8', 's9', 'season', 'episode', 'series']):
                        torrent_category = Category.SERIES
                    
                    t = Torrent(
                        name=name,
                        size='Unknown',  # Not shown in search results
                        seeders=-1,  # Not shown in search listing
                        peers=-1,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=magnet,
                        category=torrent_category,
                    )
                    
                    # Avoid duplicates
                    if not any(existing.magnet_uri == t.magnet_uri for existing in torrents):
                        torrents.append(t)
                        
                except Exception as ex:
                    continue
            
            print(f"PiratesParadise: Found {len(torrents)} results")
            return torrents[:50]  # Limit results
            
        except Exception as e:
            print(f"PiratesParadise search error: {e}")
            import traceback
            traceback.print_exc()
            return []


class MagnetCatProvider(SearchProvider):
    """MagnetCat - Magnet link search engine with billions of torrents."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="magnetcat",
            name="MagnetCat",
            url="https://magnetcatcat.com",
            specialized_category=None,  # General - All categories
            safety_status=SearchProviderSafetyStatus.SAFE,
            safety_reason="Magnet search engine with no ads",
            enabled_by_default=True,
            language="Multi",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search MagnetCat for torrents."""
        import re
        from urllib.parse import quote
        
        # URL format: /search-{query}-{category}-{sort}-{page}.html
        # category: 0=all, sort: 0=relevance, page: 1
        encoded_query = quote(query, safe='')
        url = f"{self.info.url}/search-{encoded_query}-0-0-1.html"
        
        try:
            html = self._get(url, timeout=30)
            
            if not html:
                print("MagnetCat: Empty response")
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Find ssbox divs - each contains one result
            ssboxes = soup.find_all('div', class_='ssbox')
            
            for ssbox in ssboxes:
                try:
                    # Find all links in this ssbox
                    all_links = ssbox.find_all('a', href=True)
                    
                    name = None
                    magnet_uri = None
                    desc_url = None
                    
                    for link in all_links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        
                        # Check if it's a magnet link
                        if href.startswith('magnet:'):
                            magnet_uri = href
                        # Check if it's a title link (not magnet, has actual text)
                        elif text and len(text) > 5 and '磁力' not in text and 'magnet' not in text.lower():
                            if not name:  # Take the first valid title
                                name = text
                                desc_url = href if href.startswith('http') else f"{self.info.url}{href}"
                    
                    if not magnet_uri:
                        continue
                    
                    # Extract info hash from magnet
                    hash_match = re.search(r'btih:([a-fA-F0-9]{40})', magnet_uri)
                    if not hash_match:
                        continue
                    
                    info_hash = hash_match.group(1).lower()
                    
                    # Fallback for name
                    if not name:
                        dn_match = re.search(r'dn=([^&]+)', magnet_uri)
                        if dn_match:
                            from urllib.parse import unquote
                            name = unquote(dn_match.group(1))
                        else:
                            name = f"Torrent {info_hash[:16]}"
                    
                    if not desc_url:
                        desc_url = f"{self.info.url}/hash/{info_hash}.html"
                    
                    # Find size in the ssbox text
                    ssbox_text = ssbox.get_text()
                    # More strict regex: require at least one digit, match larger units first
                    size_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(GB|GiB|MB|MiB|KB|KiB|TB|TiB)', ssbox_text, re.I)
                    if size_match:
                        # Format with limited decimal places
                        try:
                            num_val = float(size_match.group(1).replace(',', '.'))
                            unit = size_match.group(2)
                            if num_val == int(num_val):
                                size = f"{int(num_val)} {unit}"
                            else:
                                size = f"{num_val:.2f} {unit}"
                        except:
                            size = size_match.group(0)
                    else:
                        size = 'Unknown'
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=-1,
                        peers=-1,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri=magnet_uri,
                        category=Category.OTHER,
                    )
                    
                    # Avoid duplicates
                    if not any(existing.magnet_uri == t.magnet_uri for existing in torrents):
                        torrents.append(t)
                        
                except Exception as ex:
                    continue
            
            print(f"MagnetCat: Found {len(torrents)} results")
            return torrents[:50]
            
        except Exception as e:
            print(f"MagnetCat search error: {e}")
            import traceback
            traceback.print_exc()
            return []


class GamesTorrentsProvider(SearchProvider):
    """GamesTorrents - Spanish game torrents for PC, PS3, Xbox360, PS2, PSP, Mac, NDS."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="gamestorrents",
            name="GamesTorrents",
            url="https://www.gamestorrents.app",
            specialized_category=Category.GAMES,
            safety_status=SearchProviderSafetyStatus.UNSAFE,
            safety_reason="Contains cracked games - use at your own risk",
            enabled_by_default=False,
            language="Spanish",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search GamesTorrents for game torrents."""
        import re
        from urllib.parse import quote
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        url = f"{self.info.url}/?s={quote(query)}"
        
        try:
            html = self._get(url, timeout=15)
            
            if not html:
                print("GamesTorrents: Empty response")
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            seen_urls = set()
            
            # First try to find results table (main format on the site)
            results_table = soup.find('table')
            if results_table:
                rows = results_table.find_all('tr')
                for row in rows:
                    try:
                        cells = row.find_all('td')
                        if len(cells) >= 3:
                            # Table format: Nombre | Fecha | Tamaño | Version | Genero | Idioma
                            name_cell = cells[0]
                            link = name_cell.find('a', href=re.compile(r'/juegos-[^/]+/[^/]+/$'))
                            if not link:
                                continue
                            
                            href = link.get('href', '')
                            text = link.get_text(strip=True)
                            
                            if not href or href in seen_urls or not text or len(text) < 3:
                                continue
                            
                            seen_urls.add(href)
                            
                            # Extract platform from URL
                            platform_match = re.search(r'/juegos-([^/]+)/', href)
                            platform = platform_match.group(1).upper() if platform_match else 'PC'
                            
                            # Size is in 3rd column (index 2) - "Tamaño"
                            size = 'Unknown'
                            if len(cells) > 2:
                                size_text = cells[2].get_text(strip=True)
                                # Match patterns like "11.47 GBs", "0.89 GB", "907.60 MBs"
                                size_match = re.search(r'(\d+(?:[.,]\d+)?\s*(?:GB|MB|TB|KB)s?)', size_text, re.I)
                                if size_match:
                                    # Normalize: remove trailing 's' from units
                                    size = re.sub(r'(GB|MB|TB|KB)s', r'\1', size_match.group(1), flags=re.I)
                            
                            # Build full URL if needed
                            if not href.startswith('http'):
                                href = f"{self.info.url}{href}" if href.startswith('/') else f"{self.info.url}/{href}"
                            
                            t = Torrent(
                                name=f"[{platform}] {text}",
                                size=size,
                                seeders=-1,
                                peers=-1,
                                provider_id=self.info.id,
                                provider_name=self.info.name,
                                upload_date='Unknown',
                                description_url=href,
                                magnet_uri=href,  # Store detail URL, resolve later
                                category=Category.GAMES,
                            )
                            
                            torrents.append(t)
                    except Exception as ex:
                        continue
            
            # Fallback: Find game links if table parsing didn't work
            if not torrents:
                game_links = soup.find_all('a', href=re.compile(r'/juegos-[^/]+/[^/]+/$'))
                
                for link in game_links:
                    try:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        
                        # Skip category links, duplicates, and empty text
                        if '?category_name=' in href or href in seen_urls or not text or len(text) < 3:
                            continue
                        
                        seen_urls.add(href)
                        
                        # Extract platform from URL
                        platform_match = re.search(r'/juegos-([^/]+)/', href)
                        platform = platform_match.group(1).upper() if platform_match else 'PC'
                        
                        # Try to find size from parent elements
                        size = 'Unknown'
                        # Look in parent containers for size info
                        parent = link.find_parent(['div', 'li', 'article', 'section', 'tr'])
                        if parent:
                            parent_text = parent.get_text()
                            # Look for size patterns like "12.5 GBs", "800 MBs", etc
                            size_match = re.search(r'(\d+(?:[.,]\d+)?\s*(?:GB|MB|TB|KB)s?)', parent_text, re.I)
                            if size_match:
                                size = re.sub(r'(GB|MB|TB|KB)s', r'\1', size_match.group(1), flags=re.I)
                        
                        # Build full URL if needed
                        if not href.startswith('http'):
                            href = f"{self.info.url}{href}" if href.startswith('/') else f"{self.info.url}/{href}"
                        
                        t = Torrent(
                            name=f"[{platform}] {text}",
                            size=size,
                            seeders=-1,
                            peers=-1,
                            provider_id=self.info.id,
                            provider_name=self.info.name,
                            upload_date='Unknown',
                            description_url=href,
                            magnet_uri=href,  # Store detail URL, resolve later
                            category=Category.GAMES,
                        )
                        
                        torrents.append(t)
                            
                    except Exception as ex:
                        continue
            
            # Fetch sizes for torrents that don't have size info
            torrents_needing_size = [t for t in torrents if t.size == 'Unknown']
            if torrents_needing_size:
                print(f"GamesTorrents: Fetching sizes for {len(torrents_needing_size)} results...")
                self._fetch_sizes(torrents_needing_size)
            
            print(f"GamesTorrents: Found {len(torrents)} results")
            return torrents[:50]
            
        except Exception as e:
            print(f"GamesTorrents search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _fetch_sizes(self, torrents: List[Torrent]):
        """Fetch file sizes from detail pages in parallel."""
        import concurrent.futures
        import re
        
        def fetch_size(torrent: Torrent):
            try:
                html = self._get(torrent.description_url, timeout=15)
                if not html:
                    return
                
                # Pattern 1: Look for "Tamaño:" in list items (common format)
                # <li>Tamaño: <strong>11.47 GBs</strong> </li>
                tamano_match = re.search(r'Tamaño[:\s]*<?\s*(?:strong>)?(\d+(?:[.,]\d+)?\s*(?:GB|MB|TB|KB)s?)', html, re.I)
                if tamano_match:
                    size = re.sub(r'(GB|MB|TB|KB)s', r'\1', tamano_match.group(1), flags=re.I)
                    torrent.size = size
                    return
                
                # Pattern 2: Plain text "Tamaño: X GB"
                tamano_text = re.search(r'Tamaño[:\s]+(\d+(?:[.,]\d+)?\s*(?:GB|MB|TB|KB)s?)', html, re.I)
                if tamano_text:
                    size = re.sub(r'(GB|MB|TB|KB)s', r'\1', tamano_text.group(1), flags=re.I)
                    torrent.size = size
                    return
                
                # Pattern 3: Size / Peso (alternative Spanish term)
                peso_match = re.search(r'(?:Size|Peso)[:\s]+(\d+(?:[.,]\d+)?\s*(?:GB|MB|TB|KB)s?)', html, re.I)
                if peso_match:
                    size = re.sub(r'(GB|MB|TB|KB)s', r'\1', peso_match.group(1), flags=re.I)
                    torrent.size = size
                    return
                
            except Exception as e:
                print(f"GamesTorrents: Error fetching size: {e}")
        
        # Use ThreadPoolExecutor to fetch sizes in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_size, t) for t in torrents[:15]]  # Limit to 15
            concurrent.futures.wait(futures, timeout=20)
    
    def resolve_download(self, torrent: Torrent) -> Optional[str]:
        """Resolve download by fetching .torrent file from detail page."""
        import re
        import os
        import tempfile
        
        url = torrent.magnet_uri
        if not url:
            return None
        
        # If it's already a torrent file URL
        if url.endswith('.torrent'):
            try:
                torrent_content = self._get(url, timeout=30, return_bytes=True)
                if torrent_content and torrent_content.startswith(b'd'):
                    fd, path = tempfile.mkstemp(suffix='.torrent')
                    with os.fdopen(fd, 'wb') as f:
                        f.write(torrent_content)
                    print(f"GamesTorrents: Saved torrent file to: {path}")
                    return path
            except:
                pass
            return url
        
        # If it's already a magnet link
        if url.startswith('magnet:'):
            return url
        
        # If it's a detail page, fetch the torrent link
        try:
            print(f"GamesTorrents: Resolving download from {url}")
            
            html = self._get(url, timeout=15)
            if not html:
                return url
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find torrent download link
            torrent_link = soup.find('a', href=re.compile(r'\.torrent'))
            
            if torrent_link:
                torrent_url = torrent_link.get('href', '')
                if not torrent_url.startswith('http'):
                    torrent_url = f"{self.info.url}{torrent_url}" if torrent_url.startswith('/') else f"{self.info.url}/{torrent_url}"
                
                print(f"GamesTorrents: Found torrent URL: {torrent_url}")
                
                # Download the torrent file
                torrent_content = self._get(torrent_url, timeout=30, return_bytes=True)
                
                if torrent_content and torrent_content.startswith(b'd'):
                    fd, path = tempfile.mkstemp(suffix='.torrent')
                    with os.fdopen(fd, 'wb') as f:
                        f.write(torrent_content)
                    print(f"GamesTorrents: Saved torrent file to: {path}")
                    return path
                else:
                    print("GamesTorrents: Downloaded content is not a valid torrent")
            else:
                print("GamesTorrents: No torrent link found on detail page")
                
        except Exception as e:
            print(f"GamesTorrents resolve error: {e}")
            import traceback
            traceback.print_exc()
        
        return url
    
    def _get(self, url, timeout=15, return_bytes=False):
        """Custom GET method to handle bytes response."""
        try:
            import urllib3
            urllib3.disable_warnings()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            resp = self.session.get(url, headers=headers, timeout=timeout, verify=False)
            
            if resp.status_code == 200:
                if return_bytes:
                    return resp.content
                return resp.text
            return None
        except Exception as e:
            print(f"GamesTorrents GET error: {e}")
            return None


class SkidrowRepackProvider(SearchProvider):
    """Skidrow Repack - PC game repacks and cracks."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="skidrowrepack",
            name="Skidrow Repack",
            url="https://skidrowrepack.com",
            specialized_category=Category.GAMES,
            safety_status=SearchProviderSafetyStatus.UNSAFE,
            safety_reason="Contains cracked games - use at your own risk",
            enabled_by_default=False,
            language="English",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Skidrow Repack for PC game torrents."""
        import re
        from urllib.parse import quote
        
        # Minimum 4 characters required for search
        if len(query) < 4:
            query = query + " game"  # Pad short queries
        
        # Search URL format
        url = f"{self.info.url}/index.php?do=search&subaction=search&story={quote(query)}"
        
        try:
            html = self._get(url, timeout=20)
            
            if not html:
                print("SkidrowRepack: Empty response")
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Find game links with class "mov-t" or in article/entry containers
            game_links = soup.find_all('a', class_='mov-t')
            
            # If no mov-t links, try finding links in search results
            if not game_links:
                game_links = soup.find_all('a', href=re.compile(r'/\d+-.*\.html$'))
            
            seen_urls = set()
            
            for link in game_links:
                try:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Skip duplicates and invalid entries
                    if href in seen_urls or not text or len(text) < 3:
                        continue
                    
                    seen_urls.add(href)
                    
                    # Try to find size from parent elements or nearby text
                    size = 'Unknown'
                    parent = link.find_parent(['div', 'li', 'article', 'section', 'td'])
                    if parent:
                        parent_text = parent.get_text()
                        # Look for size patterns like "12.5 GB", "800 MB", etc
                        size_match = re.search(r'(\d+(?:[.,]\d+)?\s*(?:GB|MB|TB|KB))', parent_text, re.I)
                        if size_match:
                            size = size_match.group(1).strip()
                    
                    # Build full URL if needed
                    if not href.startswith('http'):
                        href = f"{self.info.url}{href}" if href.startswith('/') else f"{self.info.url}/{href}"
                    
                    t = Torrent(
                        name=text,
                        size=size,
                        seeders=-1,
                        peers=-1,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=href,
                        magnet_uri=href,  # Store detail URL, resolve later
                        category=Category.GAMES,
                    )
                    
                    torrents.append(t)
                        
                except Exception as ex:
                    continue
            
            print(f"SkidrowRepack: Found {len(torrents)} results")
            
            # Fetch sizes from detail pages for first 25 results
            self._fetch_sizes(torrents[:25])
            
            return torrents[:50]
            
        except Exception as e:
            print(f"SkidrowRepack search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _fetch_sizes(self, torrents: List[Torrent]):
        """Fetch file sizes from detail pages in parallel."""
        import concurrent.futures
        import re
        
        def fetch_size(torrent: Torrent):
            try:
                html = self._get(torrent.description_url, timeout=15)
                if not html:
                    return
                
                content = html
                
                # Pattern 1: Free Disk Space (most common on Skidrow Repack)
                free_disk_match = re.search(r'Free\s*Disk\s*Space[:\s]*(\d+(?:[.,]\d+)?\s*(?:GB|MB|TB))', content, re.I)
                if free_disk_match:
                    torrent.size = free_disk_match.group(1).replace(',', '.')
                    return
                
                # Pattern 2: Hard disk space / HDD requirement
                hdd_match = re.search(r'(?:Hard\s*disk|HDD|Disk\s*space)[:\s]*(\d+(?:[.,]\d+)?\s*(?:GB|MB|TB))', content, re.I)
                if hdd_match:
                    torrent.size = hdd_match.group(1).replace(',', '.')
                    return
                
                # Pattern 3: Storage / Space required
                storage_match = re.search(r'(?:Storage|Space\s*required|Available\s*space)[:\s]*(\d+(?:[.,]\d+)?\s*(?:GB|MB|TB))', content, re.I)
                if storage_match:
                    torrent.size = storage_match.group(1).replace(',', '.')
                    return
                
                # Pattern 4: Repack size / Download size / Game size / File size
                repack_match = re.search(r'(?:Repack|Download|Game|File|Install|Installed)\s*(?:size)?[:\s~]+(\d+(?:[.,]\d+)?\s*(?:GB|MB|TB))', content, re.I)
                if repack_match:
                    torrent.size = repack_match.group(1).replace(',', '.')
                    return
                
                # Pattern 5: Size mentioned with approximate indicator
                approx_match = re.search(r'(?:~|about|approximately|around)\s*(\d+(?:[.,]\d+)?\s*(?:GB|MB|TB))', content, re.I)
                if approx_match:
                    torrent.size = f"~{approx_match.group(1).replace(',', '.')}"
                    return
                
                # Pattern 6: Look for largest GB value (likely game size, not RAM)
                # Skip common RAM values like "8 GB" and "16 GB"
                all_sizes = re.findall(r'(\d+(?:[.,]\d+)?)\s*(GB|MB|TB)', content, re.I)
                if all_sizes:
                    # Find the largest size in GB (excluding typical RAM values 4, 8, 16, 32)
                    ram_values = {4, 8, 16, 32}
                    best_size = None
                    best_bytes = 0
                    
                    for num_str, unit in all_sizes:
                        try:
                            num = float(num_str.replace(',', '.'))
                            unit = unit.upper()
                            
                            # Skip typical RAM values if they're exactly matching
                            if unit == 'GB' and int(num) in ram_values and num == int(num):
                                continue
                            
                            # Calculate byte value for comparison
                            if unit == 'TB':
                                bytes_val = num * 1024 * 1024 * 1024 * 1024
                            elif unit == 'GB':
                                bytes_val = num * 1024 * 1024 * 1024
                            else:  # MB
                                bytes_val = num * 1024 * 1024
                            
                            if bytes_val > best_bytes:
                                best_bytes = bytes_val
                                best_size = f"{num_str} {unit}"
                        except:
                            pass
                    
                    if best_size:
                        torrent.size = best_size
                    
            except Exception as e:
                print(f"SkidrowRepack: Error fetching size: {e}")
        
        # Fetch in parallel with max 5 workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(fetch_size, torrents)

    
    def resolve_download(self, torrent: Torrent) -> Optional[str]:
        """Resolve download by fetching .torrent file from detail page."""
        import re
        import os
        import tempfile
        
        url = torrent.magnet_uri
        if not url:
            return None
        
        # If it's already a torrent file URL
        if 'do=download' in url or url.endswith('.torrent'):
            try:
                torrent_content = self._get(url, timeout=30, return_bytes=True)
                if torrent_content and torrent_content.startswith(b'd'):
                    fd, path = tempfile.mkstemp(suffix='.torrent')
                    with os.fdopen(fd, 'wb') as f:
                        f.write(torrent_content)
                    print(f"SkidrowRepack: Saved torrent file to: {path}")
                    return path
            except:
                pass
            return url
        
        # If it's already a magnet link
        if url.startswith('magnet:'):
            return url
        
        # If it's a detail page, fetch the torrent download link
        try:
            print(f"SkidrowRepack: Resolving download from {url}")
            
            html = self._get(url, timeout=20)
            if not html:
                return url
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find torrent download link
            # Patterns: "Download .torrent" link or index.php?do=download&id=
            torrent_link = soup.find('a', href=re.compile(r'do=download'))
            if not torrent_link:
                torrent_link = soup.find('a', string=re.compile(r'Download.*torrent', re.I))
            if not torrent_link:
                torrent_link = soup.find('a', class_='dwn-load')
            
            if torrent_link:
                torrent_url = torrent_link.get('href', '')
                if not torrent_url.startswith('http'):
                    torrent_url = f"{self.info.url}{torrent_url}" if torrent_url.startswith('/') else f"{self.info.url}/{torrent_url}"
                
                print(f"SkidrowRepack: Found torrent URL: {torrent_url}")
                
                # Download the torrent file
                torrent_content = self._get(torrent_url, timeout=30, return_bytes=True)
                
                if torrent_content and torrent_content.startswith(b'd'):
                    fd, path = tempfile.mkstemp(suffix='.torrent')
                    with os.fdopen(fd, 'wb') as f:
                        f.write(torrent_content)
                    print(f"SkidrowRepack: Saved torrent file to: {path}")
                    return path
                else:
                    print("SkidrowRepack: Downloaded content is not a valid torrent")
            else:
                # Try to find magnet link as fallback
                magnet_link = soup.find('a', href=re.compile(r'^magnet:'))
                if magnet_link:
                    return magnet_link.get('href')
                print("SkidrowRepack: No torrent/magnet link found on detail page")
                
        except Exception as e:
            print(f"SkidrowRepack resolve error: {e}")
            import traceback
            traceback.print_exc()
        
        return url
    
    def _get(self, url, timeout=15, return_bytes=False):
        """Custom GET method to handle bytes response."""
        try:
            import urllib3
            urllib3.disable_warnings()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Referer': self.info.url,
            }
            
            resp = self.session.get(url, headers=headers, timeout=timeout, verify=False)
            
            if resp.status_code == 200:
                if return_bytes:
                    return resp.content
                return resp.text
            return None
        except Exception as e:
            print(f"SkidrowRepack GET error: {e}")
            return None


class FTUAppsProvider(SearchProvider):
    """FTUApps - Multilingual pre-activated and portable software torrents."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="ftuapps",
            name="FTUApps",
            url="https://ftuapps1.farlad.com",
            specialized_category=Category.APPS,
            safety_status=SearchProviderSafetyStatus.UNSAFE,
            safety_reason="Contains cracked software - use at your own risk",
            enabled_by_default=False,
            language="Multi",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search FTUApps for software torrents."""
        import re
        from urllib.parse import quote
        
        url = f"{self.info.url}/?s={quote(query)}"
        
        try:
            html = self._get(url, timeout=20)
            
            if not html:
                print("FTUApps: Empty response")
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            seen_urls = set()
            
            # Find article links - pattern varies, look for post links
            # The site uses WordPress-style URLs
            post_links = soup.find_all('a', href=re.compile(rf'{re.escape(self.info.url)}/[a-z0-9-]+/$'))
            
            for link in post_links:
                try:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Skip navigation links, tags, and duplicates
                    if '/tag/' in href or '/category/' in href or '/page/' in href:
                        continue
                    if href in seen_urls or not text or len(text) < 5:
                        continue
                    if '?' in href:  # Skip query string links
                        continue
                    
                    # Skip common navigation/static pages
                    skip_patterns = ['contact', 'privacy', 'copyright', 'terms', 'policy', 
                                    'request', 'about', 'dmca', 'disclaimer']
                    text_lower = text.lower()
                    if any(pattern in text_lower for pattern in skip_patterns):
                        continue
                    
                    # Only include if it looks like software (has version or keywords)
                    if not re.search(r'v\d+|v\.\d+|\d+\.\d+|portable|activated|crack|x64|x86', text, re.I):
                        continue
                    
                    seen_urls.add(href)
                    
                    t = Torrent(
                        name=text,
                        size='Unknown',
                        seeders=-1,
                        peers=-1,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=href,
                        magnet_uri=href,  # Store detail URL, resolve later
                        category=Category.APPS,
                    )
                    
                    torrents.append(t)
                        
                except Exception as ex:
                    continue
            
            print(f"FTUApps: Found {len(torrents)} results")
            return torrents[:50]
            
        except Exception as e:
            print(f"FTUApps search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def resolve_download(self, torrent: Torrent) -> Optional[str]:
        """Resolve download by fetching .torrent file from detail page."""
        import re
        import os
        import tempfile
        
        url = torrent.magnet_uri
        if not url:
            return None
        
        # If it's already a torrent file URL
        if url.endswith('.torrent'):
            try:
                torrent_content = self._get(url, timeout=30, return_bytes=True)
                if torrent_content and torrent_content.startswith(b'd'):
                    fd, path = tempfile.mkstemp(suffix='.torrent')
                    with os.fdopen(fd, 'wb') as f:
                        f.write(torrent_content)
                    print(f"FTUApps: Saved torrent file to: {path}")
                    return path
            except:
                pass
            return url
        
        # If it's already a magnet link
        if url.startswith('magnet:'):
            return url
        
        # If it's a detail page, fetch the torrent link
        try:
            print(f"FTUApps: Resolving download from {url}")
            
            html = self._get(url, timeout=20)
            if not html:
                return url
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find torrent download link - look for .torrent file links
            torrent_link = soup.find('a', href=re.compile(r'\.torrent$'))
            
            if torrent_link:
                torrent_url = torrent_link.get('href', '')
                if not torrent_url.startswith('http'):
                    torrent_url = f"{self.info.url}{torrent_url}" if torrent_url.startswith('/') else f"{self.info.url}/{torrent_url}"
                
                print(f"FTUApps: Found torrent URL: {torrent_url}")
                
                # Download the torrent file
                torrent_content = self._get(torrent_url, timeout=30, return_bytes=True)
                
                if torrent_content and torrent_content.startswith(b'd'):
                    fd, path = tempfile.mkstemp(suffix='.torrent')
                    with os.fdopen(fd, 'wb') as f:
                        f.write(torrent_content)
                    print(f"FTUApps: Saved torrent file to: {path}")
                    return path
                else:
                    print("FTUApps: Downloaded content is not a valid torrent")
            else:
                # Try to find magnet link as fallback
                magnet_link = soup.find('a', href=re.compile(r'^magnet:'))
                if magnet_link:
                    return magnet_link.get('href')
                print("FTUApps: No torrent/magnet link found on detail page")
                
        except Exception as e:
            print(f"FTUApps resolve error: {e}")
            import traceback
            traceback.print_exc()
        
        return url
    
    def _get(self, url, timeout=15, return_bytes=False):
        """Custom GET method to handle bytes response."""
        try:
            import urllib3
            urllib3.disable_warnings()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Referer': self.info.url,
            }
            
            resp = self.session.get(url, headers=headers, timeout=timeout, verify=False)
            
            if resp.status_code == 200:
                if return_bytes:
                    return resp.content
                return resp.text
            return None
        except Exception as e:
            print(f"FTUApps GET error: {e}")
            return None


class CroTorrentsProvider(SearchProvider):
    """CroTorrents - Free PC game torrents with quality repacks."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="crotorrents",
            name="CroTorrents",
            url="https://crotorrents.com",
            specialized_category=Category.GAMES,
            safety_status=SearchProviderSafetyStatus.SAFE,
            safety_reason="Game torrent site with clean downloads",
            enabled_by_default=True,
        )
    
    def search(self, query: str, category: Category, page: int = 1) -> List[Torrent]:
        """Search CroTorrents for games."""
        import re
        from urllib.parse import quote
        
        # WordPress search pattern
        if page == 1:
            url = f"{self.info.url}/?s={quote(query)}"
        else:
            url = f"{self.info.url}/page/{page}/?s={quote(query)}"
        
        try:
            html = self._get(url)
            if not html:
                print("CroTorrents: No HTML response")
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Search results are in article tags
            articles = soup.select('article')
            
            print(f"CroTorrents: Found {len(articles)} articles")
            
            for article in articles:
                try:
                    # Get title and link from h2 a
                    title_link = article.select_one('h2 a, h2.post-title a, .post-title a')
                    if not title_link:
                        continue
                    
                    name = title_link.get_text(strip=True)
                    href = title_link.get('href', '')
                    
                    if not name or not href:
                        continue
                    
                    # Get date if available
                    date_elem = article.select_one('time, .post-date')
                    upload_date = date_elem.get_text(strip=True) if date_elem else 'Unknown'
                    
                    t = Torrent(
                        name=name,
                        size='Unknown',  # Will fetch from detail page
                        seeders=-1,  # Not shown on search results
                        peers=-1,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date=upload_date,
                        description_url=href,
                        magnet_uri='',  # Will fetch from detail page
                        category=Category.GAMES,
                    )
                    torrents.append(t)
                except Exception as e:
                    print(f"CroTorrents: Error parsing article: {e}")
                    continue
            
            # Fetch magnet links and sizes from detail pages (first 10)
            self._fetch_details(torrents[:10])
            
            return torrents
            
        except Exception as e:
            print(f"CroTorrents search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _fetch_details(self, torrents: List[Torrent]):
        """Fetch magnet links and sizes from detail pages."""
        import concurrent.futures
        import re
        
        def fetch_detail(torrent: Torrent):
            try:
                html = self._get(torrent.description_url, timeout=15)
                if not html:
                    return
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find magnet link directly
                magnet = soup.select_one('a[href^="magnet:"]')
                if magnet:
                    torrent.magnet_uri = magnet.get('href', '')
                else:
                    # Find the download button image link
                    for img in soup.select('img'):
                        img_src = img.get('src', '').lower()
                        if 'download' in img_src and ('torrent' in img_src or '300x74' in img_src):
                            link = img.find_parent('a')
                            if link:
                                href = link.get('href', '')
                                if href.startswith('magnet:'):
                                    torrent.magnet_uri = href
                                elif href.endswith('.torrent') or 'torrent' in href:
                                    torrent.magnet_uri = href
                                break
                
                # Extract size from page content
                page_text = soup.get_text()
                
                # Try Storage: pattern first
                size_match = re.search(r'(?:Storage|Hard Drive|HDD)[:\s]+([0-9.]+\s*(?:GB|MB|TB|KB))', page_text, re.I)
                if size_match:
                    torrent.size = size_match.group(1).strip()
                else:
                    # Try generic size pattern (e.g., "File Size: 20 GB")
                    size_match = re.search(r'(?:File\s*)?Size[:\s]+([0-9.]+\s*(?:GB|MB|TB|KB))', page_text, re.I)
                    if size_match:
                        torrent.size = size_match.group(1).strip()
                        
            except Exception as e:
                print(f"CroTorrents: Error fetching detail for {torrent.name}: {e}")
        
        # Use thread pool for parallel fetching
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(fetch_detail, torrents)
    
    def resolve_download(self, torrent: Torrent) -> Optional[str]:
        """Resolve the download link from detail page if not already available."""
        import re
        
        if torrent.magnet_uri and (torrent.magnet_uri.startswith('magnet:') or torrent.magnet_uri.endswith('.torrent')):
            return torrent.magnet_uri
        
        try:
            html = self._get(torrent.description_url, timeout=20)
            if not html:
                return None
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try direct magnet link
            magnet = soup.select_one('a[href^="magnet:"]')
            if magnet:
                return magnet.get('href', '')
            
            # Try finding the download button
            for img in soup.select('img'):
                img_src = img.get('src', '').lower()
                if 'download' in img_src:
                    link = img.find_parent('a')
                    if link:
                        href = link.get('href', '')
                        if href.startswith('magnet:') or href.endswith('.torrent'):
                            return href
                        
                        # Follow redirect if it's a /go/ link
                        if '/go/' in href or 'redirect' in href.lower():
                            try:
                                resp = self.session.get(href, allow_redirects=True, timeout=15)
                                final_url = resp.url
                                if 'magnet:' in final_url or final_url.endswith('.torrent'):
                                    return final_url
                                # Check response for magnet link
                                if 'magnet:' in resp.text:
                                    mag_match = re.search(r'(magnet:\?xt=urn:btih:[a-zA-Z0-9]+[^"\'<>\s]*)', resp.text)
                                    if mag_match:
                                        return mag_match.group(1)
                            except:
                                pass
            
            return None
            
        except Exception as e:
            print(f"CroTorrents resolve error: {e}")
            return None


class PlazaPCGamesProvider(SearchProvider):
    """PlazaPCGames - Free PC game torrents from PLAZA releases."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="plazapcgames",
            name="PlazaPCGames",
            url="https://plazapcgames.com",
            specialized_category=Category.GAMES,
            safety_status=SearchProviderSafetyStatus.SAFE,
            safety_reason="Game torrent site with PLAZA releases",
            enabled_by_default=True,
        )
    
    def search(self, query: str, category: Category, page: int = 1) -> List[Torrent]:
        """Search PlazaPCGames for games."""
        import re
        from urllib.parse import quote
        
        # WordPress search pattern
        if page == 1:
            url = f"{self.info.url}/?s={quote(query)}"
        else:
            url = f"{self.info.url}/page/{page}/?s={quote(query)}"
        
        try:
            html = self._get(url)
            if not html:
                print("PlazaPCGames: No HTML response")
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            torrents = []
            
            # Search results are in article tags or similar containers
            articles = soup.select('article, .post, .hentry')
            
            print(f"PlazaPCGames: Found {len(articles)} articles")
            
            for article in articles:
                try:
                    # Get title and link
                    title_link = article.select_one('h2 a, h1 a, .entry-title a, .post-title a')
                    if not title_link:
                        continue
                    
                    name = title_link.get_text(strip=True)
                    href = title_link.get('href', '')
                    
                    if not name or not href:
                        continue
                    
                    # Skip FAQ and non-game pages
                    if 'faq' in href.lower() or 'faq' in name.lower():
                        continue
                    
                    t = Torrent(
                        name=name.replace(' Free Download', '').strip(),
                        size='Unknown',  # Will fetch from detail page
                        seeders=-1,
                        peers=-1,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=href,
                        magnet_uri='',  # Will fetch from detail page
                        category=Category.GAMES,
                    )
                    torrents.append(t)
                except Exception as e:
                    print(f"PlazaPCGames: Error parsing article: {e}")
                    continue
            
            # Fetch magnet links and sizes from detail pages (first 10)
            self._fetch_details(torrents[:10])
            
            return torrents
            
        except Exception as e:
            print(f"PlazaPCGames search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _fetch_details(self, torrents: List[Torrent]):
        """Fetch magnet links and sizes from detail pages."""
        import concurrent.futures
        import re
        
        def fetch_detail(torrent: Torrent):
            try:
                html = self._get(torrent.description_url, timeout=15)
                if not html:
                    return
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find magnet link - PlazaPCGames has direct magnet links
                magnet = soup.select_one('a[href^="magnet:"]')
                if magnet:
                    torrent.magnet_uri = magnet.get('href', '')
                    
                    # Extract info hash for tracking
                    hash_match = re.search(r'btih:([a-fA-F0-9]{40})', torrent.magnet_uri)
                    if hash_match:
                        torrent.info_hash = hash_match.group(1).lower()
                
                # Extract size from page content - format: "Size: 46.40 GB"
                page_text = soup.get_text()
                size_match = re.search(r'Size[:\s]+([0-9.]+\s*(?:GB|MB|TB|KB))', page_text, re.I)
                if size_match:
                    torrent.size = size_match.group(1).strip()
                        
            except Exception as e:
                print(f"PlazaPCGames: Error fetching detail for {torrent.name}: {e}")
        
        # Use thread pool for parallel fetching
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(fetch_detail, torrents)
    
    def resolve_download(self, torrent: Torrent) -> Optional[str]:
        """Resolve the download link from detail page if not already available."""
        import re
        
        if torrent.magnet_uri and torrent.magnet_uri.startswith('magnet:'):
            return torrent.magnet_uri
        
        try:
            html = self._get(torrent.description_url, timeout=20)
            if not html:
                return None
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try direct magnet link
            magnet = soup.select_one('a[href^="magnet:"]')
            if magnet:
                return magnet.get('href', '')
            
            # Also try looking for magnet pattern in the page text
            mag_match = re.search(r'(magnet:\?xt=urn:btih:[a-zA-Z0-9]+[^"\'<>\s]*)', html)
            if mag_match:
                return mag_match.group(1)
            
            return None
            
        except Exception as e:
            print(f"PlazaPCGames resolve error: {e}")
            return None
