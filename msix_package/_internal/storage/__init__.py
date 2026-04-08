"""Storage components for persistence."""

from storage.bookmarks import BookmarkManager
from storage.settings import SettingsManager
from storage.history import SearchHistoryManager
from storage.custom_providers import CustomProviderManager

__all__ = ['BookmarkManager', 'SettingsManager', 'SearchHistoryManager', 'CustomProviderManager']
