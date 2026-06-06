class MyPornClubProvider(SearchProvider):
    """MyPorn.Club provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="mypornclub",
            name="MyPorn.Club",
            url="https://myporn.club",
            specialized_category=Category.ADULT,
            safety_status=SearchProviderSafetyStatus.NSFW,
            enabled_by_default=True,
        )

    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search MyPorn.Club."""
        from urllib.parse import quote
        
        url = f"{self.info.url}/s/{quote(query)}"
        
        try:
            self._ensure_proxy()
            html = self._get(url)
            if not html:
                return []
                
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            torrents = []
            elements = soup.select('.torrents_list .torrent_element')
            
            for el in elements:
                try:
                    # Find title and link
                    title_a = el.select_one('.torrent_element_text_div a:not(.uploader_tel)')
                    if not title_a:
                        # Fallback for some structures
                        title_a = el.select_one('a[href^="/t/"]')
                        if not title_a:
                            continue
                            
                    name = title_a.get('title') or title_a.get_text(strip=True)
                    desc_url = title_a['href']
                    if not desc_url.startswith('http'):
                        desc_url = self.info.url + desc_url
                        
                    # Find stats (size, date, seeders, peers)
                    info_div = el.select_one('.torrent_element_info')
                    size = 'Unknown'
                    upload_date = 'Unknown'
                    seeders = 0
                    peers = 0
                    
                    if info_div:
                        # Upload date is in the first .teiv > a
                        date_a = info_div.select_one('.teiv a')
                        if date_a:
                            upload_date = date_a.get_text(strip=True)
                            
                        # Seeders and leechers
                        seeders_el = info_div.select_one('.teiv_seeders')
                        if seeders_el and seeders_el.get_text(strip=True).isdigit():
                            seeders = int(seeders_el.get_text(strip=True))
                            
                        leechers_el = info_div.select_one('.teiv_leechers')
                        if leechers_el and leechers_el.get_text(strip=True).isdigit():
                            peers = int(leechers_el.get_text(strip=True))
                            
                        # Size is usually the text of the .teiv following the [size]: span
                        # Since they don't have unique classes, we can search for siblings
                        teis_spans = info_div.select('.teis')
                        for span in teis_spans:
                            if '[size]' in span.get_text().lower():
                                size_span = span.find_next_sibling('.teiv')
                                if size_span:
                                    size = size_span.get_text(strip=True)
                                break
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeders,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date=upload_date,
                        description_url=desc_url,
                        magnet_uri='', # Fetched on demand
                        category=Category.ADULT,
                    )
                    torrents.append(t)
                except Exception:
                    continue
                    
            return torrents
            
        except Exception as e:
            print(f"MyPornClub search error: {e}")
            return []

    def resolve_download(self, torrent: Torrent) -> Optional[str]:
        """Fetch magnet from detail page if possible."""
        if torrent.magnet_uri:
            return torrent.magnet_uri
            
        if not torrent.description_url:
            return None
            
        try:
            html = self._get(torrent.description_url, timeout=10)
            if not html:
                return None
                
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            magnet_elem = soup.find('a', href=lambda h: h and h.startswith('magnet:'))
            if magnet_elem:
                torrent.magnet_uri = magnet_elem['href']
                return torrent.magnet_uri
                
        except Exception:
            pass
            
        return None
