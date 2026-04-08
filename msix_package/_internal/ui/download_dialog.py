import flet as ft
import os

class DownloadDialog(ft.AlertDialog):
    """Dialog for selecting which files to download from a torrent"""
    
    def __init__(self, page, torrent, download_manager, on_confirm, on_cancel=None, files=None):
        self.page = page
        self.torrent = torrent
        self.download_manager = download_manager
        self.on_confirm_callback = on_confirm
        self.on_cancel_callback = on_cancel
        self.selected_files = []
        self.file_checkboxes = []
        self.file_priorities = {}  # Map file index to priority
        
        # Custom download path for this specific download
        # Initialize with default path from settings
        try:
            self.custom_download_path = download_manager.settings_manager.get('download_folder', 
                os.path.join(os.path.expanduser("~"), "Downloads", "SwiftSeed Download"))
        except:
            self.custom_download_path = os.path.join(os.path.expanduser("~"), "Downloads", "SwiftSeed Download")
        
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
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
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
        """Build the file selection content with two-column layout"""
        
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
        
        # Get magnet/hash info
        magnet_link = ""
        info_hash = ""
        if hasattr(self.torrent, 'get_magnet_uri'):
            magnet_link = self.torrent.get_magnet_uri() or ""
        elif hasattr(self.torrent, 'magnet'):
            magnet_link = self.torrent.magnet or ""
        elif hasattr(self.torrent, 'magnet_uri'):
            magnet_link = self.torrent.magnet_uri or ""
        
        # Extract info hash from magnet
        if magnet_link and 'btih:' in magnet_link.lower():
            try:
                info_hash = magnet_link.lower().split('btih:')[1].split('&')[0].upper()
            except:
                info_hash = "Unknown"
        
        # Get provider info
        provider = getattr(self.torrent, 'provider_name', 'Unknown')
        
        # ============ RIGHT PANEL - Torrent Info ============
        # Download location selector - editable text field
        def on_path_change(e):
            self.custom_download_path = e.control.value
        
        self.path_field = ft.TextField(
            value=self.custom_download_path,
            text_size=11,
            height=38,
            expand=True,
            border_color=ft.Colors.AMBER_400 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.AMBER_700,
            focused_border_color=ft.Colors.AMBER_600,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
            on_change=on_path_change,
            hint_text="Enter download path...",
        )
        
        def on_folder_picked(e: ft.FilePickerResultEvent):
            if e.path:
                self.custom_download_path = e.path
                self.path_field.value = e.path
                self.path_field.update()
        
        # Store folder picker reference
        self.folder_picker = ft.FilePicker(on_result=on_folder_picked)
        self.page.overlay.append(self.folder_picker)
        self.page.update()
        
        # Magnet link text field (read-only, copyable)
        magnet_field = ft.TextField(
            value=magnet_link[:100] + "..." if len(magnet_link) > 100 else magnet_link,
            text_size=10,
            height=35,
            expand=True,
            read_only=True,
            border_color=ft.Colors.GREY_400,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
        )
        
        def copy_magnet(_):
            self.page.set_clipboard(magnet_link)
            self.page.snack_bar = ft.SnackBar(content=ft.Text("Magnet link copied!"))
            self.page.snack_bar.open = True
            self.page.update()
        
        # Info panel (left side) - blue themed
        info_panel = ft.Container(
            content=ft.Column([
                # Torrent Name
                ft.Container(
                    content=ft.Column([
                        ft.Text("Torrent Name", size=11, weight=ft.FontWeight.BOLD, 
                               color=ft.Colors.GREY_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                        ft.Text(self.torrent.name, size=13, weight=ft.FontWeight.BOLD, selectable=True),
                    ], spacing=3),
                    padding=ft.padding.only(bottom=10),
                ),
                
                ft.Divider(height=1),
                
                # Stats Row
                ft.Row([
                    ft.Column([
                        ft.Text("Size", size=10, color=ft.Colors.GREY_500),
                        ft.Text(size_str, size=12, weight=ft.FontWeight.BOLD),
                    ], spacing=2),
                    ft.Column([
                        ft.Text("Seeders", size=10, color=ft.Colors.GREY_500),
                        ft.Text(str(seeders), size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN),
                    ], spacing=2),
                    ft.Column([
                        ft.Text("Peers", size=10, color=ft.Colors.GREY_500),
                        ft.Text(str(peers), size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE),
                    ], spacing=2),
                    ft.Column([
                        ft.Text("Source", size=10, color=ft.Colors.GREY_500),
                        ft.Text(provider, size=12, weight=ft.FontWeight.BOLD),
                    ], spacing=2),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Divider(height=1),
                
                # Info Hash
                ft.Column([
                    ft.Text("Info Hash", size=10, color=ft.Colors.GREY_500),
                    ft.Text(info_hash if info_hash else "Not available", size=11, selectable=True, 
                           font_family="monospace"),
                ], spacing=3),
                
                ft.Divider(height=1),
                
                # Magnet Link
                ft.Column([
                    ft.Row([
                        ft.Text("Magnet Link", size=10, color=ft.Colors.GREY_500),
                        ft.IconButton(
                            icon=ft.Icons.COPY,
                            icon_size=16,
                            tooltip="Copy magnet link",
                            on_click=copy_magnet,
                        ),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    magnet_field,
                ], spacing=3),
                
            ], spacing=8, scroll=ft.ScrollMode.AUTO),
            width=320,
            padding=15,
            bgcolor=ft.Colors.BLUE_GREY_900 if self.page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLUE_GREY_50,
            border_radius=10,
            expand=True,
        )
        
        # Download Location panel (separate, amber themed)
        download_panel = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.FOLDER_OUTLINED, size=18, color=ft.Colors.AMBER),
                    ft.Text("Download to:", size=12, weight=ft.FontWeight.BOLD),
                ], spacing=8),
                ft.Row([
                    self.path_field,
                    ft.IconButton(
                        icon=ft.Icons.FOLDER_OPEN,
                        icon_size=20,
                        tooltip="Browse for folder",
                        on_click=lambda _: self.folder_picker.get_directory_path(
                            dialog_title="Select Download Location",
                            initial_directory=self.custom_download_path if os.path.exists(self.custom_download_path) else None
                        )
                    ),
                ], spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=8),
            padding=12,
            bgcolor=ft.Colors.AMBER_50 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.with_opacity(0.15, ft.Colors.AMBER),
            border_radius=10,
            border=ft.border.all(1, ft.Colors.AMBER_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.AMBER_700),
            width=320,
        )
        
        # Combined left panel (info + download)
        left_panel = ft.Column([
            info_panel,
            download_panel,
        ], spacing=10)
        
        # ============ LEFT PANEL - File Selection ============
        # Select/Deselect all buttons
        def select_all(e):
            for cb in self.file_checkboxes:
                cb.value = True
                cb.update()
            for cb in self.folder_checkboxes.values():
                cb.value = True
                cb.update()
        
        def deselect_all(e):
            for cb in self.file_checkboxes:
                cb.value = False
                cb.update()
            for cb in self.folder_checkboxes.values():
                cb.value = False
                cb.update()
        
        # Build file tree structure
        tree = {}
        for file_info in self.files:
            normalized_path = file_info['name'].replace('\\', '/')
            path_parts = [p for p in normalized_path.split('/') if p]
            
            current_level = tree
            for i, part in enumerate(path_parts):
                if i == len(path_parts) - 1:
                    current_level[part] = {'type': 'file', 'data': file_info}
                else:
                    if part not in current_level:
                        current_level[part] = {'type': 'folder', 'children': {}}
                    current_level = current_level[part]['children']
        
        self.folder_checkboxes = {}

        def build_tree_ui(node, parent_updater=None, current_path=""):
            items = []
            sorted_keys = sorted(node.keys(), key=lambda k: (1 if node[k].get('type') == 'file' else 0, k))
            
            for key in sorted_keys:
                item = node[key]
                is_file = item.get('type') == 'file'
                item_path = f"{current_path}/{key}" if current_path else key
                
                if is_file:
                    file_info = item['data']
                    file_idx = file_info.get('index', 0)
                    
                    # Initialize priority to Normal (2) for selected files, Skip (0) for unselected
                    initial_priority = 2 if file_info['selected'] else 0
                    self.file_priorities[file_idx] = initial_priority
                    
                    # Create dropdown first (but set on_change later)
                    priority_dropdown = ft.Dropdown(
                        value=str(initial_priority),
                        options=[
                            ft.dropdown.Option(key="0", text="Skip"),
                            ft.dropdown.Option(key="1", text="Low"),
                            ft.dropdown.Option(key="2", text="Normal"),
                            ft.dropdown.Option(key="3", text="High"),
                        ],
                        width=110,
                        text_size=11,
                        content_padding=ft.padding.symmetric(horizontal=6, vertical=0),
                        dense=True,
                        border_width=0,
                        border_color=ft.Colors.TRANSPARENT,
                        filled=False,
                        data=file_idx,  # Store file index for reference
                    )
                    
                    # Create checkbox
                    checkbox = ft.Checkbox(
                        value=file_info['selected'],
                        data=file_info,
                    )
                    self.file_checkboxes.append(checkbox)
                    
                    # Now define handlers that can reference both controls
                    def on_file_check(e, f_idx=file_idx, dropdown=priority_dropdown, updater=parent_updater):
                        # When checkbox changes, update priority accordingly
                        if not e.control.value:
                            self.file_priorities[f_idx] = 0  # Skip
                            dropdown.value = "0"
                            dropdown.update()
                        elif self.file_priorities.get(f_idx, 0) == 0:
                            self.file_priorities[f_idx] = 2  # Normal
                            dropdown.value = "2"
                            dropdown.update()
                        if updater:
                            updater()
                    
                    def on_priority_change(e, f_idx=file_idx, cb=checkbox):
                        priority = int(e.control.value)
                        self.file_priorities[f_idx] = priority
                        # Auto-check/uncheck based on priority
                        if priority == 0:  # Skip
                            cb.value = False
                        else:
                            cb.value = True
                        cb.update()
                    
                    # Assign handlers
                    checkbox.on_change = on_file_check
                    priority_dropdown.on_change = on_priority_change
                    
                    row = ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=14, color=ft.Colors.BLUE),
                            checkbox,
                            ft.Text(key, size=11, expand=True, selectable=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(file_info['size'], size=10, width=65, text_align=ft.TextAlign.RIGHT,
                                   color=ft.Colors.GREY_500),
                            priority_dropdown,
                        ], alignment=ft.MainAxisAlignment.START, spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=ft.padding.only(left=5, top=2, bottom=2),
                    )
                    items.append(row)
                else:
                    def create_folder_item(folder_key, folder_item, folder_path, p_updater):
                        folder_checkbox = ft.Checkbox(value=True, tooltip="Select/Deselect All")
                        self.folder_checkboxes[folder_path] = folder_checkbox
                        
                        def update_this_folder():
                            def get_all_descendant_files(node_dict):
                                files = []
                                for k, v in node_dict.items():
                                    if v.get('type') == 'file':
                                        files.append(v['data'])
                                    elif 'children' in v:
                                        files.extend(get_all_descendant_files(v['children']))
                                return files
                                
                            descendant_files = get_all_descendant_files(folder_item['children'])
                            descendant_ids = [id(f) for f in descendant_files]
                            relevant_checkboxes = [cb for cb in self.file_checkboxes if hasattr(cb, 'data') and id(cb.data) in descendant_ids]
                            
                            if relevant_checkboxes:
                                folder_checkbox.value = any(cb.value for cb in relevant_checkboxes)
                                folder_checkbox.update()
                            
                            if p_updater:
                                p_updater()

                        children_ui = build_tree_ui(folder_item['children'], parent_updater=update_this_folder, current_path=folder_path)
                        
                        def on_folder_check(e):
                            is_checked = e.control.value
                            
                            def get_all_files(node_dict):
                                files = []
                                for k, v in node_dict.items():
                                    if v.get('type') == 'file':
                                        files.append(v['data'])
                                    elif 'children' in v:
                                        files.extend(get_all_files(v['children']))
                                return files
                                
                            if 'children' in folder_item:
                                child_files = get_all_files(folder_item['children'])
                                child_file_ids = [id(f) for f in child_files]
                                
                                for cb in self.file_checkboxes:
                                    if hasattr(cb, 'data') and id(cb.data) in child_file_ids:
                                        cb.value = is_checked
                                        cb.update()
                                        
                                for path, cb in self.folder_checkboxes.items():
                                    if path.startswith(folder_path + "/"):
                                        cb.value = is_checked
                                        cb.update()
                            
                            if p_updater:
                                p_updater()
                                    
                        folder_checkbox.on_change = on_folder_check
                        
                        expansion_tile = ft.ExpansionTile(
                            leading=ft.Icon(ft.Icons.FOLDER, color=ft.Colors.AMBER, size=18),
                            title=ft.Row([
                                folder_checkbox,
                                ft.Text(folder_key, weight=ft.FontWeight.BOLD, size=12, expand=True),
                            ], spacing=5),
                            controls=children_ui,
                            initially_expanded=False,
                            controls_padding=ft.padding.only(left=15),
                        )
                        return expansion_tile

                    items.append(create_folder_item(key, item, item_path, parent_updater))
            
            return items

        tree_items = build_tree_ui(tree)
        
        file_list = ft.ListView(
            controls=tree_items,
            expand=True,
            spacing=1,
            padding=ft.padding.only(left=5, right=10, top=5, bottom=5)
        )
        
        # Warning about metadata (only show if no real files)
        warning_container = None
        if not self.files or (len(self.files) == 1 and self.files[0].get('name') == "Magnet Download"):
            warning_container = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.BLUE, size=20),
                    ft.Text("Metadata will be fetched after starting", size=11, color=ft.Colors.BLUE),
                ], spacing=8),
                padding=8,
                bgcolor=ft.Colors.BLUE_50 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.BLUE_GREY_900,
                border_radius=6,
            )
        
        files_panel = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Select Files", size=14, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.TextButton("All", icon=ft.Icons.CHECK_BOX, on_click=select_all),
                    ft.TextButton("None", icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK, on_click=deselect_all),
                ]),
                warning_container if warning_container else ft.Container(),
                ft.Container(
                    content=file_list,
                    expand=True,
                    border=ft.border.all(1, ft.Colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_800),
                    border_radius=8,
                ),
            ], spacing=8),
            expand=True,
            padding=10,
        )
        
        # ============ MAIN LAYOUT - Two Columns ============
        main_content = ft.Row([
            left_panel,
            ft.VerticalDivider(width=1),
            files_panel,
        ], spacing=10, expand=True)
        
        return ft.Container(
            content=main_content,
            width=920,
            height=560,
        )
    
    def _build_actions(self):
        """Build dialog action buttons"""
        return [
            ft.TextButton("Save .torrent", icon=ft.Icons.SAVE, on_click=self._on_save_torrent_click),
            ft.Row([
                ft.TextButton("Cancel", on_click=self._on_cancel),
                ft.ElevatedButton(
                    "Start Download",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=self._on_start_download,
                    bgcolor=ft.Colors.GREEN_700,
                    color=ft.Colors.WHITE
                ),
            ], spacing=10, tight=True)
        ]
    
    def _on_cancel(self, e):
        """Cancel button handler"""
        if self.on_cancel_callback:
            self.on_cancel_callback(e)
        self.open = False
        self.page.update()
    
    def _on_start_download(self, e):
        """Start download with selected files"""
        print(f"DEBUG [_on_start_download]: Method called")
        
        # Get selected files with their priorities
        selected = []
        for cb in self.file_checkboxes:
            if cb.value:
                # Use the data we attached to the checkbox
                if hasattr(cb, 'data'):
                    file_data = cb.data.copy()  # Copy to avoid modifying original
                    file_idx = file_data.get('index', 0)
                    # Add priority from our priority map
                    file_data['priority'] = self.file_priorities.get(file_idx, 2)  # Default Normal
                    selected.append(file_data)
                else:
                    # Fallback for legacy/simulated files without data attribute
                    # This shouldn't happen with the new implementation but good for safety
                    idx = self.file_checkboxes.index(cb)
                    if idx < len(self.files):
                        file_data = self.files[idx].copy()
                        file_data['priority'] = self.file_priorities.get(idx, 2)
                        selected.append(file_data)
        
        print(f"DEBUG [_on_start_download]: Selected files count: {len(selected)}")
        for f in selected:
            print(f"DEBUG [_on_start_download]: File {f.get('index')}: {f.get('name')} - Priority: {f.get('priority')}")
        
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
        
        print(f"DEBUG [_on_start_download]: Calling on_confirm_callback with path: {self.custom_download_path}")
        print(f"DEBUG [_on_start_download]: on_confirm_callback is: {self.on_confirm_callback}")
        
        # Call the confirmation callback with the custom download path
        if self.on_confirm_callback:
            try:
                self.on_confirm_callback(selected, self.custom_download_path)
                print(f"DEBUG [_on_start_download]: Callback executed successfully")
            except Exception as ex:
                print(f"DEBUG [_on_start_download]: Callback error: {ex}")
                import traceback
                traceback.print_exc()
        else:
            print(f"DEBUG [_on_start_download]: No on_confirm_callback set!")

    def _on_save_torrent_click(self, e):
        """Handle save torrent button click - Save directly to Downloads"""
        print("DEBUG: Save torrent clicked")
        
        try:
            # Get configured download path
            try:
                downloads_path = self.download_manager.settings_manager.get('download_path')
            except:
                downloads_path = None
                
            if not downloads_path or not os.path.exists(downloads_path):
                # Fallback to standard Downloads folder
                downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
                
                # Check for "SwiftSeed Download" default
                swiftseed_path = os.path.join(downloads_path, 'SwiftSeed Download')
                if os.path.exists(swiftseed_path):
                    downloads_path = swiftseed_path
            
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
            
            # Remove the download from manager (cleanup temp files) since we are exporting and closing
            if hasattr(self.torrent, 'id') and self.download_manager:
                 self.download_manager.remove_download(self.torrent.id, delete_files=True)
            
            # Close the dialog
            self.open = False
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
