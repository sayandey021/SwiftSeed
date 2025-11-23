import threading
import time
import os
import json
import subprocess
import requests
from enum import Enum
from pathlib import Path
from ..storage.download_history import DownloadHistoryManager

class DownloadStatus(Enum):
    DOWNLOADING = "Downloading"
    LOADING = "Loading Metadata"
    SEEDING = "Seeding"
    PAUSED = "Paused"
    STOPPED = "Stopped"
    COMPLETED = "Completed"
    ERROR = "Error"
    CHECKING = "Checking"
    QUEUED = "Queued"

class DownloadItem:
    def __init__(self, id, name, size_str, magnet, save_path, temp_path, gid=None):
        self.id = id
        self.name = name
        self.size_str = size_str
        self.magnet = magnet
        self.save_path = save_path
        self.temp_path = temp_path
        self.gid = gid # Aria2 GID
        self.status = DownloadStatus.QUEUED
        self.progress = 0.0
        self.speed = "0 KB/s"
        self.upload_speed = "0 KB/s"
        self.eta = "∞"
        self.peers = 0
        self.seeds = 0
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.files = [] # List of files in the torrent
        self.selected_files = [] # List of selected files for download
        self.file_priorities = {} # File priorities for download
        
        # Resume data
        self.resume_data = None
        
        # Determine file extension from name
        self.file_extension = self._get_extension(name)
    
    def to_dict(self):
        """Converts the DownloadItem object to a dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "size_str": self.size_str,
            "magnet": self.magnet,
            "save_path": self.save_path,
            "temp_path": self.temp_path,
            "gid": self.gid,
            "status": self.status.value,  # Store Enum as its value
            "progress": self.progress,
            "speed": self.speed,
            "upload_speed": self.upload_speed,
            "eta": self.eta,
            "peers": self.peers,
            "seeds": self.seeds,
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes,
            "files": self.files,
            "selected_files": self.selected_files,
            "file_priorities": self.file_priorities,
            "resume_data": self.resume_data,
            "file_extension": self.file_extension
        }

    @classmethod
    def from_dict(cls, data: Dict):
        """Creates a DownloadItem object from a dictionary."""
        item = cls(
            id=data.get('id'),
            name=data.get('name'),
            size_str=data.get('size_str'),
            magnet=data.get('magnet'),
            save_path=data.get('save_path'),
            temp_path=data.get('temp_path'),
            gid=data.get('gid')
        )
        item.status = DownloadStatus(data.get('status', DownloadStatus.QUEUED.value)) # Convert value back to Enum
        item.progress = data.get('progress', 0.0)
        item.speed = data.get('speed', "0 KB/s")
        item.upload_speed = data.get('upload_speed', "0 KB/s")
        item.eta = data.get('eta', "∞")
        item.peers = data.get('peers', 0)
        item.seeds = data.get('seeds', 0)
        item.downloaded_bytes = data.get('downloaded_bytes', 0)
        item.total_bytes = data.get('total_bytes', 0)
        item.files = data.get('files', [])
        item.selected_files = data.get('selected_files', [])
        item.file_priorities = data.get('file_priorities', {})
        item.resume_data = data.get('resume_data')
        item.file_extension = data.get('file_extension', "")
        return item
        
    def _get_extension(self, filename):
        """Extract or determine file extension from filename"""
        # Comprehensive list of file extensions
        video_exts = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.ts']
        audio_exts = ['.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a', '.wma', '.opus']
        archive_exts = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.tar.gz', '.tar.bz2']
        image_exts = ['.iso', '.img', '.dmg', '.nrg', '.mdf', '.bin']
        document_exts = ['.pdf', '.doc', '.docx', '.epub', '.mobi']
        app_exts = ['.apk', '.exe', '.msi', '.deb', '.rpm', '.appimage']
        
        all_exts = video_exts + audio_exts + archive_exts + image_exts + document_exts + app_exts
        
        # Check if filename already has a known extension
        if '.' in filename:
            parts = filename.lower().split('.')
            # Check for compound extensions like .tar.gz
            if len(parts) >= 3:
                compound_ext = '.' + '.'.join(parts[-2:])
                if compound_ext in all_exts:
                    return compound_ext
            # Check for single extension
            ext = '.' + parts[-1]
            if ext in all_exts:
                return ext
        
        # Determine by content keywords
        name_lower = filename.lower()
        
        # APK files
        if 'apk' in name_lower or 'android' in name_lower:
            return '.apk'
        
        # Video files
        if any(keyword in name_lower for keyword in ['movie', '1080p', '720p', '4k', 'bluray', 'web-dl', 'hdtv', 'webrip', 'brrip']):
            return '.mkv'
        
        # Audio files
        if any(keyword in name_lower for keyword in ['album', 'flac', 'mp3', 'music', 'discography']):
            return '.mp3'
        
        # OS Images
        if any(keyword in name_lower for keyword in ['ubuntu', 'linux', 'windows', 'iso', 'fedora', 'debian', 'arch']):
            return '.iso'
        
        # Software/Apps
        if any(keyword in name_lower for keyword in ['.exe', 'setup', 'installer', 'portable']):
            return '.exe'
        
        # Archives
        if any(keyword in name_lower for keyword in ['pack', 'collection', 'backup']):
            return '.zip'
            
        return ""

    def get_temp_file_path(self):
        """Get path to the temp file being downloaded"""
        # Temp file has .part extension while downloading
        filename = f"{self.name}{self.file_extension}.part"
        return os.path.join(self.temp_path, filename)

    def get_final_file_path(self):
        """Get the final destination path with proper extension"""
        filename = f"{self.name}{self.file_extension}"
        return os.path.join(self.save_path, filename)

class DownloadManager:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.base_path = self.settings_manager.get('download_folder', os.path.join(os.path.expanduser("~"), "Downloads", "TorrentSearch"))
        self.temp_path = self.settings_manager.get('temp_folder', os.path.join(self.base_path, "temp"))
        
        # Create directories if they don't exist
        os.makedirs(self.base_path, exist_ok=True)
        os.makedirs(self.temp_path, exist_ok=True)
        
        self._downloads = {} # Map GID to DownloadItem
        self.listeners = []
        
        self.running = True
        self.lock = threading.Lock()
        
        # Initialize download history manager
        self.download_history_manager = DownloadHistoryManager()
        
        # Aria2 settings
        self.aria2_host = "localhost"
        self.aria2_port = 6800
        self.aria2_secret = ""  # Optional secret for RPC
        
        # Start aria2 process
        self.aria2_process = None
        self._start_aria2()
        
        # Load previous downloads after aria2 has started
        self._load_previous_downloads()
        
        # Start update loop
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()

    def _load_previous_downloads(self):
        """Loads downloads from history and re-adds them to aria2 if active."""
        print("Loading previous downloads...")
        for item in self.download_history_manager.get_all_downloads():
            # Only re-add if not completed or stopped
            if item.status not in [DownloadStatus.COMPLETED, DownloadStatus.STOPPED, DownloadStatus.ERROR]:
                print(f"Re-adding download: {item.name} with magnet: {item.magnet}")
                if item.magnet: # Only re-add if magnet link exists
                    # Re-add to aria2
                    options = {
                        "dir": item.save_path
                    }
                    # If it was paused, add it as paused
                    if item.status == DownloadStatus.PAUSED:
                        options["pause"] = "true"

                    result = self._aria2_rpc_call("aria2.addUri", [[item.magnet], options])
                    if result and "result" in result:
                        new_gid = result["result"]
                        # Update the item with new GID
                        item.gid = new_gid
                        item.id = new_gid
                        # Set status back to QUEUED or PAUSED as per original status
                        if item.status == DownloadStatus.PAUSED:
                            item.status = DownloadStatus.PAUSED
                        else:
                            item.status = DownloadStatus.QUEUED # It will be updated by _update_loop
                        with self.lock:
                            self._downloads[new_gid] = item
                        print(f"Re-added {item.name} with new GID: {new_gid}")
                    else:
                        print(f"Failed to re-add {item.name} to aria2. Result: {result}")
                        # If failed to re-add, set status to ERROR in history
                        item.status = DownloadStatus.ERROR
                        self.download_history_manager.update_download(item)
                else:
                    print(f"Skipping re-add for {item.name} as no magnet link found in history.")
                    # If no magnet link, mark as error
                    item.status = DownloadStatus.ERROR
                    self.download_history_manager.update_download(item)
            else:
                # Add completed/stopped/errored items to internal list for display, but don't re-add to aria2
                with self.lock:
                    self._downloads[item.id] = item # Use original ID for these items
                print(f"Loaded {item.name} (status: {item.status.value}) from history.")
        self._notify_listeners()


    @property
    def downloads(self):
        with self.lock:
            return list(self._downloads.values())

    def add_listener(self, listener):
        self.listeners.append(listener)

    def remove_listener(self, listener):
        if listener in self.listeners:
            self.listeners.remove(listener)

    def _notify_listeners(self):
        for listener in self.listeners:
            try:
                listener()
            except:
                pass

    def _start_aria2(self):
        """Start aria2c process with RPC enabled"""
        try:
            # Path to aria2c executable
            aria2_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bin", "aria2c.exe")
            
            # Check if aria2c exists
            if not os.path.exists(aria2_path):
                print(f"aria2c not found at {aria2_path}")
                return False
            
            # Build command to start aria2c with RPC
            cmd = [
                aria2_path,
                "--enable-rpc=true",
                "--rpc-listen-all=false",
                f"--rpc-listen-port={self.aria2_port}",
                "--rpc-secret=",  # No secret for simplicity
                "--dir=" + self.base_path,
                "--continue=true",
                "--max-concurrent-downloads=5",
                "--max-connection-per-server=16",
                "--split=16",
                "--min-split-size=1M",
                "--check-integrity=true",
                "--quiet=true"
            ]
            
            # Start the process
            self.aria2_process = subprocess.Popen(cmd)
            print(f"Started aria2c process with PID {self.aria2_process.pid}. Command: {' '.join(cmd)}")
            
            # Wait a moment for aria2 to start
            time.sleep(1)
            
            # Check if aria2c is actually running
            if self.aria2_process.poll() is not None:
                print(f"Aria2c process (PID {self.aria2_process.pid}) has terminated unexpectedly with exit code {self.aria2_process.poll()}.")
                return False
            
            print("Aria2c appears to be running.")
            return True
        except Exception as e:
            print(f"Failed to start aria2c: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _aria2_rpc_call(self, method, params=None):
        """Make an RPC call to aria2"""
        try:
            url = f"http://{self.aria2_host}:{self.aria2_port}/jsonrpc"
            headers = {'Content-Type': 'application/json'}
            
            payload = {
                "jsonrpc": "2.0",
                "id": "qwer",
                "method": method,
                "params": params or []
            }
            print(f"Aria2 RPC: Calling method '{method}' with params: {params}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            response.raise_for_status() # Raise an exception for HTTP errors
            json_response = response.json()
            print(f"Aria2 RPC: Method '{method}' response: {json_response}")
            return json_response
        except requests.exceptions.ConnectionError:
            print(f"Aria2 RPC: Connection to aria2c failed. Is aria2c running on {self.aria2_host}:{self.aria2_port}?")
            return None
        except requests.exceptions.Timeout:
            print(f"Aria2 RPC: Request to aria2c timed out.")
            return None
        except Exception as e:
            print(f"RPC call failed for method '{method}': {e}")
            import traceback
            traceback.print_exc()
            return None

    def add_download(self, torrent, selected_files=None):
        """Add a new download from torrent object using aria2"""
        try:
            print(f"=== add_download called for: {torrent.name} ===")
            
            # Get magnet link safely
            magnet_link = torrent.get_magnet_uri() if hasattr(torrent, 'get_magnet_uri') else getattr(torrent, 'magnet', None)
            
            if not magnet_link:
                print("Error: No magnet link found for torrent")
                return False
            
            print(f"Attempting to add magnet link: {magnet_link}")
            
            # Prepare parameters for aria2
            params = [magnet_link]
            
            # Add options
            options = {
                "dir": self.base_path
            }
            
            # If specific files are selected, we'll handle that after the torrent is added
            if selected_files:
                # We'll set file priorities after the torrent is added
                pass
            
            # Add the download to aria2
            result = self._aria2_rpc_call("aria2.addUri", [params, options])
            
            if result and "result" in result:
                gid = result["result"]
                print(f"✓ Download added to aria2 with GID: {gid}")
                
                # Create DownloadItem
                item = DownloadItem(
                    id=gid,  # Use GID as ID
                    name=torrent.name,
                    size_str=torrent.size,
                    magnet=magnet_link,
                    save_path=self.base_path,
                    temp_path=self.temp_path,
                    gid=gid
                )
                
                # Store selected files if any
                if selected_files:
                    item.selected_files = selected_files
                    # Set file priorities after metadata is loaded
                
                with self.lock:
                    self._downloads[gid] = item
                
                # Add to download history
                self.download_history_manager.add_download(item)
                
                self._notify_listeners()
                return True
            else:
                print(f"Error adding download: {result}")
                return False
                
        except Exception as e:
            print(f"Error adding download: {e}")
            import traceback
            traceback.print_exc()
            return False

    def pause_download(self, download_id):
        """Pause a download"""
        try:
            result = self._aria2_rpc_call("aria2.pause", [download_id])
            if result and "result" in result:
                print(f"Paused download {download_id}")
                self._notify_listeners()
                return True
            else:
                print(f"Error pausing download: {result}")
                return False
        except Exception as e:
            print(f"Error pausing download: {e}")
            return False

    def resume_download(self, download_id):
        """Resume a download"""
        try:
            result = self._aria2_rpc_call("aria2.unpause", [download_id])
            if result and "result" in result:
                print(f"Resumed download {download_id}")
                self._notify_listeners()
                return True
            else:
                print(f"Error resuming download: {result}")
                return False
        except Exception as e:
            print(f"Error resuming download: {e}")
            return False

    def stop_download(self, download_id):
        """Stop a download"""
        try:
            result = self._aria2_rpc_call("aria2.remove", [download_id])
            if result and "result" in result:
                print(f"Stopped download {download_id}")
                with self.lock:
                    if download_id in self._downloads:
                        del self._downloads[download_id]
                self._notify_listeners()
                return True
            else:
                print(f"Error stopping download: {result}")
                return False
        except Exception as e:
            print(f"Error stopping download: {e}")
            return False

    def remove_download(self, download_id, delete_files=False):
        """Remove a download"""
        try:
            # First stop the download
            result = self._aria2_rpc_call("aria2.remove", [download_id])
            
            # Then delete files if requested
            if delete_files:
                # We'll need to handle file deletion manually since aria2 might not do it
                pass
            
            # Remove from our tracking
            with self.lock:
                if download_id in self._downloads:
                    del self._downloads[download_id]
            
            # Remove from download history as well
            self.download_history_manager.remove_download(download_id)
            
            self._notify_listeners()
            return True
        except Exception as e:
            print(f"Error removing download: {e}")
            return False

    def remove_completed_downloads(self):
        """Remove all completed downloads from the list"""
        try:
            with self.lock:
                completed_gids = []
                for gid, item in self._downloads.items():
                    if item.status == DownloadStatus.COMPLETED:
                        completed_gids.append(gid)
                
                for gid in completed_gids:
                    del self._downloads[gid]
                    self.download_history_manager.remove_download(gid) # Remove from history
            
            self._notify_listeners()
            return True
        except Exception as e:
            print(f"Error removing completed downloads: {e}")
            return False

    def set_download_limit(self, limit_bytes):
        """Set download speed limit"""
        try:
            # Convert bytes to KB
            limit_kb = limit_bytes // 1024 if limit_bytes > 0 else 0
            result = self._aria2_rpc_call("aria2.changeGlobalOption", [{"max-overall-download-limit": str(limit_kb)}])
            return True
        except Exception as e:
            print(f"Error setting download limit: {e}")
            return False

    def set_upload_limit(self, limit_bytes):
        """Set upload speed limit"""
        try:
            # Convert bytes to KB
            limit_kb = limit_bytes // 1024 if limit_bytes > 0 else 0
            result = self._aria2_rpc_call("aria2.changeGlobalOption", [{"max-overall-upload-limit": str(limit_kb)}])
            return True
        except Exception as e:
            print(f"Error setting upload limit: {e}")
            return False

    def set_file_priority(self, download_id, file_index, priority):
        """Set priority for a specific file in a download"""
        try:
            # Priority values: 0=skip, 1=low, 2=normal, 3=high
            result = self._aria2_rpc_call("aria2.changeOption", [download_id, {f"select-file[{file_index}]": str(priority)}])
            return True
        except Exception as e:
            print(f"Error setting file priority: {e}")
            return False

    def get_files(self, download_id):
        """Get files for a specific download"""
        try:
            result = self._aria2_rpc_call("aria2.getFiles", [download_id])
            if result and "result" in result:
                files = result["result"]
                item = self._downloads.get(download_id)
                if item:
                    item.files = []
                    for i, f in enumerate(files):
                        item.files.append({
                            'index': i,
                            'path': f.get('path', ''),
                            'length': int(f.get('length', 0)),
                            'completed': int(f.get('completedLength', 0)),
                            'selected': f.get('selected', 'true') == 'true'
                        })
                return item.files if item else []
            return []
        except Exception as e:
            print(f"Error getting files: {e}")
            return []

    def _update_loop(self):
        """Update download status"""
        while self.running:
            try:
                # Get all active downloads
                result = self._aria2_rpc_call("aria2.tellActive")
                
                # Also get waiting downloads
                waiting_result = self._aria2_rpc_call("aria2.tellWaiting", [0, 1000])
                
                # Also get stopped downloads
                stopped_result = self._aria2_rpc_call("aria2.tellStopped", [0, 1000])
                
                all_downloads = []
                if result and "result" in result:
                    all_downloads.extend(result["result"])
                if waiting_result and "result" in waiting_result:
                    all_downloads.extend(waiting_result["result"])
                if stopped_result and "result" in stopped_result:
                    all_downloads.extend(stopped_result["result"])
                
                with self.lock:
                    current_gids = set()
                    
                    for t in all_downloads:
                        gid = t.get('gid', '')
                        if not gid:
                            continue
                            
                        current_gids.add(gid)
                        
                        # Create or update item
                        if gid not in self._downloads:
                            item = DownloadItem(
                                id=gid,
                                name=t.get('bittorrent', {}).get('info', {}).get('name', f"Download {gid}"),
                                size_str=self._format_size(int(t.get('totalLength', 0))),
                                magnet='',  # We don't have magnet for existing downloads
                                save_path=t.get('dir', self.base_path),
                                temp_path=self.temp_path,
                                gid=gid
                            )
                            self._downloads[gid] = item
                        else:
                            item = self._downloads[gid]
                        
                        # Update fields
                        item.name = t.get('bittorrent', {}).get('info', {}).get('name', item.name)
                        item.total_bytes = int(t.get('totalLength', 0))
                        item.downloaded_bytes = int(t.get('completedLength', 0))
                        item.progress = item.total_bytes / item.total_bytes if item.total_bytes > 0 else 0
                        item.speed = self._format_speed(int(t.get('downloadSpeed', 0)))
                        item.upload_speed = self._format_speed(int(t.get('uploadSpeed', 0)))
                        item.eta = self._format_time(int(t.get('eta', 0))) if int(t.get('eta', 0)) < 8640000 else "∞"
                        
                        # Map status
                        status = t.get('status', 'unknown')
                        if status == 'active':
                            item.status = DownloadStatus.DOWNLOADING
                        elif status == 'waiting':
                            item.status = DownloadStatus.QUEUED
                        elif status == 'paused':
                            item.status = DownloadStatus.PAUSED
                        elif status == 'complete':
                            item.status = DownloadStatus.COMPLETED
                        elif status == 'error':
                            item.status = DownloadStatus.ERROR
                        elif status == 'removed':
                            item.status = DownloadStatus.STOPPED
                        else:
                            item.status = DownloadStatus.LOADING
                        
                        # Update size string
                        item.size_str = self._format_size(item.total_bytes)
                        item.save_path = t.get('dir', item.save_path)
                        
                        # Update download history for this item
                        self.download_history_manager.update_download(item)
                    
                    # Remove items that are no longer tracked in aria2 and our internal state from history
                    to_remove_from_downloads = []
                    to_remove_from_history = []
                    for gid, item in self._downloads.items():
                        if gid not in current_gids:
                            to_remove_from_downloads.append(gid)
                            # If it's not active/waiting/stopped in aria2, it should be removed from history as well
                            # This handles cases where aria2 cleans up its state for truly removed items
                            to_remove_from_history.append(gid)

                    for gid in to_remove_from_downloads:
                        del self._downloads[gid]
                    for gid in to_remove_from_history:
                        self.download_history_manager.remove_download(gid)
                
                self._notify_listeners()
                    
            except Exception as e:
                print(f"Update loop error: {e}")
            
            time.sleep(1)

    def _format_size(self, size):
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"

    def _format_speed(self, bytes_per_sec):
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"

    def _format_time(self, seconds):
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"

    def shutdown(self):
        """Shutdown the download manager"""
        self.running = False
        # Save current downloads to history before shutting down aria2
        print("Saving current downloads to history...")
        with self.lock:
            for item in self._downloads.values():
                self.download_history_manager.update_download(item)
        
        if self.aria2_process:
            try:
                self.aria2_process.terminate()
                self.aria2_process.wait(timeout=5)
            except:
                self.aria2_process.kill()
