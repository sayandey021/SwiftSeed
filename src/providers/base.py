"""Base search provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
import requests
import urllib3
import os
import json
from models.torrent import Torrent
from models.category import Category

# Suppress SSL warnings for sites with certificate issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SearchProviderSafetyStatus(Enum):
    """Safety status of a search provider."""
    SAFE = "safe"
    UNSAFE = "unsafe"


@dataclass
class SearchProviderInfo:
    """Information about a search provider."""
    
    id: str
    name: str
    url: str
    specialized_category: Category
    safety_status: SearchProviderSafetyStatus
    safety_reason: str = ""
    enabled_by_default: bool = True
    language: str = "Multi"


def get_proxy_settings():
    """Load proxy settings from settings.json."""
    try:
        # Try to find settings.json in user data or current directory
        settings_paths = [
            os.path.join(os.path.expanduser("~"), ".swiftseed", "settings.json"),
            os.path.join(os.path.dirname(__file__), "..", "settings.json"),
            "settings.json"
        ]
        
        for path in settings_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    settings = json.load(f)
                    
                    if settings.get('proxy_enabled', False):
                        proxy_host = settings.get('proxy_host', '')
                        proxy_port = settings.get('proxy_port', '')
                        proxy_type = settings.get('proxy_type', 'HTTP').upper()
                        proxy_username = settings.get('proxy_username', '')
                        proxy_password = settings.get('proxy_password', '')
                        
                        if proxy_host:
                            # Build proxy URL
                            if proxy_username and proxy_password:
                                auth = f"{proxy_username}:{proxy_password}@"
                            else:
                                auth = ""
                            
                            port_str = f":{proxy_port}" if proxy_port else ""
                            
                            if proxy_type in ['SOCKS5', 'SOCKS4']:
                                proxy_url = f"socks5://{auth}{proxy_host}{port_str}"
                            else:
                                proxy_url = f"http://{auth}{proxy_host}{port_str}"
                            
                            return {
                                'http': proxy_url,
                                'https': proxy_url
                            }

                break
    except Exception as e:
        print(f"Error loading proxy settings: {e}")
    
    return None


class SearchProvider(ABC):
    """Abstract base class for torrent search providers."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self._proxy_configured = False

    def _ensure_proxy(self):
        """Apply proxy settings if not already configured"""
        if self._proxy_configured:
            return

        try:
            proxy_settings = get_proxy_settings()
            if proxy_settings:
                self.session.proxies = proxy_settings
            # We don't set _proxy_configured to True if None is returned, 
            # so we retry next time (e.g. if proxy was found in background)
            if proxy_settings:
                self._proxy_configured = True
        except Exception as e:
            print(f"Error applying proxy: {e}")
    
    @property
    @abstractmethod
    def info(self) -> SearchProviderInfo:
        """Get provider information."""
        pass
    
    @abstractmethod
    def search(self, query: str, category: Category, page: int = 1) -> List[Torrent]:
        """
        Search for torrents.
        
        Args:
            query: Search query string
            category: Category to filter by
            page: Page number (1-based)
        
        Returns:
            List of Torrent objects
        """
        pass
        
    def resolve_download(self, torrent: Torrent) -> Optional[str]:
        """
        Resolve the download link or file for a torrent.
        Returns a magnet URI, a HTTP URL to a .torrent file, or a local file path.
        
        Can be overridden by providers that need to fetch the magnet/file 
        using specific sessions, cookies, or extra scraping (e.g. E-Hentai).
        """
        return torrent.get_magnet_uri()
    
    def _get(self, url: str, timeout: int = 12) -> str:
        """Make HTTP GET request."""
        self._ensure_proxy()
        try:
            response = self.session.get(url, timeout=timeout, verify=False)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return ""
    
    def _get_json(self, url: str, timeout: int = 12) -> dict:
        """Make HTTP GET request and parse JSON."""
        self._ensure_proxy()
        try:
            response = self.session.get(url, timeout=timeout, verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching JSON from {url}: {e}")
            return {}
