import threading
import time
import os
import sys
import json
from enum import Enum
from pathlib import Path

def debug_log(msg):
    pass

# CRITICAL: Fix DLL load errors for frozen apps on Windows
if os.name == 'nt' and getattr(sys, 'frozen', False):
    import ctypes
    
    # Determine base directory
    base_dir = os.path.dirname(sys.executable)
    
    # Critical DLL paths
    dll_paths = [
        base_dir,  # Root folder
        os.path.join(base_dir, '_internal'),
        os.path.join(base_dir, '_internal', 'libtorrent'),
    ]
    
    # METHOD 1: Add to PATH environment variable (most compatible)
    existing_path = os.environ.get('PATH', '')
    new_paths = [p for p in dll_paths if os.path.exists(p) and p not in existing_path]
    if new_paths:
        os.environ['PATH'] = os.pathsep.join(new_paths) + os.pathsep + existing_path
    
    # METHOD 2: Use add_dll_directory (Windows 10+)
    for path in dll_paths:
        if os.path.exists(path):
            try:
                os.add_dll_directory(path)
            except (AttributeError, OSError):
                pass
    
    # METHOD 3: Preload critical DLLs to ensure they're found
    critical_dlls = [
        'zlib.dll',
        'libcrypto-1_1.dll', 
        'libssl-1_1.dll',
        'msvcp140.dll',
        'vcruntime140.dll',
        'vcruntime140_1.dll'
    ]
    
    for dll_name in critical_dlls:
        for search_path in dll_paths:
            dll_full_path = os.path.join(search_path, dll_name)
            if os.path.exists(dll_full_path):
                try:
                    ctypes.CDLL(dll_full_path)
                except Exception:
                    pass
                break

import libtorrent as lt

class DownloadStatus(Enum):
    DOWNLOADING = "Downloading"
    CHECKING = "Checking Files"
    ALLOCATING = "Allocating Space"
    DOWNLOADING_METADATA = "Loading Metadata"
    SEEDING = "Seeding"
    PAUSED = "Paused"
    STOPPED = "Stopped"
    COMPLETED = "Completed"
    ERROR = "Error"
    QUEUED = "Queued"
    DELETED = "Deleted"

class FileInfo:
    """Represents a file within a torrent"""
    def __init__(self, index, path, size, priority=4):
        self.index = index
        self.path = path
        self.size = size
        self.downloaded = 0
        self.progress = 0.0
        self.priority = priority  # 0=skip, 1=low, 4=normal, 7=high
        
    def to_dict(self):
        return {
            'index': self.index,
            'path': self.path,
            'size': self.size,
            'downloaded': self.downloaded,
            'progress': self.progress,
            'priority': self.priority
        }

