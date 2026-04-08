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

    def move_bookmark(self, bookmark_id: int, direction: str) -> bool:
        """
        Move bookmark 'up' or 'down'.
        'up' means moving towards the top of the list (higher sort_order).
        'down' means moving towards the bottom of the list (lower sort_order).
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current bookmark's order
            cursor.execute("SELECT sort_order FROM bookmarks WHERE id = ?", (bookmark_id,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False
            current_order = result[0]
            
            if direction == 'up':
                # Find the bookmark with the closest sort_order GREATER than current (since we sort DESC)
                cursor.execute("SELECT id, sort_order FROM bookmarks WHERE sort_order > ? ORDER BY sort_order ASC LIMIT 1", (current_order,))
            else: # down
                # Find the bookmark with the closest sort_order LESS than current
                cursor.execute("SELECT id, sort_order FROM bookmarks WHERE sort_order < ? ORDER BY sort_order DESC LIMIT 1", (current_order,))
                
            swap_target = cursor.fetchone()
            if swap_target:
                target_id, target_order = swap_target
                # Swap
                cursor.execute("UPDATE bookmarks SET sort_order = ? WHERE id = ?", (target_order, bookmark_id))
                cursor.execute("UPDATE bookmarks SET sort_order = ? WHERE id = ?", (current_order, target_id))
                conn.commit()
                conn.close()
                return True
            
            conn.close()
            return False
        except Exception as e:
            print(f"Error moving bookmark: {e}")
            return False
