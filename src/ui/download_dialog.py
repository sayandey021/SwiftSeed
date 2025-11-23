import flet as ft
import os

class DownloadDialog(ft.AlertDialog):
    """Dialog for selecting which files to download from a torrent"""
    
    def __init__(self, page, torrent, download_manager, on_confirm, files=None):
        self.page = page
        self.torrent = torrent
        self.download_manager = download_manager
        self.on_confirm_callback = on_confirm
        self.selected_files = []
        self.file_checkboxes = []
        
        # Use provided files or simulate
        print(f"DEBUG [DownloadDialog.__init__]: files parameter: {files}")
        print(f"DEBUG [DownloadDialog.__init__]: files is None? {files is None}")
        print(f"DEBUG [DownloadDialog.__init__]: files length: {len(files) if files is not None else 'N/A'}")
        if files is not None:
            print(f"DEBUG [DownloadDialog.__init__]: Using provided files list (v2)")
            self.files = files
        else:
            print(f"DEBUG [DownloadDialog.__init__]: Files is None, falling back to _get_torrent_files")
            self.files = self._get_torrent_files(torrent)
        
        super().__init__(
            title=ft.Text("Select Files to Download", weight=ft.FontWeight.BOLD),
            content=self._build_content(),
            actions=self._build_actions(),
            modal=True,
        )
    
    def _get_torrent_files(self, torrent):
        """Get list of files from torrent. Intelligently detects episodes and files."""
        # In real implementation with libtorrent, this would parse torrent metadata
        # For now, create an intelligent file list based on the torrent name
        
        name = torrent.name
        name = torrent.name
        
        # Handle size (string or int)
        if hasattr(torrent, 'size'):
            size = torrent.size
        elif hasattr(torrent, 'total_size'):
            size = self.download_manager.format_size(torrent.total_size)
        else:
            size = "0 B"
        
        files = []
        
        # Parse size to get numeric value and unit
        try:
            parts = size.split()
            if len(parts) >= 2:
                size_value = float(parts[0])
                size_unit = parts[1]
            else:
                size_value = float(size)
                size_unit = "B"
        except:
            size_value = 1.0
            size_unit = "GB"
        
        # Detect TV show episodes (S01E01, S02E01, etc.)
        import re
        
        # Pattern 1: Season in name (e.g., "Show S02" or "Show Season 2")
        season_match = re.search(r'[Ss](?:eason\s*)?(\d{1,2})', name)
        
        # Pattern 2: Episode range (e.g., "S02E01-E08" or "E01-E08")
        episode_range = re.search(r'[Ee](\d{2})-[Ee]?(\d{2})', name)
        
        # Pattern 3: Complete season or multiple episodes
        is_season = any(x in name.lower() for x in ['season', 'complete', 's0', 's1', 's2'])
        
        if season_match and 'season' in name.lower():
            # This is a TV season
            season_num = season_match.group(1)
            
            # Determine number of episodes
            if episode_range:
                start_ep = int(episode_range.group(1))
                end_ep = int(episode_range.group(2))
                num_episodes = end_ep - start_ep + 1
            else:
                # Estimate based on common season lengths
                # Check torrent name for clues
                if '10bits' in name.lower() or '10bit' in name.lower():
                    num_episodes = 8  # Common for streaming shows
                else:
                    num_episodes = 10  # Default estimate
            
            # Extract show name (everything before season indicator)
            show_name = re.split(r'[Ss]\d{2}|[Ss]eason', name)[0].strip()
            
            # Calculate size per episode
            size_per_episode = size_value / num_episodes
            
            # Generate episode files
            for ep in range(1, num_episodes + 1):
                episode_name = f"{show_name} - S{season_num.zfill(2)}E{ep:02d}"
                
                # Try to extract episode titles if present in original name
                # For now, use generic format
                files.append({
                    'index': ep-1, # Fake index
                    'name': f"{episode_name}.mkv",
                    'size': f"{size_per_episode:.1f} {size_unit}",
                    'selected': True
                })
        
        elif any(x in name.lower() for x in ['collection', 'trilogy', 'series']):
            # Movie collection or trilogy
            # Extract base name
            base_name = re.split(r'(?i)(collection|trilogy|series)', name)[0].strip()
            
            # Determine number of items
            if 'trilogy' in name.lower():
                num_items = 3
            elif 'collection' in name.lower():
                num_items = 5  # Estimate
            else:
                num_items = 3
            
            size_per_item = size_value / num_items
            
            for i in range(1, num_items + 1):
                files.append({
                    'index': i-1,
                    'name': f"{base_name} - Part {i}.mkv",
                    'size': f"{size_per_item:.1f} {size_unit}",
                    'selected': True
                })
        
        else:
            # Single file torrent or movie
            # Determine extension
            ext = '.mkv'
            if 'apk' in name.lower() or 'android' in name.lower():
                ext = '.apk'
            elif any(x in name.lower() for x in ['iso', 'ubuntu', 'linux', 'windows']):
                ext = '.iso'
            elif any(x in name.lower() for x in ['zip', 'archive']):
                ext = '.zip'
            elif any(x in name.lower() for x in ['mp3', 'flac', 'album', 'music']):
                ext = '.mp3'
            
            # Clean up name for display
            display_name = name
            if not any(name.endswith(e) for e in ['.mkv', '.mp4', '.avi', '.apk', '.iso', '.zip']):
                display_name = f"{name}{ext}"
            
            files.append({
                'index': 0,
                'name': display_name,
                'size': size,
                'selected': True
            })
            
            # Add common extras (subtitles, samples, etc.) for movies
            if any(x in name.lower() for x in ['movie', '1080p', '720p', '4k', 'bluray', 'webrip']):
                files.append({
                    'index': 1,
                    'name': f"{name}.srt",
                    'size': "100 KB",
                    'selected': False
                })
                files.append({
                    'index': 2,
                    'name': "Sample.mkv",
                    'size': "50 MB",
                    'selected': False
                })
        
        return files
    
    def _build_content(self):
        """Build the file selection content"""
        content_column = ft.Column([], spacing=10, tight=True)
        
        # Warning about metadata (only show if no real files)
        if not self.files or (len(self.files) == 1 and self.files[0].get('name') == "Magnet Download"):
            content_column.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.BLUE, size=30),
                        ft.Column([
                            ft.Text("Magnet Link Info", weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.BLUE),
                            ft.Text("Metadata must be downloaded first. You can manage file priorities in the Downloads tab after the torrent starts.", 
                                   size=12, color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                        ], spacing=2, expand=True)
                    ], spacing=10),
                    padding=10,
                    bgcolor=ft.Colors.BLUE_50 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.BLUE_GREY_900,
                    border_radius=8,
                    border=ft.border.all(1, ft.Colors.BLUE),
                )
            )
        
        # Get stats safely (handle both Torrent and TorrentDownload objects)
        seeders = getattr(self.torrent, 'seeders', getattr(self.torrent, 'num_seeds', 0))
        peers = getattr(self.torrent, 'peers', getattr(self.torrent, 'num_peers', 0))
        
        # Get size safely
        if hasattr(self.torrent, 'size'):
            size_str = self.torrent.size
        elif hasattr(self.torrent, 'total_size'):
            size_str = self.download_manager.format_size(self.torrent.total_size)
        else:
            size_str = "Unknown"

        # Torrent info header
        content_column.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Text(self.torrent.name, weight=ft.FontWeight.BOLD, size=14),
                    ft.Text(f"Total Size: {size_str}", size=12, 
                           color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                    ft.Text(f"Seeders: {seeders} | Peers: {peers}", 
                           size=12, color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                ], spacing=5),
                padding=10,
                bgcolor=ft.Colors.BLUE_GREY_900 if self.page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLUE_GREY_100,
                border_radius=8,
                width=float('inf'), # Full width
            )
        )
        
        content_column.controls.append(ft.Divider())
        
        # Select/Deselect all buttons
        def select_all(e):
            for cb in self.file_checkboxes:
                cb.value = True
                cb.update()
        
        def deselect_all(e):
            for cb in self.file_checkboxes:
                cb.value = False
                cb.update()
        
        content_column.controls.append(
            ft.Row([
                ft.TextButton("Select All", icon=ft.Icons.CHECK_BOX, on_click=select_all),
                ft.TextButton("Deselect All", icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK, on_click=deselect_all),
            ])
        )
        
        content_column.controls.append(ft.Text("Files:", weight=ft.FontWeight.BOLD))
        
        # Build file tree structure
        tree = {}
        for file_info in self.files:
            # Debug: print the path to see what we're getting
            print(f"DEBUG: File path received: '{file_info['name']}'")
            
            # Normalize path separators - replace all backslashes with forward slashes
            normalized_path = file_info['name'].replace('\\', '/')
            
            # Split by forward slash
            path_parts = normalized_path.split('/')
            
            # Filter out empty parts
            path_parts = [p for p in path_parts if p]
            
            print(f"DEBUG: Path parts: {path_parts}")
                
            current_level = tree
            for i, part in enumerate(path_parts):
                if i == len(path_parts) - 1:
                    # It's a file
                    current_level[part] = {'type': 'file', 'data': file_info}
                else:
                    # It's a folder
                    if part not in current_level:
                        current_level[part] = {'type': 'folder', 'children': {}}
                    current_level = current_level[part]['children']
        
        # Recursive function to build UI
        # Recursive function to build UI
        def build_tree_ui(node):
            items = []
            # Sort: folders first, then files
            sorted_keys = sorted(node.keys(), key=lambda k: (1 if node[k].get('type') == 'file' else 0, k))
            
            for key in sorted_keys:
                item = node[key]
                is_file = item.get('type') == 'file'
                
                if is_file:
                    file_info = item['data']
                    # Checkbox without label, we'll use a separate Text for better control
                    checkbox = ft.Checkbox(
                        value=file_info['selected'],
                        data=file_info
                    )
                    self.file_checkboxes.append(checkbox)
                    
                    row = ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=16, color=ft.Colors.BLUE),
                            checkbox,
                            # Allow text to wrap
                            ft.Text(key, size=12, expand=True, selectable=True),
                            ft.Text(file_info['size'], size=11, width=80, text_align=ft.TextAlign.RIGHT,
                                   color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START, spacing=10),
                        padding=ft.padding.only(left=10, top=5, bottom=5),
                    )
                    items.append(row)
                else:
                    # Folder
                    children_ui = build_tree_ui(item['children'])
                    
                    # Folder checkbox logic
                    def on_folder_check(e):
                        is_checked = e.control.value
                        
                        # Helper to collect all file data objects under this folder
                        def get_all_files(node_dict):
                            files = []
                            for k, v in node_dict.items():
                                if v.get('type') == 'file':
                                    files.append(v['data'])
                                else:
                                    files.extend(get_all_files(v['children']))
                            return files
                            
                        child_files = get_all_files(item['children'])
                        child_file_ids = [id(f) for f in child_files]
                        
                        for cb in self.file_checkboxes:
                            if hasattr(cb, 'data') and id(cb.data) in child_file_ids:
                                cb.value = is_checked
                                cb.update()
                                
                    folder_checkbox = ft.Checkbox(
                        value=True,
                        on_change=on_folder_check,
                        tooltip="Select/Deselect All in Folder"
                    )
                    
                    # Use ExpansionTile for folders
                    # Align checkbox with files: Icon (leading) -> Checkbox + Name (title)
                    expansion_tile = ft.ExpansionTile(
                        leading=ft.Icon(ft.Icons.FOLDER, color=ft.Colors.AMBER),
                        title=ft.Row([
                            folder_checkbox,
                            # Allow folder name to wrap
                            ft.Text(key, weight=ft.FontWeight.BOLD, size=13, expand=True),
                        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START),
                        controls=children_ui,
                        initially_expanded=False,
                        controls_padding=ft.padding.only(left=20),
                    )
                    
                    items.append(expansion_tile)
            
            return items

        # Build the tree UI
        tree_items = build_tree_ui(tree)
        
        # Use a ListView for the file list to handle scrolling better
        file_list = ft.ListView(
            controls=tree_items,
            expand=True,
            spacing=2,
            # Add extra right padding for scrollbar
            padding=ft.padding.only(left=10, right=25, top=10, bottom=10)
        )
        
        content_column.controls.append(
            ft.Container(
                content=file_list,
                height=300, # Fixed height for file list
                # Transparent look - no border
                # border=ft.border.all(1, ft.Colors.GREY_400),
                # border_radius=5,
            )
        )
        
        # Add Save .torrent button
        content_column.controls.append(
            ft.Container(
                content=ft.OutlinedButton(
                    "Save .torrent file",
                    icon=ft.Icons.SAVE,
                    on_click=self._on_save_torrent_click
                ),
                padding=ft.padding.only(top=10)
            )
        )
        
        # Wrap in container with max height
        return ft.Container(
            content=content_column,
            width=600,
            height=500, # Increased height
        )
    
    def _build_actions(self):
        """Build dialog action buttons"""
        return [
            ft.TextButton("Cancel", on_click=self._on_cancel),
            ft.ElevatedButton(
                "Start Download",
                icon=ft.Icons.DOWNLOAD,
                on_click=self._on_start_download,
                bgcolor=ft.Colors.GREEN_700,
                color=ft.Colors.WHITE
            ),
        ]
    
    def _on_cancel(self, e):
        """Cancel button handler"""
        self.open = False
        self.page.update()
    
    def _on_start_download(self, e):
        """Start download with selected files"""
        # Get selected files
        selected = []
        for cb in self.file_checkboxes:
            if cb.value:
                # Use the data we attached to the checkbox
                if hasattr(cb, 'data'):
                    selected.append(cb.data)
                else:
                    # Fallback for legacy/simulated files without data attribute
                    # This shouldn't happen with the new implementation but good for safety
                    idx = self.file_checkboxes.index(cb)
                    if idx < len(self.files):
                        selected.append(self.files[idx])
        
        if not selected:
            # Show error if no files selected
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Please select at least one file to download"),
                bgcolor=ft.Colors.RED_700
            )
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        # Store selected files
        self.selected_files = selected
        
        # Close dialog
        self.open = False
        self.page.update()
        
        # Call the confirmation callback
        if self.on_confirm_callback:
            self.on_confirm_callback(self.torrent, selected)

    def _on_save_torrent_click(self, e):
        """Handle save torrent button click - Save directly to Downloads"""
        print("DEBUG: Save torrent clicked")
        
        try:
            # Get Downloads folder
            downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
            
            if not os.path.exists(downloads_path):
                try:
                    os.makedirs(downloads_path)
                except:
                    # Fallback to home dir if Downloads doesn't exist/writable
                    downloads_path = os.path.expanduser('~')
                
            # Construct filename
            file_name = f"{self.torrent.name}.torrent"
            # Sanitize
            file_name = "".join(c for c in file_name if c.isalnum() or c in (' ', '.', '_', '-')).strip()
            dest_path = os.path.join(downloads_path, file_name)
            
            # Save logic
            # Check if it's a libtorrent handle (Magnet)
            if hasattr(self.torrent, 'handle') and self.torrent.handle.is_valid():
                import libtorrent as lt
                info = self.torrent.handle.torrent_file()
                t = lt.create_torrent(info)
                content = lt.bencode(t.generate())
                with open(dest_path, 'wb') as f:
                    f.write(content)
            
            # Check if it's a local file (FileTorrent)
            elif hasattr(self.torrent, 'file_path') and self.torrent.file_path and os.path.exists(self.torrent.file_path):
                import shutil
                shutil.copy2(self.torrent.file_path, dest_path)
            else:
                self.page.snack_bar = ft.SnackBar(content=ft.Text("Could not save: Source not available"))
                self.page.snack_bar.open = True
                self.page.update()
                return

            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Saved to {file_name}"),
                action="Open Folder",
                on_action=lambda _: self._open_folder(downloads_path)
            )
            self.page.snack_bar.open = True
            self.page.update()
            
        except Exception as ex:
            print(f"Error saving torrent: {ex}")
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Error: {ex}"))
            self.page.snack_bar.open = True
            self.page.update()

    def _open_folder(self, path):
        try:
            if os.name == 'nt':
                os.startfile(path)
            elif os.name == 'posix':
                import subprocess
                subprocess.Popen(['xdg-open', path])
            else:
                import subprocess
                subprocess.Popen(['open', path])
        except:
            pass