class TorrentDownload:
    """Represents a single torrent download"""
    def __init__(self, handle, magnet, name, save_path):
        self.handle = handle
        self.magnet = magnet
        self.name = name
        self.save_path = save_path
        self.id = str(handle.info_hash())
        self.visible = True # Controls visibility in UI
        
        # Status fields
        self.status = DownloadStatus.DOWNLOADING_METADATA
        self.progress = 0.0
        self.download_rate = 0
        self.upload_rate = 0
        self.num_peers = 0
        self.num_seeds = 0
        self.total_size = 0
        self.downloaded_bytes = 0
        self.uploaded_bytes = 0
        self.eta = "∞"
        self.state_str = ""
        
        # Files
        self.files = []
        self.has_metadata = False
        
        # Track if manually stopped (don't update from libtorrent)
        self.is_stopped = False
        
    def update_status(self, status):
        """Update status from libtorrent status object"""
        # Don't update status logic if manually stopped or completed
        if self.is_stopped or self.status == DownloadStatus.COMPLETED:
            if self.progress >= 1.0:
                self.status = DownloadStatus.COMPLETED
            elif self.is_stopped:
                self.status = DownloadStatus.STOPPED
            return
            
        # Update stats only if active
        # Fix: Don't overwrite progress with 0 if paused/stopped and we have a value
        if status.progress > 0 or (not status.paused and not self.is_stopped):
            self.progress = status.progress
        self.download_rate = status.download_rate
        self.upload_rate = status.upload_rate
        self.num_peers = status.num_peers
        self.num_seeds = status.num_seeds
        self.total_size = status.total_wanted
        self.downloaded_bytes = status.total_wanted_done
        self.uploaded_bytes = status.total_upload
        
        # Calculate ETA
        if self.download_rate > 0 and self.progress < 1.0:
            remaining = self.total_size - self.downloaded_bytes
            eta_seconds = remaining / self.download_rate
            self.eta = self._format_time(eta_seconds)
        elif self.progress >= 1.0:
            self.eta = "Done"
        else:
            self.eta = "inf"
        
        # Update status based on libtorrent state
        if status.paused:
            # Check for Queued state (Paused + Auto Managed)
            if status.auto_managed:
                self.status = DownloadStatus.QUEUED
            # Only set to PAUSED if we haven't manually stopped it (handled above)
            elif not self.is_stopped and self.status != DownloadStatus.COMPLETED:
                self.status = DownloadStatus.PAUSED
        else:
            # Map libtorrent state to our status
            state = status.state
            if state == lt.torrent_status.checking_files:
                self.status = DownloadStatus.CHECKING
            elif state == lt.torrent_status.allocating:
                self.status = DownloadStatus.ALLOCATING
            elif state == lt.torrent_status.downloading_metadata:
                self.status = DownloadStatus.DOWNLOADING_METADATA
            elif state == lt.torrent_status.downloading:
                self.status = DownloadStatus.DOWNLOADING
            elif state == lt.torrent_status.finished:
                self.status = DownloadStatus.COMPLETED
            elif state == lt.torrent_status.seeding:
                self.status = DownloadStatus.SEEDING
            else:
                self.status = DownloadStatus.QUEUED
    
    def update_files(self):
        """Update file list and progress"""
        try:
            if not self.handle.is_valid():
                print("DEBUG update_files: Handle not valid")
                return
            
            status = self.handle.status()
            
            # If we already have files populated, just update progress
            if self.files and len(self.files) > 0:
                # Update file progress
                try:
                    file_progress = self.handle.file_progress()
                    for i, file_info in enumerate(self.files):
                        if i < len(file_progress):
                            file_info.downloaded = file_progress[i]
                            if file_info.size > 0:
                                file_info.progress = file_progress[i] / file_info.size
                            else:
                                file_info.progress = 1.0
                        file_info.priority = self.handle.file_priority(i)
                except Exception as e:
                    print(f"DEBUG: Error updating file progress: {e}")
                return
            
            # Check if we can get torrent info (either from handle status or directly)
            torrent_info = None
            
            # Method 1: Check handle status
            if status.has_metadata:
                torrent_info = self.handle.torrent_file()
            else:
                # Method 2: Try to get torrent_file() directly even if status says no metadata
                # This can happen immediately after adding a torrent from file
                try:
                    torrent_info = self.handle.torrent_file()
                    if torrent_info and torrent_info.is_valid():
                        print("DEBUG update_files: Got torrent_info directly (status.has_metadata was False)")
                    else:
                        torrent_info = None
                except:
                    torrent_info = None
            
            if not torrent_info or not torrent_info.is_valid():
                # Torrent metadata not available yet - this is normal for magnet links
                return
            
            # Get file info
            try:
                num_files = torrent_info.num_files()
                if num_files == 0:
                    print("DEBUG update_files: Torrent has 0 files")
                    return
                
                files_obj = torrent_info.files()
                if not files_obj:
                    print("DEBUG update_files: files_obj is None")
                    return
                
                self.has_metadata = True
                self.files = []
                print(f"DEBUG update_files: Torrent has {num_files} files")
                
                for i in range(num_files):
                    try:
                        file_entry = files_obj.at(i)
                        file_path = file_entry.path
                        file_info = FileInfo(
                            index=i,
                            path=file_path,
                            size=file_entry.size,
                            priority=self.handle.file_priority(i)
                        )
                        self.files.append(file_info)
                    except Exception as e:
                        print(f"DEBUG: Error reading file {i}: {e}")
                        if i == 0:
                            print("DEBUG: Failed to read first file, metadata not ready yet")
                            self.files = []
                            return
                        continue
                        
                print(f"DEBUG update_files: Successfully loaded {len(self.files)} files")
                        
            except Exception as e:
                print(f"DEBUG: Error getting torrent info: {e}")
                import traceback
                traceback.print_exc()
                return
            
            # Update file progress
            if self.has_metadata and self.files:
                try:
                    file_progress = self.handle.file_progress()
                    for i, file_info in enumerate(self.files):
                        if i < len(file_progress):
                            file_info.downloaded = file_progress[i]
                            if file_info.size > 0:
                                file_info.progress = file_progress[i] / file_info.size
                            else:
                                file_info.progress = 1.0
                        file_info.priority = self.handle.file_priority(i)
                except Exception as e:
                    print(f"DEBUG: Error updating file progress: {e}")
                    
        except Exception as e:
            print(f"Error updating files: {e}")
    
    def _format_time(self, seconds):
        """Format time in seconds to human readable"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
    
    def get_files_dict(self):
        """Get files as dictionaries"""
        return [f.to_dict() for f in self.files]

    def check_files_exist(self):
        """Check if downloaded files exist on disk"""
        if not self.files or not self.save_path:
            return True
            
        # Only check if we have downloaded something
        if self.progress <= 0:
            return True
            
        missing_count = 0
        checked_count = 0
        
        for f in self.files:
            # Check files that should exist (priority > 0 or partially downloaded)
            if f.priority > 0 or f.downloaded > 0:
                checked_count += 1
                full_path = os.path.join(self.save_path, f.path)
                if not os.path.exists(full_path):
                    missing_count += 1
        
        # If we checked files and ALL are missing, it's definitely deleted
        if checked_count > 0 and missing_count == checked_count:
            return False
            
        return True

class TorrentManager:
    """Standalone torrent manager using libtorrent"""
    
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.session = None
        self.torrents = {}  # info_hash -> TorrentDownload
        self.listeners = []
        self.running = True
        self.lock = threading.RLock()
        
        # Paths - use private variables
        # Use LOCALAPPDATA for all writable data (required for MSIX/Store apps)
        # MSIX apps install to read-only C:\Program Files\WindowsApps\
        app_data_dir = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser("~")), "SwiftSeed")
        
        self._download_path = self.settings_manager.get('download_folder', 
            os.path.join(os.path.expanduser("~"), "Downloads", "SwiftSeed Download"))
            
        # Temp and State paths in user's app data directory (not app root - it's read-only for MSIX)
        self._temp_path = self.settings_manager.get('temp_folder', 
            os.path.join(app_data_dir, "temp"))
        self.state_path = os.path.join(app_data_dir, ".torrent_state")
        
        # Create directories
        os.makedirs(self._download_path, exist_ok=True)
        os.makedirs(self.state_path, exist_ok=True)
        os.makedirs(self._temp_path, exist_ok=True)
        
        # Initialize session
        self._init_session()
        
        # Start update thread
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        debug_log("TorrentManager initialized")
    
    
    @property
    def download_path(self):
        """Get download path"""
        return self._download_path
    
    @download_path.setter
    def download_path(self, value):
        """Set download path"""
        self._download_path = value
        # Don't move state path, keep it in app root
        # self.state_path = os.path.join(value, ".torrent_state")
        os.makedirs(self._download_path, exist_ok=True)
        # os.makedirs(self.state_path, exist_ok=True)
    
    @property
    def base_path(self):
        """Alias for download_path (compatibility)"""
        return self._download_path
    
    @base_path.setter
    def base_path(self, value):
        """Set base_path (updates download_path)"""
        self.download_path = value
    
    @property
    def temp_path(self):
        """Get temp path"""
        return self._temp_path
    
    @temp_path.setter
    def temp_path(self, value):
        """Set temp path"""
        self._temp_path = value
        os.makedirs(self._temp_path, exist_ok=True)
    
    def _init_session(self):
        """Initialize libtorrent session"""
        debug_log("Initializing libtorrent session...")
        self.session = lt.session()
        
        # HIGHLY OPTIMIZED settings for MAXIMUM download speed
        settings = {
            'user_agent': 'libtorrent/2.0.11.0',
            'listen_interfaces': '0.0.0.0:6881,[::]:6881',
            
            # DHT optimizations (critical for peer discovery)
            'enable_dht': True,
            'dht_bootstrap_nodes': 'router.bittorrent.com:6881,router.utorrent.com:6881,dht.transmissionbt.com:6881',
            'dht_upload_rate_limit': 50000,
            'dht_announce_interval': 15 * 60,
            
            # Peer exchange and discovery
            'enable_lsd': True,
            'enable_upnp': True,
            'enable_natpmp': True,
            'enable_incoming_utp': True,
            'enable_outgoing_utp': True,
            
            # ==== MAXIMUM SPEED CONNECTION SETTINGS ====
            'connections_limit': 1000,  # DOUBLED - More simultaneous connections
            'connection_speed': 500,    # MUCH FASTER - 500 new connections per second
            'peer_connect_timeout': 5,  # Faster timeout for bad peers
            'max_failcount': 1,         # Drop bad peers immediately
            'max_out_request_queue': 2500,  # LARGER - More outstanding requests
            'max_allowed_in_request_queue': 3000,
            'connections_slack': 50,    # Keep extra connections ready
            
            # ==== DOWNLOAD OPTIMIZATION ====
            'request_timeout': 15,      # Faster piece request timeout
            'piece_timeout': 8,         # Even faster piece timeout
            'min_reconnect_time': 1,
            'peer_timeout': 15,         # Drop slow peers faster
            'inactivity_timeout': 30,   # Drop inactive peers
            
            # ==== CHOKING ALGORITHM (Better peer selection) ====
            'choking_algorithm': 1,     # 1 = rate_based (fastest peers get unchoked)
            'seed_choking_algorithm': 1, # Same for seeding
            'peer_turnover_interval': 300,  # Check for better peers every 5 min
            
            # ==== DISK I/O OPTIMIZATION ====
            'max_queued_disk_bytes': 10 * 1024 * 1024,  # 10MB disk cache queue
            'cache_size': 2048,         # 2048 * 16KB = 32MB cache
            'cache_expiry': 300,        # Keep cache for 5 minutes
            'disk_io_write_mode': 0,    # enable_os_cache (use OS page cache)
            'disk_io_read_mode': 0,
            'checking_mem_usage': 1024, # 1024 * 16KB = 16MB for checking
            
            # ==== PIECE/BLOCK SETTINGS FOR SPEED ====
            'request_queue_time': 3,    # How many seconds worth of data to request
            'whole_pieces_threshold': 20, # Download whole pieces when >20 peers
            'suggest_mode': 0,          # No piece suggestions (faster)
            'send_redundant_have': True, # Send have messages faster
            'lazy_bitfields': False,    # Send full bitfield (faster handshake)
            
            # ==== METADATA & FAST RESUME ====
            'metadata_token_limit': 5000,
            'close_redundant_connections': True,
            'prioritize_partial_pieces': True,
            'rate_limit_ip_overhead': False,  # Don't limit protocol overhead
            
            # Tracker settings
            'announce_to_all_trackers': True,
            'announce_to_all_tiers': True,
            'tracker_completion_timeout': 15,
            'tracker_receive_timeout': 8,
            'stop_tracker_timeout': 5,
            'tracker_backoff': 150,     # Faster tracker retry
            
            # Bandwidth (0 = unlimited)
            'download_rate_limit': self.settings_manager.get('download_limit', 0),
            'upload_rate_limit': self.settings_manager.get('upload_limit', 0),
            
            # Queue settings
            'active_downloads': self.settings_manager.get('max_active_downloads', 5),
            'active_seeds': self.settings_manager.get('max_active_seeds', 5),
            'active_checking': 3,
            'active_dht_limit': 800,    # More DHT operations
            'active_tracker_limit': 2400,
            'active_lsd_limit': 100,
            
            # ==== MIXED MODE (Better performance on modern networks) ====
            'mixed_mode_algorithm': 0,  # 0 = prefer TCP (faster on most connections)
            
            # Alerts
            'alert_mask': lt.alert.category_t.all_categories,
        }
        
        self.session.apply_settings(settings)
        
        # Load DHT state if it exists (makes DHT much faster)
        dht_state_path = os.path.join(self.state_path, "dht_state")
        if os.path.exists(dht_state_path):
            try:
                with open(dht_state_path, 'rb') as f:
                    dht_state = f.read()
                    if dht_state:
                        self.session.load_state(lt.bdecode(dht_state))
                        print("[OK] Loaded DHT state (faster peer discovery)")
            except Exception as e:
                print(f"Warning: Could not load DHT state: {e}")
        
        # Comprehensive DHT router list - critical for fast bootstrap
        routers = [
            # BitTorrent Inc. routers
            ("router.bittorrent.com", 6881),
            ("router.utorrent.com", 6881),
            
            # Transmission
            ("dht.transmissionbt.com", 6881),
            
            # Vuze/Azureus
            ("dht.aelitis.com", 6881),
            
            # BitComet
            ("router.bitcomet.com", 6881),
            
            # libtorrent
            ("dht.libtorrent.org", 25401),
            
            # Additional reliable nodes
            ("dht.anacrolix.link", 42069),
            
            # Public DHT nodes (very reliable)
            ("167.179.87.87", 6881),  # Stable public node
            ("87.98.162.88", 6881),   # Stable public node
        ]
        
        print(f"Adding {len(routers)} DHT bootstrap nodes...")
        for router, port in routers:
            self.session.add_dht_router(router, port)
        
        print("[OK] Torrent session initialized")
        debug_log("Torrent session initialized")
        
        # Load saved state
        debug_log("Loading saved state")
        self._load_state()
        debug_log("Saved state loaded")
    
    def _load_state(self):
        """Load session state from downloads.json"""
        try:
            json_path = os.path.join(self.state_path, "downloads.json")
            if not os.path.exists(json_path):
                print("No saved state found")
                return

            with open(json_path, 'r') as f:
                saved_downloads = json.load(f)
            
            print(f"Loading {len(saved_downloads)} saved downloads...")
            
            for download_id, data in saved_downloads.items():
                try:
                    # Skip hidden/temporary downloads (e.g. cancelled metadata fetches)
                    if not data.get('visible', True):
                        print(f"Skipping hidden download: {download_id}")
                        continue

                    magnet = data.get('magnet')
                    save_path = data.get('save_path', self.download_path)
                    is_stopped = data.get('is_stopped', False)
                    
                    params = None
                    
                    # Try to load resume data first
                    resume_path = os.path.join(self.state_path, f"{download_id}.fastresume")
                    torrent_path = os.path.join(self.state_path, f"{download_id}.torrent")
                    
                    if os.path.exists(resume_path):
                        try:
                            with open(resume_path, 'rb') as f:
                                resume_data = f.read()
                                if resume_data:
                                    params = lt.read_resume_data(resume_data)
                                    print(f"Loaded resume data for {download_id}")
                        except Exception as e:
                            print(f"Warning: Could not load resume data for {download_id}: {e}")
                    
                    # If no params from resume data (or failed), create fresh
                    if params is None:
                        if os.path.exists(torrent_path):
                            params = lt.add_torrent_params()
                            params.ti = lt.torrent_info(torrent_path)
                        elif magnet:
                            params = lt.parse_magnet_uri(magnet)
                    
                    if params:
                        params.save_path = save_path
                        # Use sparse storage mode to prevent creating empty files for skipped files
                        params.storage_mode = lt.storage_mode_t.storage_mode_sparse
                        
                        # If we loaded from resume data, we might still need to attach torrent_info if available
                        if os.path.exists(torrent_path):
                             try:
                                 if not params.ti: 
                                     params.ti = lt.torrent_info(torrent_path)
                             except Exception as e:
                                 print(f"Error loading torrent info: {e}")
                        
                        # Add to session
                        try:
                            handle = self.session.add_torrent(params)
                            
                            # Restore file priorities if available
                            try:
                                if params.resume_data:
                                    try:
                                        rd = lt.bdecode(params.resume_data)
                                        if b'file_priority' in rd:
                                            priorities = rd[b'file_priority']
                                            if isinstance(priorities, list):
                                                handle.prioritize_files(priorities)
                                                print(f"Restored file priorities for {download_id}")
                                    except:
                                        pass
                                handle.save_resume_data()
                            except Exception as e:
                                print(f"Error restoring priorities: {e}")

                        except Exception as e:
                            print(f"Error adding torrent to session {download_id}: {e}")
                            # Retry without resume data if it failed
                            if hasattr(params, 'resume_data') and params.resume_data:
                                print(f"Retrying {download_id} without resume data...")
                                params.resume_data = b''
                                try:
                                    handle = self.session.add_torrent(params)
                                except Exception as e2:
                                    print(f"Failed retry: {e2}")
                                    continue
                            else:
                                continue
                        
                        if not handle.is_valid():
                            print(f"Invalid handle for {download_id}")
                            continue

                        # Create object
                        download = TorrentDownload(
                            handle=handle,
                            magnet=magnet,
                            name=data.get('name', 'Unknown'),
                            save_path=save_path
                        )
                        download.is_stopped = is_stopped
                        
                        # Restore progress and other data from saved state
                        download.progress = data.get('progress', 0.0)
                        download.total_size = data.get('total_size', 0)
                        download.downloaded_bytes = data.get('downloaded_bytes', 0)
                        download.visible = data.get('visible', True) 
                        
                        # Restore file priorities from saved state (backup for resume data)
                        saved_priorities = data.get('file_priorities', [])
                        if saved_priorities and handle.is_valid():
                            try:
                                # Only apply if length matches and we have metadata
                                # We need to check if we have metadata to know num_files
                                if handle.status().has_metadata:
                                    if len(saved_priorities) == handle.torrent_file().num_files():
                                        handle.prioritize_files(saved_priorities)
                                        print(f"Restored file priorities from json for {download_id}")
                                else:
                                    # Store for later application when metadata loads
                                    download.saved_priorities = saved_priorities
                                    print(f"Stored file priorities for later restoration: {download_id}")
                            except Exception as e:
                                print(f"Error restoring priorities from json: {e}") 
                        
                        # Apply stopped/paused state
                        if is_stopped:
                            handle.unset_flags(lt.torrent_flags.auto_managed)
                            handle.pause()
                            if data.get('status') == 'Completed':
                                download.status = DownloadStatus.COMPLETED
                            else:
                                download.status = DownloadStatus.STOPPED
                                
                        elif data.get('status') == 'Paused':
                            handle.unset_flags(lt.torrent_flags.auto_managed)
                            handle.pause()
                            download.status = DownloadStatus.PAUSED
                        
                        # Force recheck for active, incomplete downloads to ensure data integrity
                        elif download.progress < 1.0 and data.get('status') != 'Completed':
                            print(f"Forcing recheck for {download.name} to ensure integrity")
                            handle.force_recheck()
                            download.status = DownloadStatus.CHECKING
                        
                        with self.lock:
                            self.torrents[download.id] = download
                            print(f"Successfully loaded {download.name} ({download.id})")
                            
                except Exception as e:
                    print(f"Error loading download {download_id}: {e}")
            
            self._notify_listeners()
            
        except Exception as e:
            print(f"Error loading state: {e}")

    def _save_state(self):
        """Save current state to downloads.json"""
        try:
            downloads_data = {}
            with self.lock:
                for download_id, torrent in self.torrents.items():
                    downloads_data[download_id] = {
                        'magnet': torrent.magnet,
                        'name': torrent.name,
                        'save_path': torrent.save_path,
                        'is_stopped': torrent.is_stopped,
                        'status': torrent.status.value,
                        'progress': torrent.progress,
                        'total_size': torrent.total_size,
                        'downloaded_bytes': torrent.downloaded_bytes,
                        'downloaded_bytes': torrent.downloaded_bytes,
                        'visible': getattr(torrent, 'visible', True),
                        'file_priorities': [f.priority for f in torrent.files] if torrent.files else (
                            torrent.handle.file_priorities() if torrent.handle.is_valid() and torrent.handle.status().has_metadata else []
                        )
                    }
            
            json_path = os.path.join(self.state_path, "downloads.json")
            with open(json_path, 'w') as f:
                json.dump(downloads_data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving state: {e}")
    
    @property
    def downloads(self):
        """Get list of all downloads"""
        # debug_log("Acquiring lock for downloads property")
        with self.lock:
            # debug_log("Lock acquired for downloads property")
            return list(self.torrents.values())
    
    def add_listener(self, listener):
        """Add update listener"""
        self.listeners.append(listener)
    
    def remove_listener(self, listener):
        """Remove update listener"""
        if listener in self.listeners:
            self.listeners.remove(listener)
    
    def _notify_listeners(self):
        """Notify all listeners of updates"""
        for listener in self.listeners:
            try:
                listener()
            except Exception as e:
                print(f"Listener error: {e}")
    
    def add_download(self, torrent, selected_files=None, visible=True, download_path=None):
        """
        Add a new torrent download
        
        Args:
            torrent: Torrent object with magnet link or file path
            selected_files: List of file indices to download (None = all)
            visible: Whether the download should be visible in the UI (default: True)
            download_path: Optional custom download path for this specific download
        """
        try:
            print(f"DEBUG: Adding download for {torrent.name}")
            
            # Use custom download path if provided, otherwise use default
            save_path = download_path if download_path else self.download_path
            
            params = lt.add_torrent_params()
            params.save_path = save_path
            # Use sparse storage mode to prevent creating empty files for skipped files
            params.storage_mode = lt.storage_mode_t.storage_mode_sparse
            
            magnet = None
            
            # Check if it's a file path torrent
            if hasattr(torrent, 'file_path') and torrent.file_path:
                print(f"DEBUG: Using torrent file: {torrent.file_path}")
                info = lt.torrent_info(torrent.file_path)
                params.ti = info
                
                # Apply file priorities immediately to prevent unwanted file creation
                if selected_files:
                    num_files = info.num_files()
                    # Default all to 0 (skip)
                    priorities = [0] * num_files
                    # Set selected to 4 (default/normal)
                    for idx in selected_files:
                        if idx < num_files:
                            priorities[idx] = 4
                    
                    params.file_priorities = priorities
                    print(f"DEBUG: Applied initial file priorities via params")
            else:
                # Get magnet link
                magnet = torrent.get_magnet_uri() if hasattr(torrent, 'get_magnet_uri') else getattr(torrent, 'magnet', None)
                
                if not magnet:
                    print("Error: No magnet link or file path provided")
                    return None
                
                # Check if it's an HTTP URL (Internet Archive, ByRutor, etc.)
                if magnet.startswith('http://') or magnet.startswith('https://'):
                    # Libtorrent 2.x removed support for params.url
                    # We need to download the .torrent file ourselves
                    print(f"DEBUG: Downloading torrent file from URL: {magnet}")
                    try:
                        import requests
                        import urllib3
                        urllib3.disable_warnings()
                        
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            'Accept': 'application/x-bittorrent, */*',
                        }
                        resp = requests.get(magnet, headers=headers, timeout=30, verify=False, allow_redirects=True)
                        
                        print(f"DEBUG: Response status: {resp.status_code}, Content-Type: {resp.headers.get('Content-Type', 'Unknown')}")
                        print(f"DEBUG: Content length: {len(resp.content)} bytes")
                        
                        if resp.status_code != 200:
                            print(f"Error: Failed to download torrent file. Status: {resp.status_code}")
                            return None
                        
                        # Validate torrent file content
                        content = resp.content
                        if len(content) < 50:
                            print(f"Error: Downloaded file too small ({len(content)} bytes)")
                            return None
                        
                        # Check if it looks like a torrent file (starts with 'd' for bencoded dict)
                        if not content.startswith(b'd'):
                            print(f"Warning: Content doesn't look like a torrent file. First bytes: {content[:20]}")
                            # Try anyway - might still work
                        
                        # Save to temp file
                        temp_torrent_path = os.path.join(self._temp_path, f"temp_{abs(hash(magnet))}.torrent")
                        with open(temp_torrent_path, 'wb') as f:
                            f.write(content)
                        
                        print(f"DEBUG: Saved torrent file to {temp_torrent_path}")
                        
                        # Load torrent info from file
                        try:
                            info = lt.torrent_info(temp_torrent_path)
                            print(f"DEBUG: Loaded torrent info: {info.name()}, {info.num_files()} files")
                        except Exception as e:
                            print(f"Error: Invalid torrent file - {e}")
                            return None
                            
                        params = lt.add_torrent_params()
                        params.ti = info
                        params.storage_mode = lt.storage_mode_t.storage_mode_sparse
                        
                        # Store for later reference (to save to state folder)
                        torrent.file_path = temp_torrent_path
                        
                    except Exception as e:
                        print(f"Error downloading torrent from URL: {e}")
                        import traceback
                        traceback.print_exc()
                        return None
                else:
                    # Parse magnet link (this preserves all trackers in the original magnet)
                    try:
                        params = lt.parse_magnet_uri(magnet)
                    except Exception as e:
                        print(f"Error: Invalid magnet link - {e}")
                        return None
                    
                params.save_path = save_path
                # Use sparse storage mode for all download types
                params.storage_mode = lt.storage_mode_t.storage_mode_sparse
                
                # Optimize flags for FAST metadata download
                # Remove default flags that slow us down
                params.flags &= ~lt.torrent_flags.upload_mode  # We DO want to participate (helps get metadata)
                params.flags &= ~lt.torrent_flags.paused  # Start immediately
                
                # Add beneficial flags
                params.flags |= lt.torrent_flags.apply_ip_filter  # Security
                params.flags |= lt.torrent_flags.auto_managed  # Let session manage it
                
                # Metadata priority settings
                params.max_connections = 100  # More connections = faster metadata
                params.max_uploads = 10  # Need some upload for peer exchange
                
                # Get existing trackers count
                existing_trackers_count = len(params.trackers)
                print(f"DEBUG: Magnet has {existing_trackers_count} original trackers")
                
                # Add TOP-TIER public trackers for fastest metadata
                # These are appended AFTER original trackers
                additional_trackers = [
                    # Tier 1: Fastest and most reliable
                    "udp://tracker.opentrackr.org:1337/announce",
                    "udp://open.stealth.si:80/announce",
                    "udp://tracker.torrent.eu.org:451/announce",
                    "udp://exodus.desync.com:6969/announce",
                    "udp://tracker.openbittorrent.com:80/announce",
                    
                    # Tier 2: Very reliable backups
                    "udp://tracker.cyberia.is:6969/announce",
                    "udp://opentracker.i2p.rocks:6969/announce",
                    "udp://tracker.tiny-vps.com:6969/announce",
                    "udp://tracker.moeking.me:6969/announce",
                    "udp://ipv4.tracker.harry.lu:80/announce",
                    
                    # Tier 3: Additional coverage
                    "udp://9.rarbg.to:2710/announce",
                    "udp://tracker.internetwarriors.net:1337/announce",
                    "udp://tracker.zer0day.to:1337/announce",
                    "udp://tracker.leechers-paradise.org:6969/announce",
                    
                    # HTTP fallbacks (for restrictive networks)
                    "http://tracker.openbittorrent.com:80/announce",
                    "http://tracker.opentrackr.org:1337/announce",
                ]
                
                # Only add trackers that aren't already in the magnet
                for tracker in additional_trackers:
                    if tracker not in params.trackers:
                        params.trackers.append(tracker)
                
                print(f"DEBUG: Total trackers after adding public ones: {len(params.trackers)}")
            
            # Add torrent to session
            print("DEBUG: Adding to libtorrent session...")
            handle = self.session.add_torrent(params)
            print(f"DEBUG: Handle valid? {handle.is_valid()}")
            
            # Check if already exists in our tracking
            download_id = str(handle.info_hash())
            with self.lock:
                if download_id in self.torrents:
                    print(f"DEBUG: Torrent {download_id} already exists. Returning existing object.")
                    existing = self.torrents[download_id]
                    # Don't modify the existing download - let caller handle duplicates
                    return existing
            
            # Create download object
            download = TorrentDownload(
                handle=handle,
                magnet=magnet,
                name=torrent.name,
                save_path=save_path
            )
            download.is_newly_added = True
            download.visible = visible  # Set visibility before saving state
            
            # Store selected files for later (after metadata is received for magnets)
            if selected_files:
                print(f"DEBUG: Selected {len(selected_files)} files")
                # Store as dict with index -> priority mapping for later application
                if len(selected_files) > 0 and isinstance(selected_files[0], dict):
                    print("DEBUG: Converting selected file dicts to priority map")
                    # Store as dict: {index: priority} where priority is UI value (0-3)
                    download.selected_files_with_priority = {
                        f.get('index', 0): f.get('priority', 2) for f in selected_files
                    }
                    download.selected_files = list(download.selected_files_with_priority.keys())
                else:
                    download.selected_files = selected_files
                    # Default all to Normal priority
                    download.selected_files_with_priority = {idx: 2 for idx in selected_files}
            
            # If added from file, we have metadata immediately
            if hasattr(torrent, 'file_path') and torrent.file_path:
                download.has_metadata = True
                download.update_files()
                
                # Apply file selection immediately if specified
                if selected_files and download.files:
                    # Priority mapping: UI (0=skip, 1=low, 2=normal, 3=high) -> libtorrent (0, 1, 4, 7)
                    lt_priority_map = {0: 0, 1: 1, 2: 4, 3: 7}
                    
                    # Build a map of file index -> priority from selected_files
                    file_priority_map = {}
                    if len(selected_files) > 0 and isinstance(selected_files[0], dict):
                        for f in selected_files:
                            idx = f.get('index', 0)
                            priority = f.get('priority', 2)  # Default to Normal
                            file_priority_map[idx] = lt_priority_map.get(priority, 4)
                        indices = list(file_priority_map.keys())
                    else:
                        indices = selected_files
                        # If just indices, use Normal priority for all
                        for idx in indices:
                            file_priority_map[idx] = 4
                        
                    print(f"DEBUG: Applying file selection immediately for torrent file: {len(indices)} selected out of {len(download.files)} total files")
                    # First, set ALL files to skip (priority 0)
                    for i in range(len(download.files)):
                        handle.file_priority(i, 0)
                    # Then, set selected files to their specified priority
                    for idx, lt_priority in file_priority_map.items():
                        if idx < len(download.files):
                            handle.file_priority(idx, lt_priority)
                            priority_name = {0: 'Skip', 1: 'Low', 4: 'Normal', 7: 'High'}.get(lt_priority, 'Normal')
                            print(f"DEBUG: Set file {idx} to priority {lt_priority} ({priority_name})")
                    # Don't store selected_files since we applied them immediately
                    if hasattr(download, 'selected_files'):
                        delattr(download, 'selected_files')
                    if hasattr(download, 'selected_files_with_priority'):
                        delattr(download, 'selected_files_with_priority')
                
                # Save .torrent file to state folder for resume/persistence
                # NOTE: .torrent is NOT saved to download folder automatically
                # User must explicitly choose "Save .torrent" option in the UI
                try:
                    import shutil
                    dest_path = os.path.join(self.state_path, f"{download.id}.torrent")
                    shutil.copy2(torrent.file_path, dest_path)
                    print(f"DEBUG: Saved torrent file to state folder: {dest_path}")
                except Exception as e:
                    print(f"Warning: Could not save torrent file: {e}")
            
            # Add to our tracking
            with self.lock:
                self.torrents[download.id] = download
            
            # Notify listeners IMMEDIATELY for instant UI update
            self._notify_listeners()
            print(f"[OK] Added torrent: {torrent.name}")
            
            # Save state in background to avoid blocking UI
            # The update loop will also save state periodically
            threading.Thread(target=self._save_state, daemon=True).start()
            
            return download
            
        except Exception as e:
            print(f"Error adding download: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def pause_download(self, download_id):
        """Pause a download"""
        try:
            with self.lock:
                if download_id in self.torrents:
                    torrent = self.torrents[download_id]
                    # Disable auto-managed to prevent auto-resume
                    torrent.handle.unset_flags(lt.torrent_flags.auto_managed)
                    torrent.handle.pause()
                    torrent.status = DownloadStatus.PAUSED
                    print(f"Paused torrent: {download_id}")
                    self._save_state()
                    self._notify_listeners()
                    return True
            return False
        except Exception as e:
            print(f"Error pausing download: {e}")
            return False
    
    def resume_download(self, download_id):
        """Resume a download"""
        try:
            with self.lock:
                if download_id in self.torrents:
                    torrent = self.torrents[download_id]
                    
                    # Re-enable auto-managed so it respects queue limits
                    torrent.handle.set_flags(lt.torrent_flags.auto_managed)
                    
                    # If it was stopped, we might want to force recheck
                    if torrent.is_stopped:
                        print(f"Resuming stopped torrent (rechecking): {download_id}")
                        torrent.handle.force_recheck()
                        torrent.status = DownloadStatus.CHECKING
                    else:
                        torrent.status = DownloadStatus.DOWNLOADING
                    
                    torrent.is_stopped = False  # Clear stopped flag
                    torrent.handle.resume()
                    
                    self._save_state()
                    self._notify_listeners()
                    return True
            return False
        except Exception as e:
            print(f"Error resuming download: {e}")
            return False
    
    def stop_download(self, download_id):
        """Stop a download"""
        try:
            with self.lock:
                if download_id in self.torrents:
                    torrent = self.torrents[download_id]
                    
                    # Don't stop if already completed (unless it was seeding)
                    if torrent.status == DownloadStatus.COMPLETED:
                        print(f"Torrent already completed: {download_id}")
                        return False
                    
                    # Disable auto-managed
                    torrent.handle.unset_flags(lt.torrent_flags.auto_managed)
                    torrent.handle.pause()
                    torrent.is_stopped = True  # Mark as stopped
                    
                    # If it was seeding or fully downloaded, mark as completed
                    if torrent.progress >= 1.0 or torrent.status == DownloadStatus.SEEDING:
                        torrent.status = DownloadStatus.COMPLETED
                    else:
                        torrent.status = DownloadStatus.STOPPED
                        
                    print(f"Stopped torrent: {download_id}")
                    self._save_state()
                    self._notify_listeners()
                    return True
            return False
        except Exception as e:
            print(f"Error stopping download: {e}")
            return False
    
    def remove_download(self, download_id, delete_files=False):
        """Remove a download"""
        try:
            with self.lock:
                if download_id in self.torrents:
                    torrent = self.torrents[download_id]
                    
                    # Remove from session
                    if delete_files:
                        self.session.remove_torrent(torrent.handle, lt.session.delete_files)
                    else:
                        self.session.remove_torrent(torrent.handle)
                    
                    # Remove from our tracking
                    del self.torrents[download_id]
                    
                    # Clean up state files
                    try:
                        torrent_path = os.path.join(self.state_path, f"{download_id}.torrent")
                        resume_path = os.path.join(self.state_path, f"{download_id}.fastresume")
                        if os.path.exists(torrent_path): os.remove(torrent_path)
                        if os.path.exists(resume_path): os.remove(resume_path)
                    except Exception as e:
                        print(f"Error cleaning up state files: {e}")
                        
                    self._save_state()
                    self._notify_listeners()
                    return True
            return False
        except Exception as e:
            print(f"Error removing download: {e}")
            return False

    def _save_resume_data(self):
        """Save resume data for all torrents"""
        try:
            with self.lock:
                for download_id, torrent in self.torrents.items():
                    if not torrent.handle.is_valid():
                        continue
                        
                    # Save .torrent file to state folder for resume/persistence
                    # NOTE: .torrent is NOT saved to download folder automatically
                    # User must explicitly choose "Save .torrent" option in the UI
                    if torrent.has_metadata:
                        torrent_path = os.path.join(self.state_path, f"{download_id}.torrent")
                        
                        torrent_info = torrent.handle.torrent_file()
                        if torrent_info:
                            torrent_data = lt.bencode(lt.create_torrent(torrent_info).generate())
                            
                            if not os.path.exists(torrent_path):
                                with open(torrent_path, 'wb') as f:
                                    f.write(torrent_data)
                    
                    # Save fastresume data
                    if torrent.status not in [DownloadStatus.CHECKING, DownloadStatus.ALLOCATING, DownloadStatus.DOWNLOADING_METADATA]:
                        torrent.handle.save_resume_data()
                        
            # Process alerts to get resume data
            alerts = self.session.pop_alerts()
            for alert in alerts:
                if isinstance(alert, lt.save_resume_data_alert):
                    try:
                        if hasattr(lt, 'write_resume_data'):
                            # Libtorrent 2.0.x
                            resume_data = lt.bencode(lt.write_resume_data(alert.params))
                        else:
                            # Libtorrent 1.2.x
                            if hasattr(alert, 'resume_data'):
                                resume_data = lt.bencode(alert.resume_data)
                            else:
                                continue
                                
                        resume_path = os.path.join(self.state_path, f"{str(alert.handle.info_hash())}.fastresume")
                        with open(resume_path, 'wb') as f:
                            f.write(resume_data)
                        print(f"Saved resume data for {alert.handle.info_hash()}")
                    except Exception as e:
                        print(f"Error saving resume data: {e}")
                        
        except Exception as e:
            pass
            
    def remove_completed_downloads(self):
        """Remove all completed downloads"""
        try:
            with self.lock:
                to_remove = []
                for download_id, torrent in self.torrents.items():
                    if torrent.status == DownloadStatus.COMPLETED:
                        to_remove.append(download_id)
                
                for download_id in to_remove:
                    torrent = self.torrents[download_id]
                    self.session.remove_torrent(torrent.handle)
                    del self.torrents[download_id]
                
                self._save_state()
                self._notify_listeners()
                return True
        except Exception as e:
            print(f"Error removing completed: {e}")
            return False

    def set_file_priority(self, download_id, file_index, priority):
        """
        Set priority for a specific file
        
        Args:
            download_id: Torrent ID
            file_index: Index of file
            priority: 0=skip, 1=low, 2=normal, 3=high
        """
        try:
            with self.lock:
                if download_id in self.torrents:
                    torrent = self.torrents[download_id]
                    
                    # Map UI priority to libtorrent priority
                    # UI: 0=skip, 1=low, 2=normal, 3=high
                    # libtorrent: 0=skip, 1=low, 4=normal, 7=high
                    lt_priority_map = {0: 0, 1: 1, 2: 4, 3: 7}
                    lt_priority = lt_priority_map.get(priority, 4)
                    
                    torrent.handle.file_priority(file_index, lt_priority)
                    
                    # Update in our file info
                    if file_index < len(torrent.files):
                        torrent.files[file_index].priority = lt_priority
                    
                    self._notify_listeners()
                    return True
            return False
        except Exception as e:
            print(f"Error setting file priority: {e}")
            return False
    
    def get_files(self, download_id):
        """Get file list for a torrent"""
        try:
            with self.lock:
                if download_id in self.torrents:
                    torrent = self.torrents[download_id]
                    if torrent.has_metadata:
                        return torrent.get_files_dict()
            return []
        except Exception as e:
            print(f"Error getting files: {e}")
            return []
    
    def _update_loop(self):
        """Main update loop"""
        last_save_time = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                with self.lock:
                    for download_id, torrent in list(self.torrents.items()):
                        try:
                            # Update status
                            status = torrent.handle.status()
                            torrent.update_status(status)
                            
                            # Throttled file updates (important for large torrents)
                            # Only update every 5 seconds OR if metadata just arrived
                            current_time = time.time()
                            last_file_update = getattr(torrent, '_last_file_update', 0)
                            if not torrent.has_metadata or (current_time - last_file_update > 5.0):
                                torrent.update_files()
                                torrent._last_file_update = current_time
                            
                            # Check for deleted files
                            if torrent.status in [DownloadStatus.COMPLETED, DownloadStatus.SEEDING]:
                                if not torrent.check_files_exist():
                                    torrent.status = DownloadStatus.DELETED
                            
                            # Handle file selection after metadata is received (new downloads)
                            if torrent.has_metadata and hasattr(torrent, 'selected_files'):
                                # Ensure we have files to apply priorities to
                                if not torrent.files:
                                    torrent.update_files()
                                
                                if torrent.files:
                                    print(f"DEBUG: Applying file selection to {len(torrent.files)} files")
                                    
                                    # Priority mapping: UI (0=skip, 1=low, 2=normal, 3=high) -> libtorrent (0, 1, 4, 7)
                                    lt_priority_map = {0: 0, 1: 1, 2: 4, 3: 7}
                                    
                                    # Get priority info if available
                                    priority_map = getattr(torrent, 'selected_files_with_priority', {})
                                    
                                    # Set priorities for all files
                                    for i in range(len(torrent.files)):
                                        if i in torrent.selected_files:
                                            # Use user-specified priority or default to Normal
                                            ui_priority = priority_map.get(i, 2)
                                            lt_priority = lt_priority_map.get(ui_priority, 4)
                                            torrent.handle.file_priority(i, lt_priority)
                                            priority_name = {0: 'Skip', 1: 'Low', 4: 'Normal', 7: 'High'}.get(lt_priority, 'Normal')
                                            print(f"DEBUG: Set file {i} to priority {lt_priority} ({priority_name})")
                                        else:
                                            torrent.handle.file_priority(i, 0)  # Skip
                                    
                                    # Remove the attributes so we don't do this again
                                    delattr(torrent, 'selected_files')
                                    if hasattr(torrent, 'selected_files_with_priority'):
                                        delattr(torrent, 'selected_files_with_priority')
                                    # Force status update
                                    torrent.handle.resume()
                            
                            # Handle saved priorities from previous session (after restart)
                            if torrent.has_metadata and hasattr(torrent, 'saved_priorities'):
                                if not torrent.files:
                                    torrent.update_files()
                                
                                if torrent.files:
                                    saved_prios = torrent.saved_priorities
                                    if len(saved_prios) == len(torrent.files):
                                        print(f"DEBUG: Applying saved file priorities for {download_id}")
                                        torrent.handle.prioritize_files(saved_prios)
                                        # Remove the attribute so we don't do this again
                                        delattr(torrent, 'saved_priorities')
                                    else:
                                        print(f"WARNING: Saved priorities length mismatch ({len(saved_prios)} vs {len(torrent.files)})")
                                        delattr(torrent, 'saved_priorities')
                                
                        except Exception as e:
                            print(f"Error updating torrent {download_id}: {e}")
                
                # Save resume data every 60 seconds
                if current_time - last_save_time > 60:
                    self._save_resume_data()
                    self._save_state()
                    last_save_time = current_time
                
                self._notify_listeners()
                
            except Exception as e:
                print(f"Update loop error: {e}")
            
            time.sleep(0.5)
    
    def shutdown(self):
        """Shutdown the manager and ensure state is saved"""
        print("Shutting down torrent manager...")
        self.running = False
        
        # Save session state
        try:
            # First, trigger save for all torrents
            with self.lock:
                valid_handles = 0
                for downid, t in self.torrents.items():
                    if t.handle.is_valid():
                        t.handle.save_resume_data()
                        valid_handles += 1
            
            # Wait for alerts (up to 2 seconds)
            if valid_handles > 0:
                print(f"Waiting for {valid_handles} torrents to save resume data...")
                start_wait = time.time()
                saved_count = 0
                while (time.time() - start_wait) < 2.0 and saved_count < valid_handles:
                    if self.session.wait_for_alert(200):
                        alerts = self.session.pop_alerts()
                        for alert in alerts:
                            if isinstance(alert, lt.save_resume_data_alert):
                                try:
                                    # Use a robust helper for different libtorrent versions
                                    if hasattr(lt, 'write_resume_data'):
                                        # Libtorrent 2.0.x
                                        resume_data = lt.bencode(lt.write_resume_data(alert.params))
                                    elif hasattr(alert, 'resume_data'):
                                        # Libtorrent 1.2.x
                                        resume_data = lt.bencode(alert.resume_data)
                                    else:
                                        continue
                                        
                                    resume_path = os.path.join(self.state_path, f"{str(alert.handle.info_hash())}.fastresume")
                                    with open(resume_path, 'wb') as f:
                                        f.write(resume_data)
                                    saved_count += 1
                                    print(f"Saved resume data for {alert.handle.info_hash()} ({saved_count}/{valid_handles})")
                                except: pass
                            elif isinstance(alert, lt.save_resume_data_failed_alert):
                                saved_count += 1 # Count it so we don't wait forever for failures
                    else:
                        break # No more alerts coming likely

            # Save general state and DHT
            self._save_state()
            
            # Save DHT state for faster startup next time
            try:
                # save_state() returns all settings + DHT
                full_state = self.session.save_state()
                dht_state_path = os.path.join(self.state_path, "dht_state")
                with open(dht_state_path, 'wb') as f:
                    f.write(lt.bencode(full_state))
                print("[OK] Saved session and DHT state")
            except Exception as e:
                print(f"Warning: Could not save DHT state: {e}")
            
            if self.session:
                self.session.pause()
                time.sleep(0.5)
        except Exception as e:
            print(f"Error during shutdown: {e}")
            import traceback
            traceback.print_exc()
    
    def finalize_download(self, download_id, selected_indices, download_path=None):
        """
        Finalize a download by applying file selections and moving from temp to final location.

        Args:
            download_id: ID of the download to finalize
            selected_indices: List of file indices to download (others will be skipped)
            download_path: Optional custom download path for this specific download
        """
        with self.lock:
            download = self.torrents.get(download_id)

        if not download:
            print(f"Cannot finalize download {download_id}: Download not found")
            return None

        magnet = download.magnet
        name = download.name
        
        # Try to get magnet from handle if not available
        if not magnet or not magnet.startswith('magnet:'):
            try:
                if download.handle and download.handle.is_valid():
                    # Generate magnet from handle's torrent info
                    info_hash = str(download.handle.info_hash())
                    magnet = f"magnet:?xt=urn:btih:{info_hash}"
                    
                    # Add name if available
                    if download.handle.status().has_metadata:
                        ti = download.handle.torrent_file()
                        if ti:
                            from urllib.parse import quote
                            magnet += f"&dn={quote(ti.name())}"
                    
                    print(f"Generated magnet from handle: {magnet[:80]}...")
            except Exception as e:
                print(f"Failed to generate magnet from handle: {e}")
        
        print(f"DEBUG finalize: magnet={magnet[:60] if magnet else 'None'}...")
        
        # Check for saved .torrent file in state folder
        torrent_file_path = None
        if not magnet or not magnet.startswith('magnet:'):
            # Use self.state_path which is the correct state folder
            potential_files = [
                os.path.join(self.state_path, f"{download_id}.torrent"),
                os.path.join(self.state_path, f"{download.id}.torrent"),
            ]
            print(f"DEBUG finalize: Checking for torrent files in {self.state_path}")
            for path in potential_files:
                print(f"DEBUG finalize: Checking {path} - exists: {os.path.exists(path)}")
                if os.path.exists(path):
                    torrent_file_path = path
                    print(f"Found saved torrent file: {path}")
                    break

        print(f"DEBUG finalize: torrent_file_path={torrent_file_path}")
        print(f"Finalizing download {download_id} with {len(selected_indices)} selected files...")

        try:
            # Remove the existing download from temp location
            self.remove_download(download_id, delete_files=True)

            # Create a simple torrent object similar to what add_download expects
            class SimpleTorrent:
                def __init__(self, name, magnet, file_path=None):
                    self.name = name
                    self.magnet = magnet
                    self.magnet_uri = magnet
                    self.file_path = file_path

                def get_magnet_uri(self):
                    return self.magnet

            torrent_obj = SimpleTorrent(name, magnet, torrent_file_path)
            print(f"DEBUG finalize: SimpleTorrent created - file_path={torrent_obj.file_path}, magnet={torrent_obj.magnet[:50] if torrent_obj.magnet else 'None'}...")

            # Add the download again with selected files to the proper download path
            new_download = self.add_download(torrent_obj, selected_files=selected_indices, download_path=download_path)

            if new_download:
                print(f"Successfully finalized download {download_id} -> {new_download.id}")
                return new_download
            else:
                print(f"Failed to finalize download {download_id}")
                return None

        except Exception as e:
            print(f"Error finalizing download {download_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    def format_size(size):
        """Format bytes to human readable"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"
    
    @staticmethod
    def format_speed(bytes_per_sec):
        """Format speed to human readable"""
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"
