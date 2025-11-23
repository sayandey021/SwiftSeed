import flet as ft
import os
from pathlib import Path

class SettingsView(ft.Container):
    def __init__(self, page, settings_manager, download_manager, providers, provider_manager):
        super().__init__()
        self.page = page
        self.settings_manager = settings_manager
        self.download_manager = download_manager
        self.providers = providers
        self.provider_manager = provider_manager
        self.expand = True
        self.padding = 20
        
        self.content = self._build_view()
    
    def _build_view(self):
        # Create tabs for different settings sections
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="Appearance",
                    icon=ft.Icons.PALETTE,
                    content=self._build_appearance_settings()
                ),
                ft.Tab(
                    text="Download Settings",
                    icon=ft.Icons.DOWNLOAD,
                    content=self._build_download_settings()
                ),
                ft.Tab(
                    text="Search Settings",
                    icon=ft.Icons.SEARCH,
                    content=self._build_search_settings()
                ),
                ft.Tab(
                    text="Providers",
                    icon=ft.Icons.CLOUD,
                    content=self._build_provider_settings()
                ),
            ],
            expand=1,
        )
        
        return ft.Column([
            ft.Text("Settings", size=30, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            tabs
        ], expand=True)

    def _build_appearance_settings(self):
        """Appearance settings tab"""
        # Get saved settings
        saved_theme = self.settings_manager.get('theme', 'dark')
        saved_base_mode = self.settings_manager.get('base_mode', None)
        
        # If base_mode is not saved, detect from current page theme_mode
        if not saved_base_mode:
            saved_base_mode = 'dark' if self.page.theme_mode == ft.ThemeMode.DARK else 'light'
            # Save it for next time
            self.settings_manager.set('base_mode', saved_base_mode)
        
        # Determine current base mode and color theme
        if saved_theme in ['dark', 'light']:
            current_base_mode = saved_theme.capitalize()
            current_color_theme = None
        elif saved_theme in ['blue', 'green', 'purple', 'orange', 'red', 'teal']:
            current_base_mode = saved_base_mode.capitalize()
            current_color_theme = saved_theme.capitalize()
        else:
            current_base_mode = saved_base_mode.capitalize()
            current_color_theme = None
        
        def on_base_mode_change(e):
            mode = e.control.value
            if mode == "Dark":
                self.page.theme_mode = ft.ThemeMode.DARK
            else:
                self.page.theme_mode = ft.ThemeMode.LIGHT
            
            self.settings_manager.set('base_mode', mode.lower())
            
            # If a color theme is active, reapply it with new base mode
            color = color_theme_selector.value
            if color:
                color_seed = {
                    "Blue": ft.Colors.BLUE,
                    "Green": ft.Colors.GREEN,
                    "Purple": ft.Colors.PURPLE,
                    "Orange": ft.Colors.ORANGE,
                    "Red": ft.Colors.RED,
                    "Teal": ft.Colors.TEAL
                }[color]
                self.page.theme = ft.Theme(color_scheme_seed=color_seed)
                self.settings_manager.set('theme', color.lower())
            else:
                self.page.theme = None
                self.settings_manager.set('theme', mode.lower())
            
            self.page.update()
            self._show_snack(f"Base mode changed to {mode}")
        
        def on_color_theme_change(e):
            color = e.control.value
            
            if not color:
                # No color theme selected, use base mode only
                self.page.theme = None
                base_mode = base_mode_selector.value.lower()
                self.settings_manager.set('theme', base_mode)
                self._show_snack("Using base theme only")
            else:
                # Apply color theme
                color_seed = {
                    "Blue": ft.Colors.BLUE,
                    "Green": ft.Colors.GREEN,
                    "Purple": ft.Colors.PURPLE,
                    "Orange": ft.Colors.ORANGE,
                    "Red": ft.Colors.RED,
                    "Teal": ft.Colors.TEAL
                }[color]
                self.page.theme = ft.Theme(color_scheme_seed=color_seed)
                self.settings_manager.set('theme', color.lower())
                self._show_snack(f"Color theme: {color}")
            
            self.page.update()
        
        # Base mode selector (Dark/Light)
        base_mode_selector = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="Dark", label="Dark Mode"),
                ft.Radio(value="Light", label="Light Mode"),
            ]),
            value=current_base_mode,
            on_change=on_base_mode_change
        )
        
        # Color theme selector (optional - can be unselected)
        color_theme_selector = ft.RadioGroup(
            content=ft.Column([
                ft.Row([
                    ft.Radio(value="Blue", label="Blue"),
                    ft.Radio(value="Green", label="Green"),
                    ft.Radio(value="Purple", label="Purple"),
                ]),
                ft.Row([
                    ft.Radio(value="Orange", label="Orange"),
                    ft.Radio(value="Red", label="Red"),
                    ft.Radio(value="Teal", label="Teal"),
                ])
            ]),
            value=current_color_theme,
            on_change=on_color_theme_change
        )
        
        return ft.Container(
            content=ft.ListView([
                ft.Text("Theme", size=20, weight=ft.FontWeight.BOLD),
                ft.Container(height=10),
                ft.Text("Base Mode:", size=14, weight=ft.FontWeight.BOLD),
                ft.Container(content=base_mode_selector, padding=10),
                ft.Divider(),
                ft.Text("Color Theme (Optional):", size=14, weight=ft.FontWeight.BOLD),
                ft.Text("Add color accents to the interface", size=11, 
                       color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                ft.Container(content=color_theme_selector, padding=10),
            ], expand=True, spacing=10, padding=20),
            expand=True
        )
    
    def _build_download_settings(self):
        """Download settings tab with speed limits and folder settings"""
        
        # Get current settings
        download_folder = self.settings_manager.get('download_folder', self.download_manager.base_path)
        temp_folder = self.settings_manager.get('temp_folder', self.download_manager.temp_path)
        download_limit = self.settings_manager.get('download_limit_kb', 0)
        upload_limit = self.settings_manager.get('upload_limit_kb', 0)
        download_limit_enabled = self.settings_manager.get('download_limit_enabled', False)
        upload_limit_enabled = self.settings_manager.get('upload_limit_enabled', False)
        
        # Folder selection for download folder
        download_folder_field = ft.TextField(
            label="Download Folder",
            value=download_folder,
            read_only=True,
            expand=True
        )
        
        def pick_download_folder(e):
            def on_result(result: ft.FilePickerResultEvent):
                if result.path:
                    download_folder_field.value = result.path
                    self.settings_manager.set('download_folder', result.path)
                    self.download_manager.base_path = result.path
                    self._show_snack(f"Download folder set to: {result.path}")
                    download_folder_field.update()
            
            picker = ft.FilePicker(on_result=on_result)
            self.page.overlay.append(picker)
            self.page.update()
            picker.get_directory_path(dialog_title="Select Download Folder")
        
        # Folder selection for temp folder
        temp_folder_field = ft.TextField(
            label="Temporary Files Folder",
            value=temp_folder,
            read_only=True,
            expand=True
        )
        
        def pick_temp_folder(e):
            def on_result(result: ft.FilePickerResultEvent):
                if result.path:
                    temp_folder_field.value = result.path
                    self.settings_manager.set('temp_folder', result.path)
                    self.download_manager.temp_path = result.path
                    # Create temp folder if doesn't exist
                    os.makedirs(result.path, exist_ok=True)
                    self._show_snack(f"Temp folder set to: {result.path}")
                    temp_folder_field.update()
            
            picker = ft.FilePicker(on_result=on_result)
            self.page.overlay.append(picker)
            self.page.update()
            picker.get_directory_path(dialog_title="Select Temporary Folder")
        
        # Reset to defaults
        def reset_folders(e):
            default_download = os.path.join(os.path.expanduser("~"), "Downloads", "TorrentSearch")
            default_temp = os.path.join(default_download, "temp")
            
            download_folder_field.value = default_download
            temp_folder_field.value = default_temp
            
            self.settings_manager.set('download_folder', default_download)
            self.settings_manager.set('temp_folder', default_temp)
            
            self.download_manager.base_path = default_download
            self.download_manager.temp_path = default_temp
            
            # Create folders
            os.makedirs(default_download, exist_ok=True)
            os.makedirs(default_temp, exist_ok=True)
            
            self._show_snack("Folders reset to defaults")
            self.page.update()
        
        # Speed limit fields
        download_limit_field = ft.TextField(
            label="Download Limit (KB/s, 0 = unlimited)",
            value=str(download_limit),
            width=250,
            keyboard_type=ft.KeyboardType.NUMBER,
            disabled=not download_limit_enabled
        )
        
        upload_limit_field = ft.TextField(
            label="Upload Limit (KB/s, 0 = unlimited)",
            value=str(upload_limit),
            width=250,
            keyboard_type=ft.KeyboardType.NUMBER,
            disabled=not upload_limit_enabled
        )
        
        # Toggle switches for enabling/disabling limits
        download_limit_switch = ft.Switch(
            label="Enable Download Limit",
            value=download_limit_enabled,
        )
        
        upload_limit_switch = ft.Switch(
            label="Enable Upload Limit",
            value=upload_limit_enabled,
        )
        
        def on_download_limit_switch(e):
            enabled = e.control.value
            download_limit_field.disabled = not enabled
            self.settings_manager.set('download_limit_enabled', enabled)
            
            if enabled:
                # Apply the current limit
                try:
                    dl_limit = int(download_limit_field.value)
                    self.download_manager.set_download_limit(dl_limit * 1024)
                except:
                    pass
            else:
                # Disable limit (set to 0 = unlimited)
                self.download_manager.set_download_limit(0)
            
            download_limit_field.update()
            self._show_snack(f"Download limit {'enabled' if enabled else 'disabled'}")
        
        def on_upload_limit_switch(e):
            enabled = e.control.value
            upload_limit_field.disabled = not enabled
            self.settings_manager.set('upload_limit_enabled', enabled)
            
            if enabled:
                # Apply the current limit
                try:
                    ul_limit = int(upload_limit_field.value)
                    self.download_manager.set_upload_limit(ul_limit * 1024)
                except:
                    pass
            else:
                # Disable limit (set to 0 = unlimited)
                self.download_manager.set_upload_limit(0)
            
            upload_limit_field.update()
            self._show_snack(f"Upload limit {'enabled' if enabled else 'disabled'}")
        
        download_limit_switch.on_change = on_download_limit_switch
        upload_limit_switch.on_change = on_upload_limit_switch
        
        def apply_speed_limits(e):
            try:
                if download_limit_switch.value:
                    dl_limit = int(download_limit_field.value)
                    dl_bytes = dl_limit * 1024
                    self.download_manager.set_download_limit(dl_bytes)
                    self.settings_manager.set('download_limit_kb', dl_limit)
                
                if upload_limit_switch.value:
                    ul_limit = int(upload_limit_field.value)
                    ul_bytes = ul_limit * 1024
                    self.download_manager.set_upload_limit(ul_bytes)
                    self.settings_manager.set('upload_limit_kb', ul_limit)
                
                self._show_snack("Speed limits applied!")
            except ValueError:
                self._show_snack("Invalid value. Please enter numbers only.")
        
        # Advanced Torrent Settings
        max_connections = self.settings_manager.get('max_connections', 200)
        max_active_downloads = self.settings_manager.get('max_active_downloads', 5)
        max_active_seeds = self.settings_manager.get('max_active_seeds', 5)
        
        max_connections_field = ft.TextField(
            label="Max Connections",
            value=str(max_connections),
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
            hint_text="200"
        )
        
        max_active_downloads_field = ft.TextField(
            label="Max Active Downloads",
            value=str(max_active_downloads),
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
            hint_text="5"
        )
        
        max_active_seeds_field = ft.TextField(
            label="Max Active Seeds",
            value=str(max_active_seeds),
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
            hint_text="5"
        )
        
        def apply_advanced_settings(e):
            try:
                connections = int(max_connections_field.value)
                active_dls = int(max_active_downloads_field.value)
                active_seeds = int(max_active_seeds_field.value)
                
                self.settings_manager.set('max_connections', connections)
                self.settings_manager.set('max_active_downloads', active_dls)
                self.settings_manager.set('max_active_seeds', active_seeds)
                
                self._show_snack("Advanced settings saved! Restart app for changes to take effect.")
            except ValueError:
                self._show_snack("Invalid value. Please enter numbers only.")
        
        return ft.Container(
            content=ft.ListView([
                # Folders section
                ft.Text("Download Folders", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Customize where downloads and temporary files are saved", 
                       size=12, color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                ft.Container(height=10),
                
                ft.Row([
                    download_folder_field,
                    ft.IconButton(
                        icon=ft.Icons.FOLDER_OPEN,
                        tooltip="Browse",
                        on_click=pick_download_folder
                    )
                ]),
                
                ft.Row([
                    temp_folder_field,
                    ft.IconButton(
                        icon=ft.Icons.FOLDER_OPEN,
                        tooltip="Browse",
                        on_click=pick_temp_folder
                    )
                ]),
                
                ft.ElevatedButton(
                    "Reset to Defaults",
                    icon=ft.Icons.RESTORE,
                    on_click=reset_folders
                ),
                
                ft.Divider(height=30),
                
                # Speed limits section
                ft.Text("Speed Limits", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Control bandwidth usage for all downloads", 
                       size=12, color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                ft.Container(height=10),
                
                # Download limit controls
                download_limit_switch,
                download_limit_field,
                
                ft.Container(height=10),
                
                # Upload limit controls
                upload_limit_switch,
                upload_limit_field,
                
                ft.Container(height=10),
                
                ft.ElevatedButton(
                    "Apply Speed Limits",
                    icon=ft.Icons.SPEED,
                    on_click=apply_speed_limits
                ),
                
                ft.Container(height=10),
                ft.Text("💡 Tip: Use toggles to quickly enable/disable limits without changing values", 
                       size=11, color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400, 
                       italic=True),
                       
                ft.Divider(height=30),
                
                # Advanced Torrent Settings section
                ft.Text("Advanced Torrent Settings", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Configure connections and active transfers", 
                       size=12, color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                ft.Container(height=10),
                
                ft.Row([
                    max_connections_field,
                    max_active_downloads_field,
                    max_active_seeds_field,
                ], spacing=15),
                
                ft.Container(height=10),
                ft.Text("💡 These settings control how many connections and active torrents are allowed", 
                       size=11, color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400, 
                       italic=True),
                
                ft.ElevatedButton(
                    "Apply Advanced Settings",
                    icon=ft.Icons.SETTINGS,
                    on_click=apply_advanced_settings
                ),
                
            ], expand=True, spacing=10, padding=20),
            expand=True
        )
    
    def _build_search_settings(self):
        """Search settings tab"""
        
        # Max results per provider
        max_results = self.settings_manager.get('max_results_per_provider', 50)
        max_results_field = ft.Slider(
            min=10,
            max=200,
            value=max_results,
            divisions=19,
            label="{value} results",
        )
        max_results_text = ft.Text(f"Max results per provider: {int(max_results)}")
        
        def on_max_results_change(e):
            value = int(e.control.value)
            max_results_text.value = f"Max results per provider: {value}"
            self.settings_manager.set('max_results_per_provider', value)
            max_results_text.update()
        
        max_results_field.on_change = on_max_results_change
        
        # Search timeout
        timeout = self.settings_manager.get('search_timeout_seconds', 30)
        timeout_field = ft.Slider(
            min=10,
            max=120,
            value=timeout,
            divisions=11,
            label="{value}s",
        )
        timeout_text = ft.Text(f"Search timeout: {int(timeout)} seconds")
        
        def on_timeout_change(e):
            value = int(e.control.value)
            timeout_text.value = f"Search timeout: {value} seconds"
            self.settings_manager.set('search_timeout_seconds', value)
            timeout_text.update()
        
        timeout_field.on_change = on_timeout_change
        
        # Sort by preference
        sort_options = ["Seeders (High to Low)", "Size (Large to Small)", "Size (Small to Large)", "Name (A-Z)"]
        current_sort = self.settings_manager.get('default_sort', 'seeders')
        sort_value = {
            'seeders': "Seeders (High to Low)",
            'size_desc': "Size (Large to Small)",
            'size_asc': "Size (Small to Large)",
            'name': "Name (A-Z)"
        }.get(current_sort, "Seeders (High to Low)")
        
        sort_dropdown = ft.Dropdown(
            label="Default Sort Order",
            options=[ft.dropdown.Option(opt) for opt in sort_options],
            value=sort_value,
            width=300
        )
        
        def on_sort_change(e):
            mapping = {
                "Seeders (High to Low)": 'seeders',
                "Size (Large to Small)": 'size_desc',
                "Size (Small to Large)": 'size_asc',
                "Name (A-Z)": 'name'
            }
            self.settings_manager.set('default_sort', mapping[e.control.value])
            self._show_snack(f"Default sort set to: {e.control.value}")
        
        sort_dropdown.on_change = on_sort_change
        
        # Auto-clear history
        auto_clear = self.settings_manager.get('auto_clear_history_days', 0)
        auto_clear_field = ft.Dropdown(
            label="Auto-clear search history",
            options=[
                ft.dropdown.Option("Never", "0"),
                ft.dropdown.Option("After 7 days", "7"),
                ft.dropdown.Option("After 30 days", "30"),
                ft.dropdown.Option("After 90 days", "90"),
            ],
            value=str(auto_clear),
            width=300
        )
        
        def on_auto_clear_change(e):
            self.settings_manager.set('auto_clear_history_days', int(e.control.value))
            self._show_snack("History auto-clear setting updated")
        
        auto_clear_field.on_change = on_auto_clear_change
        
        return ft.Container(
            content=ft.ListView([
                ft.Text("Search Behavior", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Configure how searches are performed", 
                       size=12, color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                ft.Container(height=10),
                
                max_results_text,
                max_results_field,
                
                ft.Container(height=20),
                timeout_text,
                timeout_field,
                
                ft.Container(height=20),
                sort_dropdown,
                
                ft.Container(height=20),
                auto_clear_field,
                
            ], expand=True, spacing=10, padding=20),
            expand=True
        )
    
    def _build_provider_settings(self):
        """Provider settings tab"""
        # Built-in providers
        provider_toggles = ft.Column(spacing=10)
        enabled_providers = self.settings_manager.get_enabled_providers()
        
        for provider in self.providers:
            def on_toggle(e, pid=provider.info.id):
                self.settings_manager.toggle_provider(pid)
                status = "enabled" if e.control.value else "disabled"
                self._show_snack(f"Provider {status}")
            
            # Category badge
            category_text = provider.info.specialized_category.display_name
            category_color = {
                "Anime": ft.Colors.PINK,
                "Movies": ft.Colors.BLUE,
                "TV": ft.Colors.PURPLE,
                "Series": ft.Colors.PURPLE,
                "Porn": ft.Colors.RED_900,
                "All": ft.Colors.GREEN,
            }.get(category_text, ft.Colors.GREY)
            
            # Safety badge
            is_safe = provider.info.safety_status.value == "safe"
            safety_icon = ft.Icons.VERIFIED_USER if is_safe else ft.Icons.WARNING
            safety_color = ft.Colors.GREEN if is_safe else ft.Colors.ORANGE
            safety_tooltip = "Safe to use" if is_safe else f"{provider.info.safety_reason or 'Use with caution'}"
            
            # URL Field and Edit Logic
            url_field = ft.TextField(
                value=provider.info.url,
                text_size=12,
                dense=True,
                border_color=ft.Colors.TRANSPARENT,
                focused_border_color=ft.Colors.BLUE,
                hint_text="Provider URL",
                expand=True,
                read_only=True,
            )
            
            def toggle_edit(e, field=url_field, pid=provider.info.id):
                is_editing = not field.read_only
                
                if is_editing:
                    # Save changes
                    field.read_only = True
                    field.border_color = ft.Colors.TRANSPARENT
                    e.control.icon = ft.Icons.EDIT
                    e.control.tooltip = "Edit URL"
                    self._update_provider_url(pid, field.value)
                else:
                    # Enable editing
                    field.read_only = False
                    field.border_color = ft.Colors.BLUE
                    field.focus()
                    e.control.icon = ft.Icons.CHECK
                    e.control.tooltip = "Save URL"
                
                field.update()
                e.control.update()

            edit_btn = ft.IconButton(
                icon=ft.Icons.EDIT,
                tooltip="Edit URL",
                icon_size=18,
                on_click=toggle_edit
            )

            provider_card = ft.Container(
                content=ft.Row([
                    ft.Switch(
                        value=provider.info.id in enabled_providers,
                        on_change=on_toggle,
                    ),
                    ft.Container(
                        content=ft.Text(f"{provider.info.name}", weight=ft.FontWeight.BOLD, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                        width=120, # Fixed width for alignment
                    ),
                    ft.Container(
                        content=ft.Text(category_text, size=10, weight=ft.FontWeight.BOLD),
                        bgcolor=category_color,
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border_radius=5,
                    ),
                    ft.Icon(safety_icon, color=safety_color, size=18, tooltip=safety_tooltip),
                    url_field,
                    edit_btn
                ], alignment=ft.MainAxisAlignment.START, spacing=10),
                padding=10,
                border=ft.border.all(1, ft.Colors.GREY_800),
                border_radius=8,
            )
            provider_toggles.controls.append(provider_card)
        
        # Custom providers (Torznab)
        custom_providers_list = ft.Column(spacing=10)
        
        def show_add_provider_dialog(e):
            name_field = ft.TextField(label="Provider Name", hint_text="e.g., Jackett - Movies")
            url_field = ft.TextField(label="Base URL", hint_text="http://localhost:9117/api/v2.0/indexers/all/results/torznab")
            api_key_field = ft.TextField(label="API Key (optional)", password=True, can_reveal_password=True)
            
            def save_provider(e):
                name = name_field.value
                url = url_field.value
                api_key = api_key_field.value or ""
                
                if not name or not url:
                    self._show_snack("Name and URL are required")
                    return
                
                if self.provider_manager.add_provider(name, url, api_key):
                    dialog.open = False
                    self.page.update()
                    self._show_snack(f"Added {name}")
                else:
                    self._show_snack("Failed to add provider")
            
            dialog = ft.AlertDialog(
                title=ft.Text("Add Custom Provider"),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Add Jackett, Prowlarr, or any Torznab-compatible indexer", size=12, 
                               color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                        name_field,
                        url_field,
                        api_key_field,
                    ], tight=True, spacing=15),
                    width=500,
                    padding=10
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda e: setattr(dialog, 'open', False) or self.page.update()),
                    ft.ElevatedButton("Save", on_click=save_provider),
                ],
            )
            
            self.page.overlay.append(dialog)
            dialog.open = True
            self.page.update()
        
        return ft.Container(
            content=ft.Column([
                ft.Text("Built-in Providers", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Enable or disable torrent providers", 
                       size=12, color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                ft.Container(height=10),
                provider_toggles,
                
                ft.Divider(height=30),
                
                ft.Row([
                    ft.Text("Custom Providers (Torznab)", size=20, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton(
                        "Add Provider",
                        icon=ft.Icons.ADD,
                        on_click=show_add_provider_dialog
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text("Add Jackett, Prowlarr, or other Torznab-compatible indexers", 
                       size=12, color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                custom_providers_list,
                
            ], expand=True, spacing=10, scroll=ft.ScrollMode.AUTO),
            expand=True,
            padding=20
        )
    
    def _update_provider_url(self, provider_id, new_url):
        """Update a provider's URL when edited"""
        try:
            # Find the provider and update its URL
            for provider in self.providers:
                if provider.info.id == provider_id:
                    provider.info.url = new_url
                    # Save to settings
                    self.settings_manager.set_provider_url(provider_id, new_url)
                    self._show_snack(f"Updated {provider.info.name} URL")
                    break
        except Exception as ex:
            print(f"Error updating provider URL: {ex}")
            self._show_snack("Failed to update provider URL")
    
    def _show_snack(self, message):
        """Helper to show snackbar"""
        try:
            snack = ft.SnackBar(content=ft.Text(message))
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()
        except Exception as ex:
            print(f"Snackbar error: {ex}")
