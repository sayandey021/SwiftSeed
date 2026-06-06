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
        """Search SolidTorrents via API."""
        url = f"{self.info.url}/api/v1/search?q={query}"
        
        try:
            data = self._get_json(url)
            if not data or not data.get('success'):
                return []
            
            results = data.get('results', [])
            torrents = []
            
            for item in results:
                try:
                    title = item.get('title', 'Unknown')
                    infohash = item.get('infohash', '')
                    if not infohash:
                        continue
                    
                    size_bytes = item.get('size', 0)
                    if size_bytes > 1073741824:
                        size = f"{size_bytes / 1073741824:.2f} GB"
                    elif size_bytes > 1048576:
                        size = f"{size_bytes / 1048576:.2f} MB"
                    else:
                        size = f"{size_bytes / 1024:.2f} KB"
                        
                    seeders = item.get('seeders', 0)
                    peers = item.get('leechers', 0)
                    
                    import urllib.parse
                    safe_title = urllib.parse.quote(title)
                    magnet_uri = f"magnet:?xt=urn:btih:{infohash}&dn={safe_title}"
                    
                    t = Torrent(
                        name=title,
                        size=size,
                        seeders=seeders,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date=item.get('updatedAt', 'Unknown'),
                        description_url=f"{self.info.url}/search?q={query}",
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


class PirateiroProvider(SearchProvider):
    """Pirateiro provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="pirateiro",
            name="Pirateiro",
            url="https://pirateiro.io",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
            language="Multi",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Pirateiro."""
        from urllib.parse import quote
        
        url = f"{self.info.url}/search?query={quote(query)}"
        
        try:
            html = self._get(url)
            if not html:
                return []
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('table tr.odd, table tr.even')
            if not rows:
                rows = soup.select('table tr')
            
            torrents = []
            pending_torrents = []
            
            for row in rows:
                try:
                    cols = row.find_all('td')
                    if len(cols) < 3:
                        continue
                    
                    title_link = cols[1].find('a')
                    if not title_link:
                        continue
                    
                    name = title_link.get_text(strip=True)
                    desc_url = title_link.get('href', '')
                    if not desc_url.startswith('http'):
                        desc_url = self.info.url + desc_url
                        
                    badge_div = cols[2].select_one('.badge-div')
                    seeds = 0
                    peers = 0
                    if badge_div:
                        badges = badge_div.find_all('.badge')
                        if len(badges) >= 2:
                            s_text = badges[0].get_text(strip=True)
                            p_text = badges[1].get_text(strip=True)
                            if s_text.isdigit(): seeds = int(s_text)
                            if p_text.isdigit(): peers = int(p_text)
                            
                    t = Torrent(
                        name=name,
                        size='Unknown',
                        seeders=seeds,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri='',
                        category=Category.ALL,
                    )
                    pending_torrents.append(t)
                except Exception:
                    continue
                    
            pending_torrents = pending_torrents[:15]
            
            if pending_torrents:
                self._fetch_magnets_parallel(pending_torrents)
                
            torrents = [t for t in pending_torrents if t.magnet_uri]
            return torrents
            
        except Exception as e:
            print(f"Pirateiro search error: {e}")
            return []

    def _fetch_magnets_parallel(self, torrents: List[Torrent]):
        """Fetch magnet links from detail pages in parallel."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import re
        from bs4 import BeautifulSoup
        
        def fetch_detail(torrent: Torrent):
            try:
                detail_html = self._get(torrent.description_url, timeout=10)
                if not detail_html:
                    return
                
                detail_soup = BeautifulSoup(detail_html, 'html.parser')
                
                magnet_elem = detail_soup.select_one('a[href^="magnet:"]')
                if magnet_elem:
                    torrent.magnet_uri = magnet_elem.get('href', '')
                
                size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:GB|MB|KB|TB|GiB|MiB|Gb|Mb))', detail_html, re.IGNORECASE)
                if size_match:
                    torrent.size = size_match.group(1)
            except Exception:
                pass
                
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_detail, t) for t in torrents]
            for future in as_completed(futures, timeout=30):
                try:
                    future.result()
                except:
                    pass


class DamagNetProvider(SearchProvider):
    """Damag.net DHT provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="damagnet",
            name="Da MagNet",
            url="https://damag.net",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
            language="Multi",
        )

    def _format_size(self, size_bytes: int) -> str:
        """Format bytes to human readable size."""
        if size_bytes == 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Damag.net."""
        try:
            # Requires a POST request to search
            self._ensure_proxy()
            response = self.session.post(
                f"{self.info.url}/",
                data={'q': query, 'wanted': '50', 'token': ''},
                timeout=15,
                verify=False
            )
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')
            if not table:
                return []
                
            torrents = []
            rows = table.find_all('tr')
            
            for row in rows[1:]: # Skip header row
                try:
                    cols = row.find_all('td')
                    if len(cols) < 3:
                        continue
                        
                    title_link = cols[0].find('a')
                    if not title_link:
                        continue
                        
                    name = title_link.get_text(strip=True)
                    desc_url = title_link.get('href', '')
                    if desc_url and not desc_url.startswith('http'):
                        desc_url = self.info.url + desc_url
                        
                    # Extract size
                    size_span = cols[2].find('span', class_='label')
                    size_str = 'Unknown'
                    if size_span:
                        try:
                            size_bytes = int(size_span.get_text(strip=True))
                            size_str = self._format_size(size_bytes)
                        except ValueError:
                            pass
                            
                    t = Torrent(
                        name=name,
                        size=size_str,
                        seeders=0,  # Damag.net does not provide seeder count
                        peers=0,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=desc_url,
                        magnet_uri='', # Deferred due to Cloudflare protection on detail pages
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except Exception:
                    continue
                    
            return torrents
            
        except Exception as e:
            print(f"Damag.net search error: {e}")
            return []

    def resolve_download(self, torrent: Torrent) -> Optional[str]:
        """Fetch magnet from detail page if possible."""
        if torrent.magnet_uri:
            return torrent.magnet_uri
            
        if not torrent.description_url:
            return None
            
        try:
            # We try to fetch the detail page, but it may be blocked by Cloudflare (403).
            # If so, we just return None and let SwiftSeed handle the fallback
            # which correctly prompts the user to open the description URL.
            html = self._get(torrent.description_url, timeout=10)
            if not html:
                return None
                
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            magnet_elem = soup.select_one('a[href^="magnet:"]')
            if magnet_elem:
                torrent.magnet_uri = magnet_elem.get('href', '')
                return torrent.magnet_uri
                
        except Exception:
            pass
            
        return None


class Torrent911Provider(SearchProvider):
    """Torrent911 provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="torrent911",
            name="Torrent911",
            url="https://www.torrent911.app",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
            language="French",
        )
    
    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Torrent911."""
        try:
            self._ensure_proxy()
            
            response = self.session.post(
                f"{self.info.url}/search_torrent/",
                data={'torrentSearch': query},
                timeout=15,
                verify=False
            )
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            torrents = []
            pending_torrents = []
            
            result_items = soup.select('.banner-byx li')
            
            for item in result_items:
                try:
                    title_elem = item.select_one('.banner-title a')
                    if not title_elem:
                        continue
                        
                    name = title_elem.get('title') or title_elem.get_text(strip=True)
                    desc_url = title_elem.get('href', '')
                    if desc_url and not desc_url.startswith('http'):
                        desc_url = self.info.url + desc_url
                        
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
                    pending_torrents.append(t)
                except Exception:
                    continue
                    
            pending_torrents = pending_torrents[:15]
            
            if pending_torrents:
                self._fetch_magnets_parallel(pending_torrents)
                
            torrents = [t for t in pending_torrents if t.magnet_uri]
            return torrents
            
        except Exception as e:
            print(f"Torrent911 search error: {e}")
            return []

    def _fetch_magnets_parallel(self, torrents: List[Torrent]):
        """Fetch magnet links and metadata from detail pages in parallel."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from bs4 import BeautifulSoup
        
        def fetch_detail(torrent: Torrent):
            try:
                detail_html = self._get(torrent.description_url, timeout=10)
                if not detail_html:
                    return
                
                detail_soup = BeautifulSoup(detail_html, 'html.parser')
                
                magnet_elem = detail_soup.select_one('a[href^="magnet:"]')
                if magnet_elem:
                    torrent.magnet_uri = magnet_elem.get('href', '')
                
                tds = detail_soup.find_all('td')
                for td in tds:
                    td_text = td.get_text(strip=True)
                    if 'Poids' in td_text:
                        next_td = td.find_next_sibling('td')
                        if next_td:
                            size_str = next_td.get_text(strip=True).upper()
                            size_str = size_str.replace('GO', 'GB').replace('MO', 'MB').replace('KO', 'KB')
                            torrent.size = size_str
                    elif 'Seeders' in td_text:
                        next_td = td.find_next_sibling('td')
                        if next_td and next_td.get_text(strip=True).isdigit():
                            torrent.seeders = int(next_td.get_text(strip=True))
                    elif 'Leechers' in td_text:
                        next_td = td.find_next_sibling('td')
                        if next_td and next_td.get_text(strip=True).isdigit():
                            torrent.peers = int(next_td.get_text(strip=True))
            except Exception:
                pass
                
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_detail, t) for t in torrents]
            for future in as_completed(futures, timeout=30):
                try:
                    future.result()
                except:
                    pass
