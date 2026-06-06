class NekobtProvider(SearchProvider):
    """Nekobt.to provider."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="nekobt",
            name="Nekobt",
            url="https://nekobt.to",
            specialized_category=Category.ANIME,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
        )

    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Nekobt."""
        from urllib.parse import quote
        
        url = f"{self.info.url}/search?q={quote(query)}"
        
        try:
            self._ensure_proxy()
            html = self._get(url)
            if not html:
                return []
                
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            tbody = soup.find('tbody')
            if not tbody:
                return []
                
            torrents = []
            rows = tbody.find_all('tr')
            
            for row in rows:
                try:
                    cols = row.find_all('td')
                    if len(cols) < 7:
                        continue
                        
                    # Find title link
                    title_a = cols[2].find('a', href=lambda h: h and h.startswith('/torrents/'))
                    if not title_a:
                        continue
                        
                    # Title text may contain nested spans, so grab the first meaningful text
                    name_raw = title_a.get_text(separator='\n', strip=True)
                    name = name_raw.split('\n')[0].strip() if name_raw else 'Unknown'
                    
                    desc_url = title_a['href']
                    if not desc_url.startswith('http'):
                        desc_url = self.info.url + desc_url
                        
                    # Magnet link
                    magnet_a = row.find('a', href=lambda h: h and h.startswith('magnet:'))
                    magnet_uri = magnet_a['href'] if magnet_a else ''
                    
                    # Size, Date, Seeders, Leechers are in fixed columns based on structure
                    size = cols[4].get_text(strip=True) if len(cols) > 4 else 'Unknown'
                    upload_date = cols[5].get_text(strip=True) if len(cols) > 5 else 'Unknown'
                    
                    seeders_str = cols[6].get_text(strip=True) if len(cols) > 6 else '0'
                    leechers_str = cols[7].get_text(strip=True) if len(cols) > 7 else '0'
                    
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
            print(f"Nekobt search error: {e}")
            return []

