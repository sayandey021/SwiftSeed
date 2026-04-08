import flet as ft
import os
import sys
import webbrowser
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
        # Lazy load providers tab
        self.provider_content_container = ft.Container(
            content=ft.Column([
                ft.ProgressRing(),
                ft.Text("Loading providers...", size=16)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
            alignment=ft.alignment.center,
            padding=50
        )
        self._providers_built = False

        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            on_change=self._on_tab_change,
            tabs=[
                ft.Tab(
                    text="General",
                    icon=ft.Icons.SETTINGS,
                    content=self._build_general_settings()
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
                    content=self.provider_content_container
                ),
                ft.Tab(
                    text="Proxy",
                    icon=ft.Icons.VPN_KEY,
                    content=self._build_proxy_settings()
                ),
                ft.Tab(
                    text="File Associations",
                    icon=ft.Icons.LINK,
                    content=self._build_file_associations_settings()
                ),
            ],
            expand=1,
        )
        
        return ft.Column([
            ft.Text("Settings", size=30, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            self.tabs
        ], expand=True)

    def _on_tab_change(self, e):
        # Index 3 is Providers
        if self.tabs.selected_index == 3 and not self._providers_built:
            self._build_lazy_provider_settings()

    def _build_lazy_provider_settings(self):
        """Build provider settings when tab is selected"""
        try:
            content = self._build_provider_settings()
            self.provider_content_container.content = content
            self.provider_content_container.alignment = None
            self._providers_built = True
            
            # Use update only if attached to page
            if self.page:
                self.provider_content_container.update()
        except Exception as e:
            print(f"Error building provider settings: {e}")
    
    def _check_startup_status(self):
        """Check if app is set to run on startup"""
        if sys.platform != 'win32':
            return False
            
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "SwiftSeed"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, app_name)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"Error checking startup status: {e}")
            return False

    def _toggle_startup(self, e):
        """Toggle run on startup"""
        if sys.platform != 'win32':
            self._show_snack("Startup option only available on Windows")
            e.control.value = False
            e.control.update()
            return

        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "SwiftSeed"
        
        # Get executable path
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            # If running from source, use python executable and script
            exe_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            
            if e.control.value:
                # Add to startup
                # Use quotes for path to handle spaces
                cmd = f'"{exe_path}"' if not exe_path.startswith('"') else exe_path
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
                self._show_snack("✅ Added to startup")
            else:
                # Remove from startup
                try:
                    winreg.DeleteValue(key, app_name)
                    self._show_snack("Removed from startup")
                except FileNotFoundError:
                    pass
            
            winreg.CloseKey(key)
            self.settings_manager.set('run_on_startup', e.control.value)
            
        except Exception as ex:
            print(f"Error toggling startup: {ex}")
            self._show_snack(f"❌ Error: {ex}")
            # Revert switch if failed
            e.control.value = not e.control.value
            e.control.update()

    def _build_general_settings(self):
        """General settings tab"""
        
        # Run on Startup
        startup_switch = ft.Switch(
            label="Run on Startup",
            value=self._check_startup_status(),
            on_change=self._toggle_startup
        )
        
        # Get saved theme settings
        saved_theme = self.settings_manager.get('theme', 'dark')
        saved_base_mode = self.settings_manager.get('base_mode', None)
        
        # Normalize to lowercase
        if saved_base_mode:
            saved_base_mode = saved_base_mode.lower()
        
        # If base_mode is not saved, detect from current page theme_mode
        if not saved_base_mode:
            saved_base_mode = 'dark' if self.page.theme_mode == ft.ThemeMode.DARK else 'light'
            self.settings_manager.set('base_mode', saved_base_mode)
        
        # Use actual page theme_mode for UI display to avoid mismatch
        actual_mode = 'Dark' if self.page.theme_mode == ft.ThemeMode.DARK else 'Light'
        
        # Determine current base mode and color theme
        if saved_theme in ['dark', 'light']:
            current_base_mode = actual_mode  # Use actual mode
            current_color_theme = None
        elif saved_theme in ['blue', 'green', 'purple', 'orange', 'red', 'teal']:
            current_base_mode = actual_mode  # Use actual mode
            current_color_theme = saved_theme.capitalize()
        elif saved_theme == 'glass_dark':
            current_base_mode = 'Dark'
            current_color_theme = 'Glass_Dark'
        elif saved_theme == 'glass_light':
            current_base_mode = 'Light'
            current_color_theme = 'Glass_Light'
        elif saved_theme == 'glass':
            current_base_mode = 'Dark'
            current_color_theme = 'Glass_Dark'
        else:
            current_base_mode = actual_mode  # Use actual mode
            current_color_theme = None
        
        def on_base_mode_change(e):
            mode = e.control.value
            
            if mode == "Dark":
                self.page.theme_mode = ft.ThemeMode.DARK
                self.page.bgcolor = None
                self.page.window.bgcolor = None
                self.page.window.opacity = 1.0
            elif mode == "Light":
                self.page.theme_mode = ft.ThemeMode.LIGHT
                self.page.bgcolor = None
                self.page.window.bgcolor = None
                self.page.window.opacity = 1.0
            
            self.settings_manager.set('base_mode', mode.lower())
            self.page.update()
            self._show_snack(f"Base mode changed to {mode}")
        
        def on_color_theme_change(e):
            color = e.control.value
            
            if not color:
                self.page.theme = None
                base_mode = base_mode_selector.value.lower()
                self.settings_manager.set('theme', base_mode)
                self._show_snack("Using base theme only")
            elif color == "Glass_Dark":
                self.page.theme_mode = ft.ThemeMode.DARK
                self.page.bgcolor = '#1C1C1E'
                self.page.window.bgcolor = ft.Colors.TRANSPARENT
                self.page.window.opacity = 0.95
                self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE, font_family='SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif')
                self.settings_manager.set('theme', 'glass_dark')
                self._show_snack("Glass Dark theme applied! Restart for full effect.")
            elif color == "Glass_Light":
                self.page.theme_mode = ft.ThemeMode.LIGHT
                self.page.bgcolor = '#F5F5F7'
                self.page.window.bgcolor = ft.Colors.TRANSPARENT
                self.page.window.opacity = 0.95
                self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE, font_family='SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif')
                self.settings_manager.set('theme', 'glass_light')
                self._show_snack("Glass Light theme applied! Restart for full effect.")
            else:
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
        
        # Color theme selector
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
                ]),
            ]),
            value=current_color_theme,
            on_change=on_color_theme_change
        )
        
        return ft.Container(
            content=ft.ListView([
                ft.Text("System", size=20, weight=ft.FontWeight.BOLD),
                ft.Container(height=10),
                
                ft.Row([
                    ft.Icon(ft.Icons.POWER_SETTINGS_NEW),
                    startup_switch
                ], alignment=ft.MainAxisAlignment.START),
                ft.Text("Start SwiftSeed automatically when you log in to Windows.", 
                       size=12, color=ft.Colors.GREY_500),
                
                ft.Divider(height=30),
                
                ft.Text("Appearance", size=20, weight=ft.FontWeight.BOLD),
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

    def _build_appearance_settings(self):
        """Appearance settings tab"""
        # Get saved settings
        saved_theme = self.settings_manager.get('theme', 'dark')
        saved_base_mode = self.settings_manager.get('base_mode', None)
        
        # Normalize to lowercase
        if saved_base_mode:
            saved_base_mode = saved_base_mode.lower()

        # If base_mode is not saved, detect from current page theme_mode
        if not saved_base_mode:
            saved_base_mode = 'dark' if self.page.theme_mode == ft.ThemeMode.DARK else 'light'
            # Save it for next time
            self.settings_manager.set('base_mode', saved_base_mode)
        
        # Use actual page theme_mode for UI display to avoid mismatch
        actual_mode = 'Dark' if self.page.theme_mode == ft.ThemeMode.DARK else 'Light'
        
        # Determine current base mode and color theme
        if saved_theme in ['dark', 'light']:
            current_base_mode = actual_mode
            current_color_theme = None
        elif saved_theme in ['blue', 'green', 'purple', 'orange', 'red', 'teal']:
            current_base_mode = actual_mode
            current_color_theme = saved_theme.capitalize()
        elif saved_theme == 'glass_dark':
            current_base_mode = 'Dark'
            current_color_theme = 'Glass_Dark'
        elif saved_theme == 'glass_light':
            current_base_mode = 'Light'
            current_color_theme = 'Glass_Light'
        elif saved_theme == 'glass':
            # Legacy glass theme
            current_base_mode = 'Dark'
            current_color_theme = 'Glass_Dark'
        else:
            current_base_mode = actual_mode
            current_color_theme = None
        
        def on_base_mode_change(e):
            mode = e.control.value
            
            if mode == "Dark":
                self.page.theme_mode = ft.ThemeMode.DARK
                self.page.bgcolor = None
                self.page.window.bgcolor = None
                self.page.window.opacity = 1.0
            elif mode == "Light":
                self.page.theme_mode = ft.ThemeMode.LIGHT
                self.page.bgcolor = None
                self.page.window.bgcolor = None
                self.page.window.opacity = 1.0
            
            self.settings_manager.set('base_mode', mode.lower())
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
            elif color == "Glass_Dark":

                self.page.theme_mode = ft.ThemeMode.DARK

                self.page.bgcolor = '#1C1C1E'

                self.page.window.bgcolor = ft.Colors.TRANSPARENT

                self.page.window.opacity = 0.95

                self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE, font_family='SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif')

                self.settings_manager.set('theme', 'glass_dark')

                self._show_snack("Glass Dark theme applied! Restart for full effect.")

            elif color == "Glass_Light":

                self.page.theme_mode = ft.ThemeMode.LIGHT

                self.page.bgcolor = '#F5F5F7'

                self.page.window.bgcolor = ft.Colors.TRANSPARENT

                self.page.window.opacity = 0.95

                self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE, font_family='SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif')

                self.settings_manager.set('theme', 'glass_light')

                self._show_snack("Glass Light theme applied! Restart for full effect.")

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
                ]),

                
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
        
        # Folder selection for download folder - editable
        def on_download_folder_change(e):
            path = e.control.value.strip()
            if path:
                self.settings_manager.set('download_folder', path)
                self.download_manager.base_path = path
                # Create folder if it doesn't exist
                try:
                    os.makedirs(path, exist_ok=True)
                except:
                    pass
        
        download_folder_field = ft.TextField(
            label="Download Folder",
            value=download_folder,
            expand=True,
            hint_text="Enter path or use browse button",
            on_change=on_download_folder_change,
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
        
        # Folder selection for temp folder - editable
        def on_temp_folder_change(e):
            path = e.control.value.strip()
            if path:
                self.settings_manager.set('temp_folder', path)
                self.download_manager.temp_path = path
                # Create folder if it doesn't exist
                try:
                    os.makedirs(path, exist_ok=True)
                except:
                    pass
        
        temp_folder_field = ft.TextField(
            label="Temporary Files Folder",
            value=temp_folder,
            expand=True,
            hint_text="Enter path or use browse button",
            on_change=on_temp_folder_change,
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
            default_download = os.path.join(os.path.expanduser("~"), "Downloads", "SwiftSeed Download")
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
        """Provider settings tab with search, filters, and category sorting"""
        enabled_providers = self.settings_manager.get_enabled_providers()
        
        # Collect unique languages from providers (exclude Multi as it shows for all)
        all_languages = set()
        for provider in self.providers:
            lang = getattr(provider.info, 'language', 'Multi')
            if lang != 'Multi':  # Don't add Multi to filter options
                all_languages.add(lang)
        language_options = ["All"] + sorted(list(all_languages))
        
        # Category options for filtering
        category_options = ["All", "Movies", "Anime", "Series", "Games", "Other", "Adult"]
        
        # State for filters
        current_search = ""
        current_category = "All"
        current_language = "All"
        
        # Container for provider cards (no scroll, outer container scrolls)
        provider_container = ft.Column(spacing=10)
        
        # Status indicators for each provider
        status_indicators = {}
        
        def check_provider_status(provider_url, status_icon, provider_name):
            """Check if provider is accessible"""
            import threading
            
            def check():
                try:
                    import requests
                    import urllib3
                    urllib3.disable_warnings()
                    
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    response = requests.get(provider_url, headers=headers, timeout=10, verify=False)
                    
                    if response.status_code == 200:
                        status_icon.name = ft.Icons.CHECK_CIRCLE
                        status_icon.color = ft.Colors.GREEN
                        status_icon.tooltip = "Working"
                    else:
                        status_icon.name = ft.Icons.ERROR
                        status_icon.color = ft.Colors.ORANGE
                        status_icon.tooltip = f"Error: {response.status_code}"
                except Exception as e:
                    status_icon.name = ft.Icons.CANCEL
                    status_icon.color = ft.Colors.RED
                    status_icon.tooltip = "Blocked/Timeout"
                
                try:
                    status_icon.update()
                except:
                    pass
            
            thread = threading.Thread(target=check, daemon=True)
            thread.start()
        
        def get_provider_category(provider):
            """Get category text for a provider"""
            if provider.info.specialized_category is not None:
                return provider.info.specialized_category.display_name
            return "All"
        
        def get_category_order(category_text):
            """Get sort order for categories"""
            order = {
                "All": 0,
                "Movies": 1,
                "Anime": 2,
                "Series": 3,
                "TV": 3,
                "Games": 4,
                "Apps": 5,  # Separate Apps category
                "Software": 5,  # Same as Apps
                "Other": 6,
                "Adult": 7,
            }
            return order.get(category_text, 6)
        
        def build_provider_card(provider):
            """Build a single provider card"""
            def on_toggle(e, pid=provider.info.id):
                self.settings_manager.toggle_provider(pid)
                status = "enabled" if e.control.value else "disabled"
                self._show_snack(f"Provider {status}")
            
            # Category badge
            category_text = get_provider_category(provider)
            category_color = {
                "Anime": ft.Colors.PINK,
                "Movies": ft.Colors.BLUE,
                "TV": ft.Colors.PURPLE,
                "Series": ft.Colors.PURPLE,
                "Adult": ft.Colors.RED_900,
                "Games": "#1e3a8a",
                "Apps": ft.Colors.TEAL_700,
                "Software": ft.Colors.TEAL_700,
                "All": ft.Colors.GREEN,
            }.get(category_text, ft.Colors.GREY)
            
            # Language badge
            language_text = getattr(provider.info, 'language', 'Multi')
            language_color = {
                "Multi": ft.Colors.BLUE_GREY_700,
                "English": ft.Colors.INDIGO_700,
                "Portuguese": ft.Colors.GREEN_800,
                "Japanese": ft.Colors.RED_800,
                "Spanish": ft.Colors.ORANGE_800,
                "French": ft.Colors.BLUE_800,
                "Russian": ft.Colors.RED_700,
            }.get(language_text, ft.Colors.BLUE_GREY_700)
            
            # Safety badge
            is_safe = provider.info.safety_status.value == "safe"
            safety_icon = ft.Icons.VERIFIED_USER if is_safe else ft.Icons.WARNING
            safety_color = ft.Colors.GREEN if is_safe else ft.Colors.ORANGE
            safety_tooltip = "Safe to use" if is_safe else f"{provider.info.safety_reason or 'Use with caution'}"
            
            # Status indicator icon
            status_icon = ft.Icon(ft.Icons.HELP_OUTLINE, color=ft.Colors.GREY, size=18, tooltip="Click Check to test")
            status_indicators[provider.info.id] = status_icon
            
            # Check button
            def create_check_handler(url, icon, name):
                return lambda e: check_provider_status(url, icon, name)
            
            check_btn = ft.IconButton(
                icon=ft.Icons.NETWORK_CHECK,
                tooltip="Check if working",
                icon_size=18,
                on_click=create_check_handler(provider.info.url, status_icon, provider.info.name)
            )
            
            return ft.Container(
                content=ft.Row([
                    ft.Switch(
                        value=provider.info.id in enabled_providers,
                        on_change=on_toggle,
                    ),
                    ft.Container(
                        content=ft.Text(f"{provider.info.name}", weight=ft.FontWeight.BOLD, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                        width=130,
                    ),
                    ft.Container(
                        content=ft.Text(category_text, size=10, weight=ft.FontWeight.BOLD),
                        bgcolor=category_color,
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border_radius=5,
                    ),
                    ft.Container(
                        content=ft.Text(language_text, size=10, weight=ft.FontWeight.BOLD),
                        bgcolor=language_color,
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border_radius=5,
                    ),
                    ft.Icon(safety_icon, color=safety_color, size=18, tooltip=safety_tooltip),
                    status_icon,
                    check_btn,
                    ft.Text(provider.info.url, size=10, color=ft.Colors.GREY_500, expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                ], alignment=ft.MainAxisAlignment.START, spacing=8),
                padding=10,
                border=ft.border.all(1, ft.Colors.GREY_800),
                border_radius=8,
            )
        
        def update_provider_list(search_text="", category_filter="All", language_filter="All"):
            """Update the provider list based on filters"""
            provider_container.controls.clear()
            
            # Sort providers by category
            sorted_providers = sorted(self.providers, key=lambda p: (get_category_order(get_provider_category(p)), p.info.name.lower()))
            
            current_category_header = None
            
            for provider in sorted_providers:
                provider_category = get_provider_category(provider)
                provider_language = getattr(provider.info, 'language', 'Multi')
                provider_name = provider.info.name.lower()
                
                # Apply search filter
                if search_text and search_text.lower() not in provider_name:
                    continue
                
                # Apply category filter
                if category_filter != "All":
                    if category_filter == "Series" and provider_category not in ["Series", "TV"]:
                        continue
                    elif category_filter == "Other" and provider_category != "Other":
                        continue
                    elif category_filter not in ["Series", "Other"] and provider_category != category_filter:
                        continue
                
                # Apply language filter (Multi providers always show)
                if language_filter != "All" and provider_language != language_filter and provider_language != "Multi":
                    continue
                
                # Add category header if new category
                # Normalize Software to Apps for display
                display_category = provider_category
                if provider_category == "Software":
                    display_category = "Apps"
                
                if category_filter == "All" and display_category != current_category_header:
                    current_category_header = display_category
                    header_color = {
                        "Anime": ft.Colors.PINK,
                        "Movies": ft.Colors.BLUE,
                        "TV": ft.Colors.PURPLE,
                        "Series": ft.Colors.PURPLE,
                        "Adult": ft.Colors.RED_900,
                        "Games": "#1e3a8a",
                        "All": ft.Colors.GREEN,
                        "Apps": ft.Colors.TEAL_700,  # Distinct teal color for Apps
                        "Other": ft.Colors.GREY,
                    }.get(display_category, ft.Colors.GREY)
                    
                    provider_container.controls.append(
                        ft.Container(
                            content=ft.Text(f"━━━ {display_category.upper()} ━━━", size=14, weight=ft.FontWeight.BOLD, color=header_color),
                            margin=ft.margin.only(top=15, bottom=5),
                        )
                    )
                
                # Add provider card
                provider_container.controls.append(build_provider_card(provider))
            
            # Show message if no results
            if len(provider_container.controls) == 0:
                provider_container.controls.append(
                    ft.Container(
                        content=ft.Text("No providers match your filters", size=14, color=ft.Colors.GREY_500, italic=True),
                        padding=20,
                    )
                )
            
            try:
                provider_container.update()
            except:
                pass
        
        # Search field
        search_field = ft.TextField(
            label="Search providers",
            prefix_icon=ft.Icons.SEARCH,
            hint_text="Type to search...",
            width=250,
            height=45,
            text_size=14,
        )
        
        def on_search_change(e):
            nonlocal current_search
            current_search = e.control.value
            update_provider_list(current_search, current_category, current_language)
        
        search_field.on_change = on_search_change
        
        # Category filter dropdown
        category_dropdown = ft.Dropdown(
            label="Category",
            options=[ft.dropdown.Option(opt) for opt in category_options],
            value="All",
            width=130,
            text_size=14,
        )
        
        def on_category_change(e):
            nonlocal current_category
            current_category = e.control.value
            update_provider_list(current_search, current_category, current_language)
        
        category_dropdown.on_change = on_category_change
        
        # Language filter dropdown
        language_dropdown = ft.Dropdown(
            label="Language",
            options=[ft.dropdown.Option(opt) for opt in language_options],
            value="All",
            width=130,
            text_size=14,
        )
        
        def on_language_change(e):
            nonlocal current_language
            current_language = e.control.value
            update_provider_list(current_search, current_category, current_language)
        
        language_dropdown.on_change = on_language_change
        
        # Initial population
        update_provider_list()
        
        # Custom providers section
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
                
                # Filter controls row
                ft.Row([
                    search_field,
                    category_dropdown,
                    language_dropdown,
                ], spacing=15),
                
                ft.Container(height=10),
                ft.Text(f"Total: {len(self.providers)} providers", size=11, color=ft.Colors.GREY_500),
                ft.Container(height=5),
                
                # Provider list (no nested scroll)
                provider_container,
                
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
            ], expand=True, scroll=ft.ScrollMode.AUTO, spacing=10),
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
    
    def _build_proxy_settings(self):
        """Proxy settings tab for bypassing blocked sites"""
        
        # Get current proxy settings
        proxy_enabled = self.settings_manager.get('proxy_enabled', False)
        proxy_type = self.settings_manager.get('proxy_type', 'HTTP')
        proxy_host = self.settings_manager.get('proxy_host', '')
        proxy_port = self.settings_manager.get('proxy_port', '')
        proxy_username = self.settings_manager.get('proxy_username', '')
        proxy_password = self.settings_manager.get('proxy_password', '')
        
        # Proxy enable switch
        proxy_switch = ft.Switch(
            label="Enable Proxy",
            value=proxy_enabled,
        )
        
        # Proxy type dropdown
        proxy_type_dropdown = ft.Dropdown(
            label="Proxy Type",
            options=[
                ft.dropdown.Option("HTTP"),
                ft.dropdown.Option("SOCKS5"),
                ft.dropdown.Option("SOCKS4"),
            ],
            value=proxy_type,
            width=200,
            disabled=not proxy_enabled,
        )
        
        # Host field
        proxy_host_field = ft.TextField(
            label="Proxy Host",
            value=proxy_host,
            hint_text="e.g., 127.0.0.1 or proxy.example.com",
            width=350,
            disabled=not proxy_enabled,
        )
        
        # Port field
        proxy_port_field = ft.TextField(
            label="Port",
            value=str(proxy_port) if proxy_port else "",
            hint_text="e.g., 8080",
            width=120,
            keyboard_type=ft.KeyboardType.NUMBER,
            disabled=not proxy_enabled,
        )
        
        # Username field (optional)
        proxy_username_field = ft.TextField(
            label="Username (optional)",
            value=proxy_username,
            hint_text="Leave empty if not required",
            width=250,
            disabled=not proxy_enabled,
        )
        
        # Password field (optional)
        proxy_password_field = ft.TextField(
            label="Password (optional)",
            value=proxy_password,
            hint_text="Leave empty if not required",
            width=250,
            password=True,
            can_reveal_password=True,
            disabled=not proxy_enabled,
        )
        
        # Status indicator
        status_text = ft.Text("", size=12)
        
        def on_proxy_toggle(e):
            enabled = e.control.value
            # Enable/disable all fields
            proxy_type_dropdown.disabled = not enabled
            proxy_host_field.disabled = not enabled
            proxy_port_field.disabled = not enabled
            proxy_username_field.disabled = not enabled
            proxy_password_field.disabled = not enabled
            
            self.settings_manager.set('proxy_enabled', enabled)
            self._show_snack(f"Proxy {'enabled' if enabled else 'disabled'}")
            self.page.update()
        
        proxy_switch.on_change = on_proxy_toggle
        
        def save_proxy_settings(e):
            # Validate inputs
            host = proxy_host_field.value.strip()
            port = proxy_port_field.value.strip()
            
            if proxy_switch.value and not host:
                self._show_snack("❌ Proxy host is required when proxy is enabled")
                return
            
            if port:
                try:
                    port_num = int(port)
                    if port_num < 1 or port_num > 65535:
                        raise ValueError()
                except ValueError:
                    self._show_snack("❌ Port must be a valid number between 1-65535")
                    return
            
            # Save settings
            self.settings_manager.set('proxy_enabled', proxy_switch.value)
            self.settings_manager.set('proxy_type', proxy_type_dropdown.value)
            self.settings_manager.set('proxy_host', host)
            self.settings_manager.set('proxy_port', port)
            self.settings_manager.set('proxy_username', proxy_username_field.value)
            self.settings_manager.set('proxy_password', proxy_password_field.value)
            
            self._show_snack("✅ Proxy settings saved! Changes will apply to new requests.")
        
        def test_proxy(e):
            """Test the proxy connection"""
            import threading
            
            host = proxy_host_field.value.strip()
            port = proxy_port_field.value.strip()
            ptype = proxy_type_dropdown.value
            username = proxy_username_field.value
            password = proxy_password_field.value
            
            if not host:
                self._show_snack("❌ Enter proxy host first")
                return
            
            # Check SOCKS dependencies if using SOCKS proxy
            if ptype in ['SOCKS5', 'SOCKS4']:
                try:
                    from urllib3.contrib.socks import SOCKSProxyManager
                except ImportError:
                    status_text.value = "❌ SOCKS support not installed. Run: pip install requests[socks]"
                    status_text.color = ft.Colors.RED
                    self.page.update()
                    return
            
            status_text.value = "🔄 Testing proxy connection..."
            status_text.color = ft.Colors.BLUE
            self.page.update()
            
            def do_test():
                try:
                    import requests
                    
                    # Build proxy URL
                    if username and password:
                        auth = f"{username}:{password}@"
                    else:
                        auth = ""
                    
                    port_str = f":{port}" if port else ""
                    
                    if ptype in ['SOCKS5', 'SOCKS4']:
                        proxy_url = f"socks5://{auth}{host}{port_str}"
                    else:
                        proxy_url = f"http://{auth}{host}{port_str}"
                    
                    proxies = {
                        'http': proxy_url,
                        'https': proxy_url
                    }
                    
                    # Test with a reliable site
                    response = requests.get(
                        'https://www.google.com',
                        proxies=proxies,
                        timeout=10,
                        verify=False
                    )
                    
                    if response.status_code == 200:
                        status_text.value = "✅ Proxy is working! Connection successful."
                        status_text.color = ft.Colors.GREEN
                    else:
                        status_text.value = f"⚠️ Unexpected response: {response.status_code}"
                        status_text.color = ft.Colors.ORANGE
                        
                except requests.exceptions.ProxyError as pe:
                    status_text.value = "❌ Proxy error: Could not connect to proxy server"
                    status_text.color = ft.Colors.RED
                except requests.exceptions.Timeout:
                    status_text.value = "❌ Connection timed out"
                    status_text.color = ft.Colors.RED
                except Exception as ex:
                    error_msg = str(ex)
                    if "SOCKS" in error_msg or "socks" in error_msg:
                        status_text.value = "❌ SOCKS error. Run: pip install requests[socks]"
                    else:
                        status_text.value = f"❌ Error: {error_msg[:50]}"
                    status_text.color = ft.Colors.RED
                
                try:
                    self.page.update()
                except:
                    pass
            
            thread = threading.Thread(target=do_test, daemon=True)
            thread.start()
        
        def clear_proxy_settings(e):
            """Clear all proxy settings"""
            proxy_switch.value = False
            proxy_type_dropdown.value = "HTTP"
            proxy_host_field.value = ""
            proxy_port_field.value = ""
            proxy_username_field.value = ""
            proxy_password_field.value = ""
            
            # Disable fields
            proxy_type_dropdown.disabled = True
            proxy_host_field.disabled = True
            proxy_port_field.disabled = True
            proxy_username_field.disabled = True
            proxy_password_field.disabled = True
            
            # Clear saved settings
            self.settings_manager.set('proxy_enabled', False)
            self.settings_manager.set('proxy_type', 'HTTP')
            self.settings_manager.set('proxy_host', '')
            self.settings_manager.set('proxy_port', '')
            self.settings_manager.set('proxy_username', '')
            self.settings_manager.set('proxy_password', '')
            
            status_text.value = ""
            self._show_snack("Proxy settings cleared")
            self.page.update()
        
        return ft.Container(
            content=ft.ListView([
                ft.Text("Proxy Settings", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Configure a proxy to bypass blocked torrent sites", 
                       size=12, color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                
                ft.Container(height=15),
                
                # Info banner
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.BLUE, size=20),
                        ft.Text(
                            "Use a proxy to access torrent sites that may be blocked in your region.",
                            size=12,
                            color=ft.Colors.BLUE_200,
                            expand=True,
                        ),
                    ], spacing=10),
                    padding=15,
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.BLUE),
                    border_radius=8,
                ),
                
                ft.Container(height=20),
                
                # Enable switch
                ft.Row([
                    ft.Icon(ft.Icons.VPN_LOCK, size=24),
                    proxy_switch,
                ], spacing=10),
                
                ft.Container(height=15),
                ft.Divider(),
                ft.Container(height=15),
                
                # Connection settings
                ft.Text("Connection", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(height=10),
                
                proxy_type_dropdown,
                
                ft.Container(height=10),
                
                ft.Row([
                    proxy_host_field,
                    proxy_port_field,
                ], spacing=15),
                
                ft.Container(height=20),
                
                # Authentication (optional)
                ft.Text("Authentication (Optional)", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("Only fill these if your proxy requires authentication", 
                       size=11, color=ft.Colors.GREY_500, italic=True),
                ft.Container(height=10),
                
                ft.Row([
                    proxy_username_field,
                    proxy_password_field,
                ], spacing=15),
                
                ft.Container(height=25),
                
                # Action buttons
                ft.Row([
                    ft.ElevatedButton(
                        "Save Settings",
                        icon=ft.Icons.SAVE,
                        on_click=save_proxy_settings,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.GREEN_700,
                            color=ft.Colors.WHITE,
                        ),
                    ),
                    ft.ElevatedButton(
                        "Test Connection",
                        icon=ft.Icons.NETWORK_CHECK,
                        on_click=test_proxy,
                    ),
                    ft.OutlinedButton(
                        "Clear All",
                        icon=ft.Icons.CLEAR,
                        on_click=clear_proxy_settings,
                    ),
                ], spacing=15),
                
                ft.Container(height=15),
                status_text,
                
                ft.Container(height=30),
                ft.Divider(),
                ft.Container(height=15),
                
                # Free proxy sources info
                ft.Text("Where to Find Proxies", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(height=10),
                
                ft.Container(
                    content=ft.Column([
                        ft.Text("🌐 Free Proxy Sources:", size=13, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.TextButton("Free Proxy List", on_click=lambda e: webbrowser.open("https://free-proxy-list.net/")),
                            ft.TextButton("ProxyScrape", on_click=lambda e: webbrowser.open("https://proxyscrape.com/free-proxy-list")),
                            ft.TextButton("Geonode", on_click=lambda e: webbrowser.open("https://geonode.com/free-proxy-list")),
                        ]),
                        ft.Container(height=5),
                        ft.Text("🔒 For best results, use SOCKS5 proxies or a VPN service.", size=11, 
                               color=ft.Colors.GREY_500, italic=True),
                        ft.Text("⚠️ Free proxies may be slow or unreliable. Consider a paid VPN for better experience.", size=11, 
                               color=ft.Colors.ORANGE_300, italic=True),
                    ]),
                    padding=15,
                    border=ft.border.all(1, ft.Colors.GREY_700),
                    border_radius=8,
                ),
                
                ft.Container(height=20),
                
                # Common proxies examples
                ft.Text("Example Configurations", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Column([
                        ft.Text("HTTP Proxy:", size=12, weight=ft.FontWeight.BOLD),
                        ft.Text("Type: HTTP | Host: proxy.example.com | Port: 8080", size=11, color=ft.Colors.GREY_400),
                        ft.Container(height=8),
                        ft.Text("SOCKS5 Proxy (e.g., from VPN apps):", size=12, weight=ft.FontWeight.BOLD),
                        ft.Text("Type: SOCKS5 | Host: 127.0.0.1 | Port: 1080", size=11, color=ft.Colors.GREY_400),
                        ft.Container(height=8),
                        ft.Text("Tor Network:", size=12, weight=ft.FontWeight.BOLD),
                        ft.Text("Type: SOCKS5 | Host: 127.0.0.1 | Port: 9050", size=11, color=ft.Colors.GREY_400),
                    ]),
                    padding=15,
                    bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.WHITE),
                    border_radius=8,
                ),
                
            ], expand=True, spacing=10, padding=20),
            expand=True
        )
    
    def _build_file_associations_settings(self):
        """File associations settings tab"""
        from managers.file_association_manager import FileAssociationManager
        
        file_manager = FileAssociationManager()
        
        # Status text controls
        status_text = ft.Text("Checking association status...", size=14)
        torrent_status = ft.Text("", size=13)
        magnet_status = ft.Text("", size=13)
        
        def update_status():
            """Update the status display"""
            if not file_manager.is_running_as_executable():
                status_text.value = "⚠️ File associations can only be set when running as an executable (.exe)"
                status_text.color = ft.Colors.ORANGE
                torrent_status.value = ""
                magnet_status.value = ""
            else:
                is_torrent = file_manager.is_torrent_handler()
                is_magnet = file_manager.is_magnet_handler()
                
                torrent_status.value = "✓ .torrent files: Registered" if is_torrent else "✗ .torrent files: Not registered"
                torrent_status.color = ft.Colors.GREEN if is_torrent else ft.Colors.GREY
                
                magnet_status.value = "✓ magnet: links: Registered" if is_magnet else "✗ magnet: links: Not registered"
                magnet_status.color = ft.Colors.GREEN if is_magnet else ft.Colors.GREY
                
                if is_torrent and is_magnet:
                    status_text.value = "✓ SwiftSeed is set as the default handler"
                    status_text.color = ft.Colors.GREEN
                elif is_torrent or is_magnet:
                    status_text.value = "⚠️ Partially configured"
                    status_text.color = ft.Colors.ORANGE
                else:
                    status_text.value = "SwiftSeed is not set as the default handler"
                    status_text.color = ft.Colors.GREY
            
            # Update the page instead of individual controls
            try:
                self.page.update()
            except:
                pass  # Controls may not be added to page yet
        
        # Initial status check
        update_status()
        
        def register_all(e):
            """Register both .torrent and magnet: handlers"""
            if not file_manager.is_running_as_executable():
                self._show_snack("⚠️ Can only register when running as executable")
                return
            
            success, message = file_manager.register_all()
            if success:
                self._show_snack("✓ Successfully registered all handlers!")
                
                update_status()
            else:
                self._show_snack(f"✗ {message}")
        
        def register_torrent(e):
            """Register only .torrent handler"""
            if not file_manager.is_running_as_executable():
                self._show_snack("⚠️ Can only register when running as executable")
                return
            
            success, message = file_manager.register_torrent_handler()
            self._show_snack(message)
            update_status()
        
        def register_magnet(e):
            """Register only magnet: handler"""
            if not file_manager.is_running_as_executable():
                self._show_snack("⚠️ Can only register when running as executable")
                return
            
            success, message = file_manager.register_magnet_handler()
            self._show_snack(message)
            update_status()
        
        def unregister_torrent(e):
            """Unregister .torrent handler"""
            success, message = file_manager.unregister_torrent_handler()
            self._show_snack(message)
            update_status()
        
        def unregister_magnet(e):
            """Unregister magnet: handler"""
            success, message = file_manager.unregister_magnet_handler()
            self._show_snack(message)
            update_status()
        
        def open_windows_settings(e):
            """Open Windows default apps settings"""
            success, message = file_manager.open_windows_default_apps()
            if not success:
                self._show_snack(message)
        
        # Build the UI
        return ft.Container(
            content=ft.ListView([
                ft.Text("File Associations", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Set SwiftSeed as the default handler for torrent files and magnet links", 
                       size=12, color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                
                ft.Container(height=20),
                
                # Status display
                ft.Container(
                    content=ft.Column([
                        status_text,
                        ft.Container(height=5),
                        torrent_status,
                        magnet_status,
                    ]),
                    padding=15,
                    border=ft.border.all(1, ft.Colors.GREY_700),
                    border_radius=8,
                ),
                
                ft.Container(height=20),
                
                # Register all button (primary action)
                ft.ElevatedButton(
                    "Set as Default for All",
                    icon=ft.Icons.CHECK_CIRCLE,
                    on_click=register_all,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.GREEN_700,
                        color=ft.Colors.WHITE,
                    ),
                    disabled=not file_manager.is_running_as_executable()
                ),
                
                ft.Container(height=10),
                
                ft.Text("Or register individually:", size=14, weight=ft.FontWeight.BOLD),
                ft.Container(height=5),
                
                # Individual registration
                ft.Row([
                    ft.ElevatedButton(
                        ".torrent Files",
                        icon=ft.Icons.INSERT_DRIVE_FILE,
                        on_click=register_torrent,
                        disabled=not file_manager.is_running_as_executable()
                    ),
                    ft.ElevatedButton(
                        "magnet: Links",
                        icon=ft.Icons.LINK,
                        on_click=register_magnet,
                        disabled=not file_manager.is_running_as_executable()
                    ),
                ], spacing=10),
                
                ft.Divider(height=30),
                
                # Unregister section
                ft.Text("Unregister Handlers", size=14, weight=ft.FontWeight.BOLD),
                ft.Text("Remove SwiftSeed as the default handler", 
                       size=11, color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                ft.Container(height=5),
                
                ft.Row([
                    ft.OutlinedButton(
                        "Unregister .torrent",
                        icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                        on_click=unregister_torrent,
                    ),
                    ft.OutlinedButton(
                        "Unregister magnet:",
                        icon=ft.Icons.LINK_OFF,
                        on_click=unregister_magnet,
                    ),
                ], spacing=10),
                
                ft.Divider(height=30),
                
                # Windows settings button
                ft.ElevatedButton(
                    "Open Windows Default Apps Settings",
                    icon=ft.Icons.SETTINGS,
                    on_click=open_windows_settings,
                ),
                
                ft.Container(height=20),
                
                # Help text
                ft.Container(
                    content=ft.Column([
                        ft.Text("ℹ️ How it works:", size=12, weight=ft.FontWeight.BOLD),
                        ft.Text("• After registration, double-clicking .torrent files will open them in SwiftSeed", size=11),
                        ft.Text("• Clicking magnet: links in your browser will open them in SwiftSeed", size=11),
                        ft.Text("• You can always change this in Windows Settings > Apps > Default apps", size=11),
                        ft.Container(height=5),
                        ft.Text("⚠️ Note: This feature only works when SwiftSeed is running as an .exe file", size=11, italic=True, color=ft.Colors.ORANGE),
                    ]),
                    padding=15,
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE),
                    border_radius=8,
                ),
                
            ], expand=True, spacing=10, padding=20),
            expand=True
        )
    

    
    def _show_snack(self, message):
        """Helper to show snackbar"""
        try:
            snack = ft.SnackBar(content=ft.Text(message))
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()
        except Exception as ex:
            print(f"Snackbar error: {ex}")
