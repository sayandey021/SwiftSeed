import flet as ft
import threading
from typing import List
import webbrowser
import time
import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

# Import existing backend logic
from models.category import Category
from models.torrent import Torrent
from providers import get_all_providers
from storage.bookmarks import BookmarkManager
from storage.settings import SettingsManager
from storage.history import SearchHistoryManager
from storage.custom_providers import CustomProviderManager
from managers.torrent_manager import TorrentManager
from ui.downloads_view import DownloadsView
from ui.settings_view import SettingsView

class TorrentSearchApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "SwiftSeed"
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.DARK
        
        # Set window icon
        icon_path = resource_path(os.path.join("assets", "icon.ico"))
        self.page.window.icon = icon_path
        
        # Initialize managers
        self.settings_manager = SettingsManager()
        self.bookmark_manager = BookmarkManager()
        self.history_manager = SearchHistoryManager()
        self.provider_manager = CustomProviderManager()
        self.download_manager = TorrentManager(self.settings_manager)
        
        # Load settings and apply theme
        saved_theme = self.settings_manager.get('theme', 'dark')
        saved_base_mode = self.settings_manager.get('base_mode', 'dark')
        
        # Apply base mode (dark/light)
        if saved_theme in ['dark', 'light']:
            self.page.theme_mode = ft.ThemeMode.LIGHT if saved_theme == 'light' else ft.ThemeMode.DARK
            self.page.theme = None
        elif saved_theme in ['blue', 'green', 'purple', 'orange', 'red', 'teal']:
            # Apply color theme with appropriate base mode
            self.page.theme_mode = ft.ThemeMode.LIGHT if saved_base_mode == 'light' else ft.ThemeMode.DARK
            color_seed = {
                'blue': ft.Colors.BLUE,
                'green': ft.Colors.GREEN,
                'purple': ft.Colors.PURPLE,
                'orange': ft.Colors.ORANGE,
                'red': ft.Colors.RED,
                'teal': ft.Colors.TEAL
            }[saved_theme]
            self.page.theme = ft.Theme(color_scheme_seed=color_seed)
        else:
            # Default to dark mode
            self.page.theme_mode = ft.ThemeMode.DARK
            self.page.theme = None
        
        # State
        self.providers = get_all_providers()
        
        # Apply saved provider URLs
        for provider in self.providers:
            saved_url = self.settings_manager.get_provider_url(provider.info.id)
            if saved_url:
                provider.info.url = saved_url
        self.current_results = []
        self.bookmarked_names = self.bookmark_manager.get_bookmarked_names()
        
        # UI Components
        self._setup_ui()
        
    def _setup_ui(self):
        # Navigation Rail (Sidebar)
        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=400,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.SEARCH, 
                    selected_icon=ft.Icons.SEARCH, 
                    label="Search"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.BOOKMARK_BORDER, 
                    selected_icon=ft.Icons.BOOKMARK, 
                    label="Bookmarks"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.HISTORY, 
                    selected_icon=ft.Icons.HISTORY, 
                    label="History"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.DOWNLOAD,
                    selected_icon=ft.Icons.DOWNLOAD_DONE,
                    label="Downloads"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED, 
                    selected_icon=ft.Icons.SETTINGS, 
                    label="Settings"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.INFO_OUTLINE, 
                    selected_icon=ft.Icons.INFO, 
                    label="About"
                ),
            ],
            on_change=self._on_nav_change
        )

        # Navigation Config (Icon, Selected Icon, Label)
        self.nav_configs = [
            (ft.Icons.SEARCH, ft.Icons.SEARCH, "Search"),
            (ft.Icons.BOOKMARK_BORDER, ft.Icons.BOOKMARK, "Bookmarks"),
            (ft.Icons.HISTORY, ft.Icons.HISTORY, "History"),
            (ft.Icons.DOWNLOAD, ft.Icons.DOWNLOAD_DONE, "Downloads"),
            (ft.Icons.SETTINGS_OUTLINED, ft.Icons.SETTINGS, "Settings"),
            (ft.Icons.INFO_OUTLINE, ft.Icons.INFO, "About"),
        ]

        # Custom Mobile Navigation Bar (Container with Row of IconButtons)
        self.mobile_nav_items = []
        for i, (icon, selected_icon, label) in enumerate(self.nav_configs):
            btn = ft.IconButton(
                icon=icon,
                selected_icon=selected_icon,
                icon_size=24,
                on_click=lambda e, idx=i: self._set_nav_index(idx),
                data=i,
                tooltip=label
            )
            self.mobile_nav_items.append(btn)

        self.mobile_nav = ft.Container(
            content=ft.Row(
                controls=self.mobile_nav_items,
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
            ),
            bgcolor="surfaceVariant",
            padding=5,
            visible=False
        )

        # Content Areas
        self.search_view = self._build_search_view()
        self.bookmarks_view = self._build_bookmarks_view()
        self.history_view = self._build_history_view()
        self.downloads_view = DownloadsView(self.page, self.download_manager)
        self.settings_view = SettingsView(
            self.page, 
            self.settings_manager, 
            self.download_manager,
            self.providers,
            self.provider_manager
        )
        self.about_view = self._build_about_view()
        
        # Main Layout Container
        self.body = ft.Container(
            content=self.search_view,
            expand=True,
            padding=20,
        )

        # Initialize layout state
        self.is_mobile = False
        
        # Setup resize handler
        self.page.on_resize = self._on_resize
        
        # Initial layout update
        self._update_layout()

    def _on_resize(self, e):
        self._update_layout()
        
    def _update_layout(self):
        # Define mobile breakpoint
        is_mobile = self.page.width < 800
        
        # Only update if mode changed or controls are empty
        if is_mobile != self.is_mobile or not self.page.controls:
            self.is_mobile = is_mobile
            self.page.controls.clear()
            
            if is_mobile:
                # Mobile Layout: Body + Bottom Nav Bar
                self.rail.visible = False
                self.mobile_nav.visible = True
                self._update_mobile_nav_state()
                
                self.page.add(
                    ft.Column([
                        self.body,
                        self.mobile_nav
                    ], expand=True, spacing=0)
                )
            else:
                # Desktop Layout: Side Rail + Body
                self.rail.visible = True
                self.mobile_nav.visible = False
                
                self.page.add(
                    ft.Row([
                        self.rail,
                        ft.VerticalDivider(width=1),
                        self.body,
                    ], expand=True, spacing=0)
                )
            self.page.update()

    def _set_nav_index(self, index):
        """Manual navigation handler for mobile nav"""
        self.rail.selected_index = index
        self._update_mobile_nav_state()
        
        # Create a mock event to reuse _on_nav_change logic
        class MockEvent:
            class Control:
                selected_index = index
            control = Control()
            
        self._on_nav_change(MockEvent())

    def _update_mobile_nav_state(self):
        """Update selected state of mobile nav buttons"""
        current_index = self.rail.selected_index
        for i, btn in enumerate(self.mobile_nav_items):
            btn.selected = (i == current_index)
            # Highlight color
            btn.icon_color = "primary" if i == current_index else "onSurfaceVariant"

    def _on_nav_change(self, e):
        try:
            index = e.control.selected_index
            print(f"DEBUG: Navigating to index {index}")
            
            # Sync controls
            self.rail.selected_index = index
            self._update_mobile_nav_state()
            
            # Update mobile nav if visible
            if self.mobile_nav.visible:
                self.mobile_nav.update()
            
            if index == 0:
                self.body.content = self.search_view
            elif index == 1:
                self._refresh_bookmarks()
                self.body.content = self.bookmarks_view
            elif index == 2:
                self._refresh_history()
                self.body.content = self.history_view
            elif index == 3:
                self.downloads_view._refresh_list()
                self.body.content = self.downloads_view
            elif index == 4:
                self.body.content = self.settings_view
            elif index == 5:
                self.body.content = self.about_view
            self.body.update()
        except Exception as err:
            print(f"Error in navigation: {err}")
            import traceback
            import traceback
            traceback.print_exc()

    def _build_about_view(self):
        return ft.Column(
            [
                ft.Text("About SwiftSeed", size=30, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Container(height=20),
                ft.Image(
                    src=resource_path(os.path.join("assets", "icon.png")),
                    width=100,
                    height=100,
                    fit=ft.ImageFit.CONTAIN,
                ),
                ft.Container(height=10),
                ft.Text("SwiftSeed", size=40, weight=ft.FontWeight.BOLD, color="primary"),
                ft.Text("Version 1.5", size=20, weight=ft.FontWeight.W_500),
                ft.Container(height=20),
                ft.Text("Developed by Sayan Dey", size=18),
                ft.Container(height=10),
                ft.Text("A fast and lightweight torrent search and download client.", size=16),
                ft.Text("Built with Python, Flet, and Libtorrent.", size=16),
                
                ft.Container(height=30),
                
                # Social Links
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "GitHub", 
                            icon=ft.Icons.CODE, 
                            on_click=lambda e: webbrowser.open("https://github.com/sayandey021")
                        ),
                        ft.ElevatedButton(
                            "LinkedIn", 
                            icon=ft.Icons.LINK, 
                            on_click=lambda e: webbrowser.open("https://www.linkedin.com/in/sayan-dey021")
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20
                ),
                
                ft.Container(height=30),
                ft.Divider(),
                ft.Container(height=10),
                
                # Buy Me a Coffee
                ft.Text(
                    "Building free software takes time and passion.\nIf SwiftSeed has helped you, please consider supporting its development.\nEvery coffee counts! ☕❤️", 
                    size=16, 
                    text_align=ft.TextAlign.CENTER,
                    italic=True
                ),
                ft.Container(height=15),
                ft.ElevatedButton(
                    "Buy Me a Coffee",
                    icon=ft.Icons.COFFEE,
                    style=ft.ButtonStyle(
                        color="white",
                        bgcolor="orange",
                    ),
                    on_click=lambda e: webbrowser.open("https://buymeacoffee.com/sayandey025")
                )
            ],
            expand=True,
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO
        )

    # --- SEARCH VIEW ---
    def _build_search_view(self):
        self.search_field = ft.TextField(
            hint_text="Search for movies, games, software...",
            expand=True,
            on_submit=self._perform_search,
            border_radius=10,
            prefix_icon=ft.Icons.SEARCH,
            text_align=ft.TextAlign.LEFT,
            dense=True,
            content_padding=ft.padding.only(left=10, right=10, top=5, bottom=25),
            height=50,
            suffix=ft.IconButton(
                icon=ft.Icons.CLEAR,
                tooltip="Clear search",
                icon_size=18,
                on_click=lambda e: self._clear_search_field(e)
            )
        )
        
        self.category_dropdown = ft.Dropdown(
            width=150,
            options=[ft.dropdown.Option(c.display_name) for c in Category],
            value="All",
            border_radius=10,
            content_padding=ft.padding.symmetric(horizontal=15, vertical=12),
        )
        
        self.search_btn = ft.ElevatedButton(
            "Search",
            icon=ft.Icons.SEARCH,
            on_click=self._perform_search,
            height=50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
            )
        )
        
        self.clear_results_btn = ft.TextButton(
            "Clear Results",
            icon=ft.Icons.DELETE_OUTLINE,
            on_click=self._clear_results,
            visible=False
        )
        
        self.progress_bar = ft.ProgressBar(visible=False)
        self.results_list = ft.ListView(expand=True, spacing=10, padding=10)
        self.status_text = ft.Text("Ready to search", 
                              color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400)

        return ft.Column(
            [
                ft.Text("SwiftSeed", size=30, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [self.search_field, self.category_dropdown, self.search_btn],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row([
                    self.status_text,
                    self.clear_results_btn
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.progress_bar,
                ft.Divider(),
                self.results_list,
            ],
            expand=True,
        )

    def _clear_search_field(self, e):
        self.search_field.value = ""
        self.search_field.update()

    def _clear_results(self, e):
        self.results_list.controls.clear()
        self.current_results = []
        self.status_text.value = "Ready to search"
        self.clear_results_btn.visible = False
        self.page.update()

    def _perform_search(self, e):
        query = self.search_field.value
        if not query:
            return

        category_name = self.category_dropdown.value
        category = Category.from_string(category_name)
        
        # Add to history
        self.history_manager.add_search(query, category_name)

        self.progress_bar.visible = True
        self.status_text.value = f"Searching for '{query}'..."
        self.search_btn.disabled = True
        self.clear_results_btn.visible = False
        self.results_list.controls.clear()
        self.page.update()

        # Run in thread
        def search_task():
            results = []
            enabled_providers = self.settings_manager.get_enabled_providers()
            
            if not enabled_providers:
                print("No providers enabled!")
            
            # Create a list of providers to search
            providers_to_search = [p for p in self.providers if p.info.id in enabled_providers]
            
            # Use ThreadPoolExecutor for parallel searching
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            def search_provider(provider):
                """Search a single provider and return results"""
                try:
                    print(f"Searching {provider.info.name}...")
                    return provider.search(query, category)
                except Exception as err:
                    print(f"Error searching {provider.info.name}: {err}")
                    return []
            
            # Run all searches in parallel (max 10 concurrent)
            with ThreadPoolExecutor(max_workers=min(10, len(providers_to_search))) as executor:
                # Submit all search tasks
                future_to_provider = {
                    executor.submit(search_provider, provider): provider 
                    for provider in providers_to_search
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_provider):
                    provider = future_to_provider[future]
                    try:
                        provider_results = future.result()
                        if provider_results:
                            results.extend(provider_results)
                            # Update UI with partial results for faster feedback
                            self.status_text.value = f"Found {len(results)} results so far..."
                            
                            # Add new results to UI immediately (progressive loading)
                            # Note: These won't be sorted yet, but user sees data faster
                            for torrent in provider_results:
                                self.results_list.controls.append(self._create_torrent_card(torrent))
                            self.page.update()
                            
                    except Exception as exc:
                        print(f"{provider.info.name} generated an exception: {exc}")
            
            # Final sort and clean update
            results.sort(key=lambda t: t.seeders, reverse=True)
            self.current_results = results
            
            # Clear and show sorted results
            self.results_list.controls.clear()
            self._update_results_ui(results)

        threading.Thread(target=search_task, daemon=True).start()

    def _update_results_ui(self, results):
        self.progress_bar.visible = False
        self.search_btn.disabled = False
        self.status_text.value = f"Found {len(results)} results"
        self.clear_results_btn.visible = True if results else False
        
        if not results:
            self.results_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.SEARCH_OFF, size=50, 
                               color=ft.Colors.GREY_400 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_600),
                        ft.Text("No results found", size=20, 
                               color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                        ft.Text("Check your enabled providers in Settings", size=12, 
                               color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=50
                )
            )
        else:
            for torrent in results:
                self.results_list.controls.append(self._create_torrent_card(torrent))
        
        self.page.update()

    def _detect_language(self, text):
        text = text.lower()
        if "hindi" in text: return "Hindi"
        if "english" in text: return "English"
        if "spanish" in text: return "Spanish"
        if "french" in text: return "French"
        if "german" in text: return "German"
        if "italian" in text: return "Italian"
        if "japanese" in text: return "Japanese"
        if "korean" in text: return "Korean"
        if "chinese" in text: return "Chinese"
        if "russian" in text: return "Russian"
        return None

    def _create_torrent_card(self, torrent: Torrent):
        is_dead = torrent.seeders == 0
        is_healthy = torrent.seeders >= 50
        
        icon_color = ft.Colors.RED if is_dead else (ft.Colors.GREEN if is_healthy else ft.Colors.ORANGE)
        
        is_bookmarked = torrent.name in self.bookmarked_names
        bookmark_icon = ft.Icons.STAR if is_bookmarked else ft.Icons.STAR_BORDER
        bookmark_color = ft.Colors.AMBER if is_bookmarked else (ft.Colors.GREY_400 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_600)

        # Details
        category_name = torrent.category.display_name if (hasattr(torrent, 'category') and torrent.category) else "Unknown"
        is_nsfw = torrent.category.is_nsfw if (hasattr(torrent, 'category') and torrent.category) else False
        
        # Language detection
        language = self._detect_language(torrent.name)
        
        # Category color mapping - diverse colors
        category_colors = {
            "Anime": ft.Colors.PINK_400,
            "Movies": ft.Colors.BLUE_400,
            "TV": ft.Colors.PURPLE_400,
            "Series": ft.Colors.PURPLE_400,
            "Porn": ft.Colors.RED_900,
            "Games": ft.Colors.ORANGE_400,
            "Software": ft.Colors.CYAN_400,
            "Books": ft.Colors.AMBER_700,
            "Music": ft.Colors.GREEN_400,
            "All": ft.Colors.BLUE_GREY_600,
            "Unknown": ft.Colors.GREY,
        }
        
        category_color = category_colors.get(category_name, ft.Colors.BLUE_GREY)
        
        tags = [
            ft.Container(
                content=ft.Text(category_name, size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                bgcolor=category_color,
                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                border_radius=4
            )
        ]
        
        if language:
            tags.append(
                ft.Container(
                    content=ft.Text(language, size=10, color=ft.Colors.WHITE),
                    bgcolor=ft.Colors.INDIGO,
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    border_radius=4
                )
            )
            
        if is_nsfw:
            tags.append(
                ft.Container(
                    content=ft.Text("18+", size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                    bgcolor=ft.Colors.RED,
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    border_radius=4
                )
            )

        card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.DOWNLOAD, color=icon_color),
                        title=ft.Text(torrent.name, weight=ft.FontWeight.BOLD),
                        subtitle=ft.Column([
                            ft.Text(f"{torrent.size} • {torrent.seeders} Seeds • {torrent.peers} Peers • {torrent.provider_name}"),
                            ft.Row(tags, spacing=5)
                        ], spacing=2),
                        trailing=ft.IconButton(
                            icon=bookmark_icon,
                            icon_color=bookmark_color,
                            on_click=lambda e, t=torrent: self._toggle_bookmark(e, t)
                        ),
                    ),
                    ft.Row([
                        ft.ElevatedButton(
                            "Download",
                            icon=ft.Icons.DOWNLOAD,
                            on_click=lambda _, t=torrent: self._start_download(t),
                            bgcolor=ft.Colors.GREEN_700,
                            color=ft.Colors.WHITE
                        ),
                        ft.OutlinedButton(
                            "Magnet", 
                            icon=ft.Icons.LINK, 
                            on_click=lambda _, t=torrent: self._copy_magnet(t)
                        ),
                        ft.OutlinedButton(
                            "Open Page", 
                            icon=ft.Icons.OPEN_IN_NEW, 
                            on_click=lambda _, t=torrent: self._open_url(t)
                        ),
                    ], alignment=ft.MainAxisAlignment.END)
                ]),
                padding=10,
            )
        )
        card.data = torrent
        return card

    def _show_snack(self, message):
        """Helper to show snackbar with correct Flet API"""
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

    def _start_download(self, torrent):
        """Show file selection dialog before starting download"""
        magnet = torrent.get_magnet_uri()
        if not magnet:
            self._show_snack("No magnet link available")
            return
            
        # Add torrent immediately to start fetching metadata
        download = self.download_manager.add_download(torrent)
        
        if not download:
            self._show_snack("Failed to add download")
            return
            
        # Check if it's a duplicate
        if not getattr(download, 'is_newly_added', True):
            self._show_snack("ℹ️ Torrent already exists in downloads")
            download.visible = True
            
            # Switch to downloads tab to show it
            self.rail.selected_index = 3
            class MockEvent:
                def __init__(self, control):
                    self.control = control
            self._on_nav_change(MockEvent(self.rail))
            return
            
        # Hide from list until confirmed
        download.visible = False
        
        def cancel_loading(e=None):
            loading_dlg.open = False
            self.page.update()
            # Remove the download since we cancelled
            self.download_manager.remove_download(download.id, delete_files=True)

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
                    if not loading_dlg.open:
                        return

                    if download.has_metadata:
                        found = True
                        break
                    
                    try:
                        if not download.handle.is_valid():
                            return
                        if download.handle.status().has_metadata:
                            # Try to update files immediately
                            download.update_files()
                            if download.files:  # If files populated, we're good
                                download.has_metadata = True
                                found = True
                                break
                    except:
                        pass
                        
                    time.sleep(2)  # Check every 2 seconds (not every second)
                
                if found:
                    # Pause to prevent auto-start
                    self.download_manager.pause_download(download.id)
                    
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
                        self.download_manager.remove_download(download.id)
                        self._show_snack("Failed to retrieve file list. The torrent metadata may be corrupted.")
                        return

                    loading_dlg.open = False
                    self.page.update()

                    # Prepare files
                    files = []
                    for f in download.files:
                        files.append({
                            'index': f.index,
                            'name': f.path,
                            'size': self.download_manager.format_size(f.size),
                            'selected': True
                        })
                    
                    # Update torrent object info
                    download.size = self.download_manager.format_size(download.total_size)
                    if download.handle.is_valid() and download.handle.status().has_metadata:
                        download.name = download.handle.torrent_file().name()
                    
                    def on_confirm(torrent, selected_files):
                        indices = [f['index'] for f in selected_files]
                        for i in range(len(files)):
                            self.download_manager.set_file_priority(download.id, i, 0)
                        for idx in indices:
                            self.download_manager.set_file_priority(download.id, idx, 2)
                        
                        self.download_manager.resume_download(download.id)
                        download.visible = True
                        
                        self._show_snack("Download started!")
                        
                        # Switch to downloads tab
                        self.rail.selected_index = 3
                        class MockEvent:
                            def __init__(self, control):
                                self.control = control
                        self._on_nav_change(MockEvent(self.rail))

                    from ui.download_dialog import DownloadDialog
                    download_dlg = DownloadDialog(self.page, download, self.download_manager, on_confirm, files=files)
                    
                    def on_cancel(e):
                        # Only remove if it's not visible (meaning it was just added and not confirmed yet)
                        # If it's visible, it means it was already in the list (duplicate add attempt)
                        if not download.visible:
                            self.download_manager.remove_download(download.id, delete_files=True)
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
                        self.download_manager.remove_download(download.id, delete_files=True)
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

    def _copy_magnet(self, torrent):
        magnet = torrent.get_magnet_uri()
        if magnet:
            self.page.set_clipboard(magnet)
            self._show_snack("Magnet link copied!")
        else:
            self._show_snack("No magnet link available")

    def _open_url(self, torrent):
        webbrowser.open(torrent.description_url)
        self._show_snack("Opening in browser...")

    def _toggle_bookmark(self, e, torrent):
        try:
            # Validate torrent object
            if not torrent or not hasattr(torrent, 'name'):
                print("Invalid torrent object")
                return
            
            # Update bookmark state
            if torrent.name in self.bookmarked_names:
                self.bookmark_manager.remove_bookmark(torrent.name)
                self.bookmarked_names.discard(torrent.name)
                new_icon = ft.Icons.STAR_BORDER
                new_color = ft.Colors.GREY
                message = "Bookmark removed"
                print(f"Removed bookmark: {torrent.name}")
            else:
                self.bookmark_manager.add_bookmark(torrent)
                self.bookmarked_names.add(torrent.name)
                new_icon = ft.Icons.STAR
                new_color = ft.Colors.AMBER
                message = "Added to bookmarks"
                print(f"Added bookmark: {torrent.name}")
            
            # Update the icon button directly with error handling
            try:
                e.control.icon = new_icon
                e.control.icon_color = new_color
                print(f"Updated icon to {new_icon}, color to {new_color}")
            except Exception as ex:
                print(f"Failed to update icon: {ex}")
                return
            
            # Force updates with multiple attempts
            try:
                e.control.update()
            except Exception as ex:
                print(f"e.control.update() failed: {ex}")
            
            try:
                self.page.update()
            except Exception as ex:
                print(f"self.page.update() failed: {ex}")
            
            # Show feedback
            self._show_snack(message)
                
        except Exception as ex:
            print(f"Bookmark toggle error: {ex}")
            import traceback
            traceback.print_exc()

    # --- BOOKMARKS VIEW ---
    def _build_bookmarks_view(self):
        self.bookmarks_list = ft.ListView(expand=True, spacing=10, padding=10)
        return ft.Column(
            [
                ft.Text("Bookmarks", size=30, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                self.bookmarks_list
            ],
            expand=True
        )

    def _refresh_bookmarks(self):
        try:
            self.bookmarks_list.controls.clear()
            bookmarks = self.bookmark_manager.get_bookmarks()
            
            if not bookmarks:
                self.bookmarks_list.controls.append(
                    ft.Container(
                        content=ft.Text("No bookmarks yet", size=16, 
                                   color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                        alignment=ft.alignment.center,
                        padding=50
                    )
                )
            else:
                for b in bookmarks:
                    # Safely get values
                    name = b.get('name', 'Unknown')
                    size = b.get('size', '?')
                    seeders = b.get('seeders', 0)
                    peers = b.get('peers', 0)
                    provider = b.get('provider', 'Unknown')
                    
                    # Create a card similar to search results
                    card = ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.BOOKMARK, color=ft.Colors.AMBER),
                                    title=ft.Text(name, weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text(f"{size} • {seeders} Seeds • {peers} Peers • {provider}")
                                ),
                                ft.Row([
                                    ft.ElevatedButton(
                                        "Download",
                                        icon=ft.Icons.DOWNLOAD,
                                        on_click=lambda _, bookmark=b: self._start_bookmark_download(bookmark),
                                        bgcolor=ft.Colors.GREEN_700,
                                        color=ft.Colors.WHITE
                                    ),
                                    ft.OutlinedButton(
                                        "Magnet", 
                                        icon=ft.Icons.LINK, 
                                        on_click=lambda _, bookmark=b: self._copy_bookmark_magnet(bookmark)
                                    ),
                                    ft.OutlinedButton(
                                        "Open Page", 
                                        icon=ft.Icons.OPEN_IN_NEW, 
                                        on_click=lambda _, bookmark=b: self._open_bookmark_url(bookmark)
                                    ),
                                    ft.Container(expand=True), # Spacer replacement
                                    ft.IconButton(
                                        ft.Icons.DELETE,
                                        icon_color=ft.Colors.RED,
                                        tooltip="Delete bookmark",
                                        on_click=lambda e, name=name: self._delete_bookmark(name)
                                    )
                                ], alignment=ft.MainAxisAlignment.START)
                            ]),
                            padding=10
                        )
                    )
                    self.bookmarks_list.controls.append(card)
            self.page.update()
        except Exception as e:
            print(f"Error refreshing bookmarks: {e}")
            import traceback
            traceback.print_exc()

    def _start_bookmark_download(self, bookmark):
        """Start download from a bookmark"""
        try:
            # Create a mock torrent object from bookmark data
            class BookmarkTorrent:
                def __init__(self, bookmark):
                    self.name = bookmark.get('name', 'Unknown')
                    self.size = bookmark.get('size', '0 B')
                    self.seeders = bookmark.get('seeders', 0)
                    self.peers = bookmark.get('peers', 0)
                    self.provider_name = bookmark.get('provider', 'Unknown')
                    self.magnet_uri = bookmark.get('magnet_uri', '')
                    
                    # Extract info hash safely
                    if self.magnet_uri and 'btih:' in self.magnet_uri:
                        try:
                            self.info_hash = self.magnet_uri.split('btih:')[1].split('&')[0]
                        except:
                            self.info_hash = str(bookmark.get('id', 'unknown'))
                    else:
                        self.info_hash = str(bookmark.get('id', 'unknown'))
                
                def get_magnet_uri(self):
                    return self.magnet_uri
            
            torrent = BookmarkTorrent(bookmark)
            self._start_download(torrent)
        except Exception as e:
            print(f"Error starting bookmark download: {e}")
            self._show_snack(f"Error starting download: {e}")
    
    def _copy_bookmark_magnet(self, bookmark):
        """Copy magnet link from bookmark"""
        magnet = bookmark.get('magnet_uri')
        if magnet:
            self.page.set_clipboard(magnet)
            self._show_snack("Magnet link copied!")
        else:
            self._show_snack("No magnet link available")
    
    def _open_bookmark_url(self, bookmark):
        """Open bookmark URL in browser"""
        import webbrowser
        url = bookmark.get('description_url')
        if url:
            webbrowser.open(url)
            self._show_snack("Opening in browser...")
        else:
            self._show_snack("No URL available")


    def _delete_bookmark(self, name):
        try:
            self.bookmark_manager.remove_bookmark(name)
            self.bookmarked_names.discard(name)
            self._refresh_bookmarks()
            
            # Update any matching cards in search results
            for control in self.results_list.controls:
                if hasattr(control, 'data') and hasattr(control.data, 'name') and control.data.name == name:
                    # Find the star icon button in the card and update it
                    # Card -> Container -> Column -> ListTile -> trailing (IconButton)
                    try:
                        container = control.content
                        column = container.content
                        list_tile = column.controls[0]
                        icon_button = list_tile.trailing
                        icon_button.icon = ft.Icons.STAR_BORDER
                        icon_button.icon_color = ft.Colors.GREY_400 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_600
                        icon_button.update()
                    except Exception as ex:
                        print(f"Failed to update search result icon: {ex}")
            
            try:
                self.results_list.update()
            except:
                pass
            
            try:
                self._show_snack("Bookmark deleted")
            except:
                pass
        except Exception as ex:
            print(f"Delete bookmark error: {ex}")

    # --- HISTORY VIEW ---
    def _build_history_view(self):
        self.history_list = ft.ListView(expand=True, spacing=5, padding=10)
        return ft.Column(
            [
                ft.Row([
                    ft.Text("Search History", size=30, weight=ft.FontWeight.BOLD),
                    ft.IconButton(ft.Icons.DELETE_SWEEP, on_click=self._clear_history, tooltip="Clear All")
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                self.history_list
            ],
            expand=True
        )

    def _refresh_history(self):
        self.history_list.controls.clear()
        history = self.history_manager.get_recent_searches(50)
        
        if not history:
            self.history_list.controls.append(
                ft.Container(
                    content=ft.Text("No search history", size=16, 
                                   color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                    alignment=ft.alignment.center,
                    padding=50
                )
            )
        else:
            for h in history:
                row = ft.Row([
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.HISTORY),
                        title=ft.Text(h['query']),
                        subtitle=ft.Text(f"{h['category']} • {h['last_used']}"),
                        on_click=lambda e, q=h['query']: self._restore_search(q),
                        expand=True
                    ),
                    ft.IconButton(
                        ft.Icons.CLOSE,
                        icon_color=ft.Colors.GREY_400 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_600,
                        tooltip="Remove",
                        on_click=lambda e, q=h['query']: self._delete_history_item(q)
                    )
                ])
                self.history_list.controls.append(row)
        self.page.update()

    def _delete_history_item(self, query):
        self.history_manager.delete_search(query)
        self._refresh_history()
        self._show_snack("History item removed")

    def _restore_search(self, query):
        self.search_field.value = query
        self.rail.selected_index = 0
        # Create a simple mock event object
        class MockEvent:
            def __init__(self, control):
                self.control = control
        self._on_nav_change(MockEvent(self.rail))
        self._perform_search(None)

    def _clear_history(self, e):
        self.history_manager.clear_all()
        self._refresh_history()
        self._show_snack("History cleared")

    # --- SETTINGS VIEW ---
    def _build_settings_view(self):
        # Theme Switcher
        def on_theme_change(e):
            val = e.control.value
            if val == "Dark":
                self.page.theme_mode = ft.ThemeMode.DARK
                self.page.theme = None
            elif val == "Light":
                self.page.theme_mode = ft.ThemeMode.LIGHT
                self.page.theme = None
            else:
                # Color themes
                self.page.theme_mode = ft.ThemeMode.DARK
                if val == "Blue":
                    self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE)
                elif val == "Green":
                    self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.GREEN)
                elif val == "Purple":
                    self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.PURPLE)
                elif val == "Orange":
                    self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.ORANGE)
            
            self.settings_manager.set('theme', val.lower())
            self.page.update()
            self._show_snack(f"Theme changed to {val}")

        current_theme_val = "Dark"
        saved = self.settings_manager.get('theme', 'dark').capitalize()
        if saved in ["Dark", "Light", "Blue", "Green", "Purple", "Orange"]:
            current_theme_val = saved

        theme_selector = ft.RadioGroup(
            content=ft.Column([
                ft.Row([
                    ft.Radio(value="Dark", label="Dark Mode"),
                    ft.Radio(value="Light", label="Light Mode"),
                ]),
                ft.Text("Color Themes (Dark Base):", size=12, 
                       color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                ft.Row([
                    ft.Radio(value="Blue", label="Blue"),
                    ft.Radio(value="Green", label="Green"),
                    ft.Radio(value="Purple", label="Purple"),
                    ft.Radio(value="Orange", label="Orange"),
                ])
            ]),
            value=current_theme_val,
            on_change=on_theme_change
        )

        # Built-in Provider Toggles with Category & Safety
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
            
            provider_card = ft.Container(
                content=ft.Row([
                    ft.Switch(
                        label=f"{provider.info.name}",
                        value=provider.info.id in enabled_providers,
                        on_change=on_toggle,
                    ),
                    ft.Container(
                        content=ft.Text(category_text, size=10, weight=ft.FontWeight.BOLD),
                        bgcolor=category_color,
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border_radius=5,
                    ),
                    ft.Icon(safety_icon, color=safety_color, size=18, tooltip=safety_tooltip),
                    ft.Text(f"{provider.info.url}", 
                           color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400, 
                           size=10, expand=True),
                ], alignment=ft.MainAxisAlignment.START, spacing=10),
                padding=10,
                border=ft.border.all(1, ft.Colors.GREY_800),
                border_radius=8,
            )
            provider_toggles.controls.append(provider_card)

        # Custom Providers Section
        self.custom_providers_list = ft.Column(spacing=10)
        
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
                    self._refresh_custom_providers()
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
        
        add_provider_btn = ft.ElevatedButton(
            "Add Custom Provider",
            icon=ft.Icons.ADD,
            on_click=show_add_provider_dialog
        )
        
        self._refresh_custom_providers()

        return ft.Column(
            [
                ft.Text("Settings", size=30, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                
                # Appearance
                ft.Text("Appearance", size=20, weight=ft.FontWeight.BOLD),
                ft.Container(content=theme_selector, padding=10),
                ft.Divider(),
                
                # Built-in Providers
                ft.Text("Built-in Providers", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Each provider shows: Category (content type), Safety status (safe / caution), and URL", 
                       color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400, size=11),
                ft.Container(content=provider_toggles, padding=10),
                ft.Divider(),
                
                # Custom Providers
                ft.Row([
                    ft.Text("Custom Providers (Torznab)", size=20, weight=ft.FontWeight.BOLD),
                    add_provider_btn
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text("Add Jackett, Prowlarr, or other Torznab-compatible indexers", 
                       color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400, size=12),
                ft.Container(content=self.custom_providers_list, padding=10),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO
        )
    
    def _refresh_custom_providers(self):
        """Refresh the custom providers list."""
        self.custom_providers_list.controls.clear()
        providers = self.provider_manager.get_providers()
        
        if not providers:
            self.custom_providers_list.controls.append(
                ft.Text("No custom providers yet. Click 'Add Custom Provider' to get started!", 
                       color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400, size=12)
            )
        else:
            for p in providers:
                def delete_provider(e, pid=p['id'], pname=p['name']):
                    self.provider_manager.delete_provider(pid)
                    self._show_snack(f"Deleted {pname}")
                    self._refresh_custom_providers()
                
                def toggle_provider(e, pid=p['id']):
                    self.provider_manager.toggle_provider(pid)
                    self._refresh_custom_providers()
                
                url_text = p['base_url']
                if len(url_text) > 60:
                    url_text = url_text[:60] + "..."
                
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.CLOUD, size=20),
                                ft.Text(p['name'], weight=ft.FontWeight.BOLD, expand=True),
                                ft.Switch(
                                    value=bool(p['enabled']),
                                    on_change=toggle_provider,
                                    label="Enabled"
                                )
                            ]),
                            ft.Text(f"{url_text}", size=11, 
                                   color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                            ft.Row([
                                ft.Text(f"Type: {p['provider_type']}", size=10, color=ft.Colors.BLUE_GREY),
                                ft.IconButton(
                                    ft.Icons.DELETE,
                                    icon_color=ft.Colors.RED,
                                    tooltip="Delete provider",
                                    on_click=delete_provider
                                )
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        ], spacing=5),
                        padding=15
                    )
                )
                self.custom_providers_list.controls.append(card)
        
        self.page.update()

def main(page: ft.Page):
    app = TorrentSearchApp(page)

if __name__ == "__main__":
    ft.app(target=main)
