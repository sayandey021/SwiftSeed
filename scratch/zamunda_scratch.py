class ZamundaRipProvider(SearchProvider):
    """Zamunda.RIP provider (uses JSON API)."""
    
    @property
    def info(self) -> SearchProviderInfo:
        return SearchProviderInfo(
            id="zamundarip",
            name="Zamunda.RIP",
            url="https://zamunda.rip",
            specialized_category=Category.ALL,
            safety_status=SearchProviderSafetyStatus.SAFE,
            enabled_by_default=True,
            language="Bulgarian",
        )

    def search(self, query: str, category: Category) -> List[Torrent]:
        """Search Zamunda.RIP via JSON API."""
        from urllib.parse import quote
        import json
        
        url = f"{self.info.url}/api/torrents?q={quote(query)}"
        
        try:
            self._ensure_proxy()
            response = self._get(url)
            if not response:
                return []
                
            data = json.loads(response)
            if not isinstance(data, list):
                return []
                
            torrents = []
            for item in data:
                try:
                    name = item.get('title', 'Unknown')
                    magnet_uri = item.get('link', '')
                    size = item.get('size', 'Unknown')
                    
                    # They don't provide seeders/leechers in the basic API
                    seeders = 0
                    peers = 0
                    
                    t = Torrent(
                        name=name,
                        size=size,
                        seeders=seeders,
                        peers=peers,
                        provider_id=self.info.id,
                        provider_name=self.info.name,
                        upload_date='Unknown',
                        description_url=f"{self.info.url}/download?id={item.get('external_id', '')}",
                        magnet_uri=magnet_uri,
                        category=Category.ALL,
                    )
                    torrents.append(t)
                except Exception:
                    continue
                    
            return torrents
            
        except Exception as e:
            print(f"Zamunda.RIP search error: {e}")
            return []
