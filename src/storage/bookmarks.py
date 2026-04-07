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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sort_order INTEGER DEFAULT 0
            )
        ''')
        
        # Check if sort_order column exists (migration for existing DBs)
        cursor.execute("PRAGMA table_info(bookmarks)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'sort_order' not in columns:
            print("Migrating database: adding sort_order column")
            cursor.execute("ALTER TABLE bookmarks ADD COLUMN sort_order INTEGER DEFAULT 0")
            # Initialize sort_order based on id to maintain insertion order (newest first)
            cursor.execute("UPDATE bookmarks SET sort_order = id")
            
        conn.commit()
        conn.close()
    
    def add_bookmark(self, torrent) -> bool:
        """Add a torrent to bookmarks."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get max sort_order
            cursor.execute("SELECT MAX(sort_order) FROM bookmarks")
            result = cursor.fetchone()
            max_order = result[0] if result[0] is not None else 0
            next_order = max_order + 1
            
            cursor.execute('''
                INSERT INTO bookmarks 
                (name, magnet_uri, size, seeders, peers, provider, upload_date, category, description_url, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                next_order
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
                ORDER BY sort_order DESC
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

    def clear_all(self) -> bool:
        """Delete all bookmarks."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM bookmarks')
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error clearing bookmarks: {e}")
            return False

    def reorder_bookmarks(self, old_index: int, new_index: int) -> bool:
        """
        Reorder bookmarks based on the display-level old and new indices.
        Updates all sort_orders in the database.
        """
        try:
            # 1. Get all bookmarks in current order
            bookmarks = self.get_bookmarks()
            if not bookmarks or old_index >= len(bookmarks) or new_index >= len(bookmarks):
                return False
            
            # 2. Reorder in-memory list
            item = bookmarks.pop(old_index)
            bookmarks.insert(new_index, item)
            
            # 3. Update database sort_orders
            # top of list gets highest sort_order
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Use a descending range to match the ORDER BY sort_order DESC
            total = len(bookmarks)
            for i, b in enumerate(bookmarks):
                new_order = total - i
                cursor.execute("UPDATE bookmarks SET sort_order = ? WHERE id = ?", (new_order, b['id']))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error reordering bookmarks: {e}")
            return False
