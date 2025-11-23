"""Bookmark management using SQLite."""

import sqlite3
import os
from typing import List, Set


class BookmarkManager:
    """Manages torrent bookmarks using SQLite."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use user's home directory
            home = os.path.expanduser("~")
            app_dir = os.path.join(home, ".swiftseed")
            os.makedirs(app_dir, exist_ok=True)
            db_path = os.path.join(app_dir, "bookmarks.db")
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                magnet_uri TEXT NOT NULL,
                size TEXT,
                seeders INTEGER,
                peers INTEGER,
                provider TEXT,
                upload_date TEXT,
                category TEXT,
                description_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_bookmark(self, torrent) -> bool:
        """Add a torrent to bookmarks."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO bookmarks 
                (name, magnet_uri, size, seeders, peers, provider, upload_date, category, description_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                torrent.name,
                torrent.get_magnet_uri(),
                torrent.size,
                torrent.seeders,
                torrent.peers,
                torrent.provider_name,
                torrent.upload_date,
                str(torrent.category) if torrent.category else None,
                torrent.description_url,
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding bookmark: {e}")
            return False
    
    def remove_bookmark(self, name: str) -> bool:
        """Remove a bookmark by torrent name."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM bookmarks WHERE name = ?', (name,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error removing bookmark: {e}")
            return False
    
    def is_bookmarked(self, name: str) -> bool:
        """Check if a torrent is bookmarked."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM bookmarks WHERE name = ?', (name,))
            count = cursor.fetchone()[0]
            
            conn.close()
            return count > 0
        except Exception as e:
            print(f"Error checking bookmark: {e}")
            return False
    
    def get_bookmarks(self) -> List[dict]:
        """Get all bookmarks."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM bookmarks 
                ORDER BY created_at DESC
            ''')
            
            bookmarks = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return bookmarks
        except Exception as e:
            print(f"Error getting bookmarks: {e}")
            return []
    
    def get_bookmarked_names(self) -> Set[str]:
        """Get set of all bookmarked torrent names."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT name FROM bookmarks')
            names = {row[0] for row in cursor.fetchall()}
            
            conn.close()
            return names
        except Exception as e:
            print(f"Error getting bookmarked names: {e}")
            return set()
