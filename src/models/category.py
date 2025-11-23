"""Category enum for torrent classification."""

from enum import Enum


class Category(Enum):
    """Torrent categories."""
    
    ALL = ("All", False)
    ANIME = ("Anime", False)
    APPS = ("Apps", False)
    BOOKS = ("Books", False)
    GAMES = ("Games", False)
    MOVIES = ("Movies", False)
    MUSIC = ("Music", False)
    PORN = ("Porn", True)
    SERIES = ("Series", False)
    TV = ("TV", False)  # Alias for Series
    OTHER = ("Other", True)
    
    def __init__(self, display_name: str, is_nsfw: bool):
        self.display_name = display_name
        self.is_nsfw = is_nsfw
    
    def __str__(self):
        return self.display_name
    
    @classmethod
    def from_string(cls, name: str):
        """Get category from string name."""
        for category in cls:
            if category.display_name.lower() == name.lower():
                return category
        return cls.ALL
