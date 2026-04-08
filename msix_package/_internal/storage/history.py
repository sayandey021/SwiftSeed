"""Search history management using SQLite."""

import sqlite3
import os
from typing import List, Dict
from datetime import datetime


class SearchHistoryManager:
    """Manages search history using SQLite."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use user's home directory
            home = os.path.expanduser("~")
            app_dir = os.path.join(home, ".swiftseed")
            os.makedirs(app_dir, exist_ok=True)
            db_path = os.path.join(app_dir, "history.db")
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                category TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index on query for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_query 
            ON search_history(query)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_search(self, query: str, category: str = "All"):
        """Add a search to history."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO search_history (query, category)
                VALUES (?, ?)
            ''', (query, category))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding search to history: {e}")
            return False
    
    def get_recent_searches(self, limit: int = 20) -> List[Dict]:
        """Get recent searches."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT query, category, MAX(timestamp) as last_used
                FROM search_history
                GROUP BY query, category
                ORDER BY last_used DESC
                LIMIT ?
            ''', (limit,))
            
            searches = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return searches
        except Exception as e:
            print(f"Error getting recent searches: {e}")
            return []
    
    def search_history(self, filter_text: str) -> List[Dict]:
        """Search within history."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT query, category, MAX(timestamp) as last_used
                FROM search_history
                WHERE query LIKE ?
                GROUP BY query, category
                ORDER BY last_used DESC
                LIMIT 50
            ''', (f'%{filter_text}%',))
            
            searches = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return searches
        except Exception as e:
            print(f"Error searching history: {e}")
            return []
    
    def delete_search(self, query: str):
        """Delete all instances of a search query."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM search_history WHERE query = ?', (query,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting search: {e}")
            return False
    
    def clear_all(self):
        """Clear all search history."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM search_history')
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error clearing history: {e}")
            return False
    
    def get_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on prefix."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT query
                FROM search_history
                WHERE query LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (f'{prefix}%', limit))
            
            suggestions = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return suggestions
        except Exception as e:
            print(f"Error getting suggestions: {e}")
            return []
