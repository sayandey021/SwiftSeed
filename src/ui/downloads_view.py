import flet as ft
from managers.torrent_manager import DownloadStatus, TorrentManager
import os
import subprocess
import platform
import time
import threading

class DownloadsView(ft.Container):
    def __init__(self, page, torrent_manager):
        super().__init__()
        self.page = page
        self.torrent_manager = torrent_manager
        self.torrent_manager.add_listener(self._on_update)
        self.expand = True
        self.padding = 20
        self._is_refreshing = False
        self._last_update_time = 0
        self._cached_state = {}
        self._update_lock = threading.Lock()
        # Dictionary to store controls for each download: {id: {control_name: control_instance}}
        self.download_controls = {} 
        self.content = self._build_view()

    def _build_view(self):
        self.downloads_list = ft.ListView(expand=True, spacing=10, padding=10)
        self._refresh_list()
        
        return ft.Column([
            ft.Row([
                ft.Text("Downloads", size=28, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.Icons.ADD_LINK,
                    tooltip="Add Magnet Link",
                    on_click=lambda e: self._show_add_magnet_dialog()
                ),
                ft.IconButton(
                    icon=ft.Icons.NOTE_ADD,
                    tooltip="Add .torrent File",
                    on_click=lambda e: self._pick_torrent_file()
                ),
                ft.IconButton(
                    icon=ft.Icons.FOLDER_OPEN,
                    tooltip="Open Downloads Folder",
                    on_click=lambda e: self._open_downloads_folder()
                ),
                ft.VerticalDivider(width=10),
                ft.ElevatedButton(
                    "Clear Completed",
                    icon=ft.Icons.CLEAR_ALL,
                    on_click=lambda e: self._clear_completed(),
                    style=ft.ButtonStyle(color=ft.Colors.RED)
                )
            ]),
            ft.Text("Manage your torrent downloads with full control", 
                   size=12, 
                   color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
            ft.Divider(),
            self.downloads_list
        ], expand=True)

    def _show_snack(self, message):
        """Helper to show snackbar"""
        try:
            snack = ft.SnackBar(
                content=ft.Text(message),
                duration=4000,  # 4 seconds
                action="OK"
            )
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()
            print(f"Snackbar shown: {message}")
        except Exception as ex:
            print(f"Snackbar display failed: {ex}")
            import traceback
            traceback.print_exc()

    def _show_add_magnet_dialog(self):
        magnet_input = ft.TextField(label="Magnet Link", expand=True, autofocus=True)
        
        def close_dlg(e):
            dlg.open = False
            self.page.update()

        def add_magnet(e):
            magnet = magnet_input.value.strip()
            
            # Validate magnet link
            if not magnet:
                self._show_snack("⚠️ Please enter a magnet link")
                return
            
            if not magnet.startswith("magnet:"):
                self._show_snack("❌ Invalid magnet link format. Must start with 'magnet:'")
                return
            
            # Basic check for info_hash
            if "xt=urn:btih:" not in magnet.lower():
                self._show_snack("❌ Invalid magnet link. Missing info hash (xt=urn:btih:)")
                return
            
            # Try to parse with libtorrent to validate
            try:
                import libtorrent as lt
                test_params = lt.parse_magnet_uri(magnet)
                if not test_params:
                    self._show_snack("❌ Invalid magnet link. Failed to parse.")
                    return
            except Exception as e:
                self._show_snack(f"❌ Invalid magnet link: {str(e).split('[')[0].strip()}")
                return
                
            close_dlg(e)
            
            # Create a dummy torrent object
            class MagnetTorrent:
                def __init__(self, link):
                    self.magnet = link
                    self.name = "Fetching Metadata..."
                    self.file_path = None
                def get_magnet_uri(self):
                    return self.magnet
            
            # Add torrent immediately to start fetching metadata
            download = self.torrent_manager.add_download(MagnetTorrent(magnet))
            
            if not download:
                self._show_snack("❌ Failed to add magnet link")
                return
            
            # Check if it's a duplicate
            if not getattr(download, 'is_newly_added', True):
                self._show_snack("ℹ️ Torrent already exists in downloads")
                download.visible = True
                self._refresh_list()
                return
            
            # Hide from list until confirmed
            download.visible = False
            self._refresh_list() # Force refresh to hide it if it appeared
                
            def cancel_loading(e=None):
                loading_dlg.open = False
                self.page.update()
                # Remove the download since we cancelled
                self.torrent_manager.remove_download(download.id, delete_files=True)

            loading_dlg = ft.AlertDialog(
                title=ft.Text("Loading Torrent Info"),
                content=ft.Column([
                    ft.ProgressRing(),
                    ft.Text("Fetching metadata... Please wait.", size=12),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, height=100, alignment=ft.MainAxisAlignment.CENTER),
                modal=True,
                actions=[
                    ft.TextButton("Cancel", on_click=cancel_loading)
                ],
                actions_alignment=ft.MainAxisAlignment.CENTER
            )
            
            self.page.overlay.append(loading_dlg)
            loading_dlg.open = True
            self.page.update()
            
            def poll_metadata():
                try:
                    start_time = time.time()
                    found = False
                    
                    # Give libtorrent time to start connecting (like qBittorrent does)
                    print("Waiting for peers and metadata...")
                    time.sleep(3)  # Initial wait for DHT/tracker responses
                    
                    # Wait up to 180 seconds for metadata
                    while time.time() - start_time < 180:
                        # Check if cancelled (dialog closed)
                        if not loading_dlg.open:
                            return

                        if download.has_metadata:
                            found = True
                            break
                        
                        # Check if metadata appeared in handle (backup check)
                        try:
                            if not download.handle.is_valid():
                                return
                            if download.handle.status().has_metadata:
                                # Try to update files immediately
                                download.update_files()
                                if download.files:  # If files populated, we're good
                                    # Set priorities to 0 immediately to prevent file creation
                                    for i in range(len(download.files)):
                                        self.torrent_manager.set_file_priority(download.id, i, 0)
                                        
                                    download.has_metadata = True
                                    found = True
                                    break
                        except:
                            pass
                            
                        time.sleep(2)  # Check every 2 seconds (not every second)
                    
                    if found:
                        # Ensure priorities are 0
                        if download.files:
                             for i in range(len(download.files)):
                                 self.torrent_manager.set_file_priority(download.id, i, 0)

                        # Pause download immediately to prevent auto-start of files while user selects
                        self.torrent_manager.pause_download(download.id)
                        
                        # Final check: ensure files are populated
                        if not download.files:
                            download.update_files()
                        
                        # Short retry if files still not there (rare edge case)
                        retry_count = 0
                        while len(download.files) == 0 and retry_count < 5:
                            time.sleep(1)
                            download.update_files()
                            retry_count += 1
                            if download.files:
                                break
                        
                        # If STILL no files after retries, abort
                        if len(download.files) == 0:
                            loading_dlg.open = False
                            self.page.update()
                            self.torrent_manager.remove_download(download.id)
                            self._show_snack("Failed to retrieve file list. The torrent metadata may be corrupted.")
                            return

                        loading_dlg.open = False
                        self.page.update()
                        
                        # Prepare files for dialog
                        files = []
                        print(f"DEBUG [downloads_view.py poll_metadata]: download.files type: {type(download.files)}")
                        print(f"DEBUG [downloads_view.py poll_metadata]: download.files length: {len(download.files) if hasattr(download.files, '__len__') else 'N/A'}")
                        for f in download.files:
                            files.append({
                                'index': f.index,
                                'name': f.path,
                                'size': self.torrent_manager.format_size(f.size),
                                'selected': True
                            })
                        print(f"DEBUG [downloads_view.py poll_metadata]: Built files list with {len(files)} files")
                        
                        # Update dummy torrent object
                        download.size = self.torrent_manager.format_size(download.total_size)
                        if download.handle.is_valid() and download.handle.status().has_metadata:
                            download.name = download.handle.torrent_file().name()
                        
                        def on_confirm(torrent, selected_files):
                            indices = [f['index'] for f in selected_files]
                            # First, set ALL files in the torrent to skip (priority 0)
                            # Use the actual number of files from the download object
                            if download.files:
                                for i in range(len(download.files)):
                                    self.torrent_manager.set_file_priority(download.id, i, 0)
                            # Then, set selected files to normal priority
                            for idx in indices:
                                self.torrent_manager.set_file_priority(download.id, idx, 2)
                            
                            # Resume download now that user confirmed
                            self.torrent_manager.resume_download(download.id)
                            # Make visible in list
                            download.visible = True
                            self._refresh_list()
                            self._show_snack("Download started!")

                        from ui.download_dialog import DownloadDialog
                        download_dlg = DownloadDialog(self.page, download, self.torrent_manager, on_confirm, files=files)
                        
                        def on_cancel(e):
                            # Only remove if it's not visible (meaning it was just added and not confirmed yet)
                            if not download.visible:
                                self.torrent_manager.remove_download(download.id, delete_files=True)
                            download_dlg.open = False
                            self.page.update()
                            
                        download_dlg.actions[0].on_click = on_cancel
                        
                        self.page.overlay.append(download_dlg)
                        download_dlg.open = True
                        self.page.update()
                    else:
                        # Metadata fetch failed - show retry dialog
                        loading_dlg.open = False
                        self.page.update()
                        
                        def on_retry(e):
                            retry_dlg.open = False
                            self.page.update()
                            # Restart the metadata polling
                            threading.Thread(target=poll_metadata, daemon=True).start()
                        
                        def on_cancel_retry(e):
                            retry_dlg.open = False
                            self.page.update()
                            self.torrent_manager.remove_download(download.id, delete_files=True)
                            self._show_snack("Download cancelled")
                        
                        retry_dlg = ft.AlertDialog(
                            title=ft.Text("Metadata Fetch Failed"),
                            content=ft.Text(
                                "Unable to retrieve torrent metadata after 3 minutes.\n\n"
                                "This could be due to:\n"
                                "• No seeders available\n"
                                "• Network connectivity issues\n"
                                "• Dead torrent\n\n"
                                "Would you like to try again?",
                                size=13
                            ),
                            actions=[
                                ft.TextButton("Retry", on_click=on_retry, icon=ft.Icons.REFRESH),
                                ft.TextButton("Cancel", on_click=on_cancel_retry, icon=ft.Icons.CANCEL),
                            ],
                            actions_alignment=ft.MainAxisAlignment.END
                        )
                        
                        self.page.overlay.append(retry_dlg)
                        retry_dlg.open = True
                        self.page.update()
                except Exception as e:
                    print(f"Error in poll_metadata: {e}")
                    loading_dlg.open = False
                    self.page.update()

            threading.Thread(target=poll_metadata, daemon=True).start()

        dlg = ft.AlertDialog(
            title=ft.Text("Add Magnet Link"),
            content=ft.Container(
                content=magnet_input,
                width=400,
                padding=10
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.TextButton("Next", on_click=add_magnet),
            ],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _pick_torrent_file(self):
        def on_file_picked(e: ft.FilePickerResultEvent):
            if e.files:
                file_path = e.files[0].path
                
                try:
                    import libtorrent as lt
                    ti = lt.torrent_info(file_path)
                    
                    files = []
                    for i in range(ti.num_files()):
                        file_entry = ti.files().at(i)
                        files.append({
                            'index': i,
                            'name': file_entry.path,
                            'size': self.torrent_manager.format_size(file_entry.size),
                            'selected': True
                        })
                    
                    # Create a dummy torrent object for the dialog
                    class FileTorrent:
                        def __init__(self, path, name, size):
                            self.file_path = path
                            self.name = name
                            self.size = size
                            self.seeders = 0
                            self.peers = 0
                            self.provider_name = "Local File"
                    
                    torrent_obj = FileTorrent(
                        file_path, 
                        ti.name(), 
                        self.torrent_manager.format_size(ti.total_size())
                    )
                    
                    def on_confirm(torrent, selected_files):
                        # Extract indices
                        indices = [f['index'] for f in selected_files]
                        
                        if self.torrent_manager.add_download(torrent, indices):
                             self._show_snack("Torrent added!")
                        else:
                             self._show_snack("Failed to add torrent")
                    
                    # Show dialog
                    from ui.download_dialog import DownloadDialog
                    dlg = DownloadDialog(self.page, torrent_obj, self.torrent_manager, on_confirm, files=files)
                    self.page.overlay.append(dlg)
                    dlg.open = True
                    self.page.update()
                    
                except Exception as ex:
                    print(f"Error parsing torrent file: {ex}")
                    self._show_snack(f"Invalid torrent file: {ex}")

        file_picker = ft.FilePicker(on_result=on_file_picked)
        self.page.overlay.append(file_picker)
        self.page.update()
        file_picker.pick_files(allow_multiple=False, allowed_extensions=["torrent"])

    def _open_downloads_folder(self):
        path = self.torrent_manager.download_path
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _clear_completed(self):
        self.torrent_manager.remove_completed_downloads()
        self._refresh_list()

    def _refresh_list(self):
        if not self.page:
            return
        
        try:
            self._is_refreshing = True
            
            downloads = self.torrent_manager.downloads
            # Filter only visible downloads
            visible_downloads = [d for d in downloads if getattr(d, 'visible', True)]
            
            if not visible_downloads:
                self.downloads_list.controls.clear()
                self.download_controls.clear()
                self.downloads_list.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.DOWNLOAD_DONE, size=64, 
                                   color=ft.Colors.GREY_400 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_600),
                            ft.Text("No active downloads", 
                                   color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        padding=50
                    )
                )
            else:
                # Remove empty state if present
                if len(self.downloads_list.controls) == 1 and isinstance(self.downloads_list.controls[0], ft.Container) and hasattr(self.downloads_list.controls[0], "content") and isinstance(self.downloads_list.controls[0].content, ft.Column):
                     # Check if it's the "No active downloads" container
                     col = self.downloads_list.controls[0].content
                     if len(col.controls) >= 2 and isinstance(col.controls[1], ft.Text) and col.controls[1].value == "No active downloads":
                         self.downloads_list.controls.clear()

                current_ids = set(d.id for d in visible_downloads)
                existing_ids = set(self.download_controls.keys())
                
                # Remove old downloads
                for old_id in existing_ids - current_ids:
                    controls = self.download_controls.pop(old_id)
                    if controls['card'] in self.downloads_list.controls:
                        self.downloads_list.controls.remove(controls['card'])
                
                # Add or update downloads
                for item in visible_downloads:
                    if item.id not in self.download_controls:
                        # Create new card
                        card, controls = self._create_download_card(item)
                        self.download_controls[item.id] = controls
                        self.downloads_list.controls.append(card)
                    else:
                        # Update existing card
                        self._update_download_card(item, self.download_controls[item.id])
                        
        except Exception as e:
            print(f"Error refreshing list: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._is_refreshing = False
        
        if self.page:
            try:
                self.page.update()
            except Exception as e:
                print(f"Error updating page: {e}")

    def _create_download_card(self, item):
        # Create controls
        name_text = ft.Text(item.name, weight=ft.FontWeight.BOLD, expand=True, size=14)
        
        pause_btn = ft.IconButton(
            ft.Icons.PAUSE if item.status in [DownloadStatus.DOWNLOADING, DownloadStatus.SEEDING, DownloadStatus.QUEUED] else ft.Icons.PLAY_ARROW,
            tooltip="Pause/Resume",
            icon_size=20,
            on_click=lambda e, download_id=item.id: self._toggle_pause(download_id)
        )
        
        stop_btn = ft.IconButton(
            ft.Icons.STOP,
            tooltip="Stop",
            icon_size=20,
            icon_color=ft.Colors.ORANGE,
            on_click=lambda e, download_id=item.id: self._stop_download(download_id)
        )
        
        progress_bar = ft.ProgressBar(value=item.progress, height=8)
        status_text = ft.Text(f"{item.status.value}", size=12, weight=ft.FontWeight.BOLD)
        status_container = ft.Container(content=status_text, padding=ft.padding.only(right=10))
        progress_text = ft.Text(f"Progress: {item.progress*100:.1f}%", size=11)
        size_text = ft.Text(f"Size: {TorrentManager.format_size(item.total_size)}", size=11)
        
        down_speed_text = ft.Text(f"{TorrentManager.format_speed(item.download_rate)}", size=11)
        up_speed_text = ft.Text(f"{TorrentManager.format_speed(item.upload_rate)}", size=11)
        peers_text = ft.Text(f"Peers: {item.num_peers} ({item.num_seeds} seeds)", size=11)
        eta_text = ft.Text(f"ETA: {item.eta}", size=11)
        
        downloaded_text = ft.Text(f"↓ Downloaded: {TorrentManager.format_size(item.downloaded_bytes)}", size=11)
        uploaded_text = ft.Text(f"↑ Uploaded: {TorrentManager.format_size(item.uploaded_bytes)}", size=11)
        ratio_text = ft.Text(f"Ratio: {(item.uploaded_bytes / item.downloaded_bytes if item.downloaded_bytes > 0 else 0):.2f}", size=11)

        # Assemble Card
        card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.FOLDER, color=ft.Colors.BLUE, size=20),
                        name_text,
                        ft.IconButton(
                            ft.Icons.FOLDER_OPEN,
                            tooltip="Open Folder",
                            icon_size=20,
                            on_click=lambda e, download_id=item.id: self._open_folder(download_id)
                        ),
                        ft.IconButton(
                            ft.Icons.LIST,
                            tooltip="Show Files",
                            icon_size=20,
                            on_click=lambda e, download_id=item.id: self._show_files(download_id)
                        ),
                        pause_btn,
                        stop_btn,
                        ft.IconButton(
                            ft.Icons.DELETE,
                            icon_size=20,
                            icon_color=ft.Colors.RED,
                            tooltip="Delete",
                            on_click=lambda e, download_id=item.id: self._delete_download(download_id)
                        )
                    ]),
                    progress_bar,
                    ft.Row([
                        status_container,
                        progress_text,
                        ft.Container(width=10),
                        size_text,
                    ], spacing=5),
                    ft.Row([
                        ft.Row([
                            ft.Icon(ft.Icons.ARROW_DOWNWARD, size=12, color=ft.Colors.GREEN),
                            down_speed_text,
                        ], spacing=2),
                        ft.Container(width=10),
                        ft.Row([
                            ft.Icon(ft.Icons.ARROW_UPWARD, size=12, color=ft.Colors.BLUE),
                            up_speed_text,
                        ], spacing=2),
                        ft.Container(width=10),
                        ft.Row([
                            ft.Icon(ft.Icons.PEOPLE, size=12, color=ft.Colors.ORANGE),
                            peers_text,
                        ], spacing=2),
                        ft.Container(width=10),
                        eta_text,
                    ], spacing=5),
                    ft.Row([
                        downloaded_text,
                        ft.Container(width=10),
                        uploaded_text,
                        ft.Container(width=10),
                        ratio_text,
                    ], spacing=5),
                ], spacing=8),
                padding=15
            ),
            elevation=2
        )
        
        # Initial update of colors
        self._update_colors(item, progress_bar, status_text)

        controls = {
            'card': card,
            'name_text': name_text,
            'pause_btn': pause_btn,
            'stop_btn': stop_btn,
            'progress_bar': progress_bar,
            'status_text': status_text,
            'progress_text': progress_text,
            'size_text': size_text,
            'down_speed_text': down_speed_text,
            'up_speed_text': up_speed_text,
            'peers_text': peers_text,
            'eta_text': eta_text,
            'downloaded_text': downloaded_text,
            'uploaded_text': uploaded_text,
            'ratio_text': ratio_text
        }
        return card, controls

    def _update_download_card(self, item, controls):
        # Update values
        controls['name_text'].value = item.name
        
        # Update buttons state
        controls['pause_btn'].icon = ft.Icons.PAUSE if item.status in [DownloadStatus.DOWNLOADING, DownloadStatus.SEEDING, DownloadStatus.QUEUED] else ft.Icons.PLAY_ARROW
        controls['pause_btn'].disabled = (item.status in [DownloadStatus.STOPPED, DownloadStatus.COMPLETED])
        controls['stop_btn'].disabled = (item.status in [DownloadStatus.STOPPED, DownloadStatus.COMPLETED])
        
        # Update progress and text
        controls['progress_bar'].value = item.progress
        controls['status_text'].value = f"{item.status.value}"
        controls['progress_text'].value = f"Progress: {item.progress*100:.1f}%"
        controls['size_text'].value = f"Size: {TorrentManager.format_size(item.total_size)}"
        
        controls['down_speed_text'].value = f"{TorrentManager.format_speed(item.download_rate)}"
        controls['up_speed_text'].value = f"{TorrentManager.format_speed(item.upload_rate)}"
        controls['peers_text'].value = f"Peers: {item.num_peers} ({item.num_seeds} seeds)"
        controls['eta_text'].value = f"ETA: {item.eta}"
        
        controls['downloaded_text'].value = f"↓ Downloaded: {TorrentManager.format_size(item.downloaded_bytes)}"
        controls['uploaded_text'].value = f"↑ Uploaded: {TorrentManager.format_size(item.uploaded_bytes)}"
        controls['ratio_text'].value = f"Ratio: {(item.uploaded_bytes / item.downloaded_bytes if item.downloaded_bytes > 0 else 0):.2f}"
        
        self._update_colors(item, controls['progress_bar'], controls['status_text'])

    def _update_colors(self, item, progress_bar, status_text):
        progress_color = ft.Colors.BLUE
        if item.status == DownloadStatus.COMPLETED:
            progress_color = ft.Colors.GREEN
        elif item.status == DownloadStatus.DOWNLOADING_METADATA:
            progress_color = ft.Colors.ORANGE
        elif item.status == DownloadStatus.PAUSED:
            progress_color = ft.Colors.GREY
        elif item.status == DownloadStatus.ERROR:
            progress_color = ft.Colors.RED
        elif item.status == DownloadStatus.SEEDING:
            progress_color = ft.Colors.LIGHT_GREEN
        elif item.status == DownloadStatus.STOPPED:
            progress_color = ft.Colors.AMBER
        elif item.status == DownloadStatus.QUEUED:
            progress_color = ft.Colors.CYAN
            
        progress_bar.color = progress_color
        progress_bar.bgcolor = ft.Colors.GREY_200 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_800
        status_text.color = progress_color

    def _toggle_pause(self, id):
        try:
            item = next((d for d in self.torrent_manager.downloads if d.id == id), None)
            if item:
                if item.status in [DownloadStatus.DOWNLOADING, DownloadStatus.SEEDING, DownloadStatus.QUEUED]:
                    self.torrent_manager.pause_download(id)
                else:
                    self.torrent_manager.resume_download(id)
                time.sleep(0.1)
                self._refresh_list()
        except Exception as e:
            print(f"Error in toggle_pause: {e}")
    
    def _stop_download(self, id):
        try:
            self.torrent_manager.stop_download(id)
            time.sleep(0.1)
            self._refresh_list()
        except Exception as e:
            print(f"Error in stop_download: {e}")

    def _delete_download(self, id):
        def delete_action(e, delete_files):
            self._close_files_dialog(dlg)
            self.torrent_manager.remove_download(id, delete_files=delete_files)
            self._refresh_list()
        
        # Clean up previous dialogs from overlay
        if self.page.overlay:
            self.page.overlay.clear()
            
        dlg = ft.AlertDialog(
            title=ft.Text("Remove Download"),
            content=ft.Text("What would you like to do with this download?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self._close_files_dialog(dlg)),
                ft.TextButton("Remove from List", on_click=lambda e: delete_action(e, False)),
                ft.TextButton("Delete Files & Remove", on_click=lambda e: delete_action(e, True), style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=lambda e: self._close_files_dialog(dlg)
        )
        
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _open_folder(self, id):
        item = next((d for d in self.torrent_manager.downloads if d.id == id), None)
        if not item:
            return

        # Libtorrent saves torrents in save_path/torrent_name/
        # We need to construct the actual torrent folder path
        torrent_folder = os.path.join(item.save_path, item.name)
        
        # Check if the torrent folder exists, otherwise fall back to save_path
        if os.path.exists(torrent_folder):
            path = torrent_folder
        elif os.path.exists(item.save_path):
            # If torrent folder doesn't exist yet, open the base folder
            path = item.save_path
        else:
            # Create the folder if it doesn't exist
            try:
                os.makedirs(item.save_path)
                path = item.save_path
            except:
                return
            
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            print(f"Error opening folder: {e}")
    
    def _close_files_dialog(self, dialog):
        """Close the files dialog"""
        try:
            print(f"DEBUG: Closing files dialog...")
            dialog.open = False
            self.page.update()
            print(f"DEBUG: Dialog closed (open=False)")
            
            # Optional: Clean up overlay after a delay or next time
            # For now, we just hide it to prevent the "stuck" issue
            # caused by removing it from the tree too quickly
        except Exception as e:
            print(f"Error closing dialog: {e}")

    def _show_files(self, download_id):
        print(f"DEBUG: _show_files called for {download_id}")
        try:
            # Clean up previous dialogs from overlay
            if self.page.overlay:
                self.page.overlay.clear()
            
            item = next((i for i in self.torrent_manager.downloads if i.id == download_id), None)
            if not item:
                print("Download not found")
                return
            
            # Use get_files to safely retrieve file list (returns dicts)
            files = self.torrent_manager.get_files(download_id)
            print(f"DEBUG: Retrieved {len(files)} files for {item.name}")
            
            dialog_content = ft.Column(scroll=ft.ScrollMode.AUTO, height=400, width=700, spacing=5)
            
            if not item.has_metadata:
                dialog_content.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.ProgressRing(),
                            ft.Text("Loading metadata...", size=14),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=40,
                        alignment=ft.alignment.center
                    )
                )
            elif files:
                for file_info in files:
                    path = file_info['path']
                    file_name = path.split('/')[-1] if '/' in path else path
                    # Handle windows paths too just in case
                    if '\\' in file_name:
                        file_name = file_name.split('\\')[-1]
                        
                    size_str = TorrentManager.format_size(file_info['size'])
                    progress = file_info['progress']
                    priority = file_info.get('priority', 4)
                    
                    # Highlight skipped files (priority 0) in red
                    is_skipped = priority == 0
                    text_color = ft.Colors.RED if is_skipped else None
                    
                    dialog_content.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=20, color=text_color),
                            title=ft.Text(file_name, size=12, color=text_color),
                            subtitle=ft.Text(f"Size: {size_str} | Progress: {progress*100:.1f}%", size=10, color=text_color),
                        )
                    )
            else:
                dialog_content.controls.append(ft.Text("No files available", size=12))
            
            dlg = ft.AlertDialog(
                title=ft.Text(f"Files: {item.name}", size=14, weight=ft.FontWeight.BOLD),
                content=dialog_content,
                actions=[ft.TextButton("Close", on_click=lambda e: self._close_files_dialog(dlg))],
                on_dismiss=lambda e: self._close_files_dialog(dlg)
            )
            
            self.page.overlay.append(dlg)
            dlg.open = True
            self.page.update()
            print(f"Opened file dialog for: {item.name} (added to overlay)")
        except Exception as e:
            print(f"Error showing files: {e}")
            import traceback
            traceback.print_exc()

    def _on_update(self):
        current_time = time.time()
        has_changes = self._detect_changes()
        
        if has_changes or (current_time - self._last_update_time >= 2.0 and self.torrent_manager.downloads):
            with self._update_lock:
                if not self._is_refreshing:
                    self._last_update_time = current_time
                    self._refresh_list()
    
    def _detect_changes(self):
        current_state = {}
        for download in self.torrent_manager.downloads:
            state_key = (
                download.id,
                download.status.value,
                int(download.progress * 100),
                download.total_size,
                len(download.files) if hasattr(download, 'files') and download.files else 0
            )
            current_state[download.id] = state_key
        
        if current_state != self._cached_state:
            self._cached_state = current_state
            return True
        return False
