"""Custom provider management using SQLite."""

import sqlite3
import os
from typing import List, Dict, Optional


class CustomProviderManager:
    """Manages custom torrent search providers (Torznab compatible)."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use user's home directory
            home = os.path.expanduser("~")
            app_dir = os.path.join(home, ".swiftseed")
            os.makedirs(app_dir, exist_ok=True)
            db_path = os.path.join(app_dir, "providers.db")
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_providers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                base_url TEXT NOT NULL,
                api_key TEXT,
                provider_type TEXT DEFAULT 'torznab',
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_provider(self, name: str, base_url: str, api_key: str = "", 
                     provider_type: str = "torznab") -> bool:
        """Add a custom provider."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO custom_providers (name, base_url, api_key, provider_type)
                VALUES (?, ?, ?, ?)
            ''', (name, base_url, api_key, provider_type))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            print(f"Provider '{name}' already exists")
            return False
        except Exception as e:
            print(f"Error adding provider: {e}")
            return False
    
    def update_provider(self, provider_id: int, name: str, base_url: str, 
                       api_key: str = "", enabled: bool = True) -> bool:
        """Update an existing provider."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE custom_providers
                SET name = ?, base_url = ?, api_key = ?, enabled = ?
                WHERE id = ?
            ''', (name, base_url, api_key, enabled, provider_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating provider: {e}")
            return False
    
    def delete_provider(self, provider_id: int) -> bool:
        """Delete a provider."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM custom_providers WHERE id = ?', (provider_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting provider: {e}")
            return False
    
    def get_providers(self, enabled_only: bool = False) -> List[Dict]:
        """Get all custom providers."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if enabled_only:
                cursor.execute('''
                    SELECT * FROM custom_providers
                    WHERE enabled = 1
                    ORDER BY name
                ''')
            else:
                cursor.execute('''
                    SELECT * FROM custom_providers
                    ORDER BY name
                ''')
            
            providers = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return providers
        except Exception as e:
            print(f"Error getting providers: {e}")
            return []
    
    def get_provider(self, provider_id: int) -> Optional[Dict]:
        """Get a specific provider."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM custom_providers WHERE id = ?', (provider_id,))
            row = cursor.fetchone()
            
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"Error getting provider: {e}")
            return None
    
    def toggle_provider(self, provider_id: int) -> bool:
        """Toggle provider enabled state."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE custom_providers
                SET enabled = NOT enabled
                WHERE id = ?
            ''', (provider_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error toggling provider: {e}")
            return False
