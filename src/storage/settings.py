"""Settings management using JSON."""

import json
import os
from typing import Dict, Any


class SettingsManager:
    """Manages application settings using JSON file."""
    
    def __init__(self, settings_path: str = None):
        if settings_path is None:
            # Use user's home directory
            home = os.path.expanduser("~")
            app_dir = os.path.join(home, ".swiftseed")
            os.makedirs(app_dir, exist_ok=True)
            settings_path = os.path.join(app_dir, "settings.json")
        
        self.settings_path = settings_path
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file."""
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading settings: {e}")
        
        # Return defaults
        return {
            'enabled_providers': ['nyaasi', '1337x', 'torrentscsv'],
            'default_category': 'All',
            'window_width': 1200,
            'window_height': 700,
        }
    
    def _save_settings(self):
        """Save settings to file."""
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a setting value."""
        self.settings[key] = value
        self._save_settings()
    
    def get_enabled_providers(self) -> list:
        """Get list of enabled provider IDs."""
        return self.get('enabled_providers', [])
    
    def set_enabled_providers(self, provider_ids: list):
        """Set enabled provider IDs."""
        self.set('enabled_providers', provider_ids)
    
    def is_provider_enabled(self, provider_id: str) -> bool:
        """Check if a provider is enabled."""
        return provider_id in self.get_enabled_providers()
    
    def toggle_provider(self, provider_id: str):
        """Toggle a provider's enabled state."""
        enabled = self.get_enabled_providers()
        if provider_id in enabled:
            enabled.remove(provider_id)
        else:
            enabled.append(provider_id)
        self.set_enabled_providers(enabled)

    def get_provider_url(self, provider_id: str) -> str:
        """Get saved URL override for a provider."""
        urls = self.get('provider_urls', {})
        return urls.get(provider_id)

    def set_provider_url(self, provider_id: str, url: str):
        """Save URL override for a provider."""
        urls = self.get('provider_urls', {})
        urls[provider_id] = url
        self.set('provider_urls', urls)
