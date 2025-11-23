"""Base search provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
from enum import Enum
import requests
from models.torrent import Torrent
from models.category import Category


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


class SearchProvider(ABC):
    """Abstract base class for torrent search providers."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    @property
    @abstractmethod
    def info(self) -> SearchProviderInfo:
        """Get provider information."""
        pass
    
    @abstractmethod
    def search(self, query: str, category: Category) -> List[Torrent]:
        """
        Search for torrents.
        
        Args:
            query: Search query string
            category: Category to filter by
            
        Returns:
            List of Torrent objects
        """
        pass
    
    def _get(self, url: str, timeout: int = 10) -> str:
        """Make HTTP GET request."""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return ""
    
    def _get_json(self, url: str, timeout: int = 10) -> dict:
        """Make HTTP GET request and parse JSON."""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching JSON from {url}: {e}")
            return {}
