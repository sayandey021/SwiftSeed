import json
import os
from typing import List, Dict
from ..managers.download_manager import DownloadItem, DownloadStatus # Relative import

class DownloadHistoryManager:
    def __init__(self, data_file_path: str = None):
        if data_file_path is None:
            home = os.path.expanduser("~")
            app_dir = os.path.join(home, ".torrentsearch")
            os.makedirs(app_dir, exist_ok=True)
            self.data_file = os.path.join(app_dir, "downloads_history.json")
        else:
            self.data_file = data_file_path
        
        self.downloads_data: List[Dict] = []
        self._load_data()

    def _load_data(self):
        """Loads download history from the JSON file."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.downloads_data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error decoding downloads history JSON: {e}")
                self.downloads_data = []
            except Exception as e:
                print(f"Error loading downloads history: {e}")
                self.downloads_data = []

    def _save_data(self):
        """Saves current download history to the JSON file."""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.downloads_data, f, indent=4)
        except Exception as e:
            print(f"Error saving downloads history: {e}")

    def add_download(self, download_item: DownloadItem):
        """Adds a download item to history and saves."""
        # Convert DownloadItem to dictionary for serialization
        item_dict = download_item.to_dict() 
        # Check if an item with the same ID already exists and update it
        for i, existing_item in enumerate(self.downloads_data):
            if existing_item.get('id') == item_dict['id']:
                self.downloads_data[i] = item_dict
                self._save_data()
                return
        self.downloads_data.append(item_dict)
        self._save_data()

    def update_download(self, download_item: DownloadItem):
        """Updates an existing download item in history."""
        for i, existing_item in enumerate(self.downloads_data):
            if existing_item.get('id') == download_item.id:
                self.downloads_data[i] = download_item.to_dict()
                self._save_data()
                return
        # If not found, add it
        self.add_download(download_item)

    def remove_download(self, download_id: str):
        """Removes a download item from history and saves."""
        self.downloads_data = [item for item in self.downloads_data if item.get('id') != download_id]
        self._save_data()

    def get_all_downloads(self) -> List[DownloadItem]:
        """Retrieves all download items from history."""
        # Convert dictionaries back to DownloadItem objects
        return [DownloadItem.from_dict(item_dict) for item_dict in self.downloads_data]

    def clear_history(self):
        """Clears all download history."""
        self.downloads_data = []
        self._save_data()
