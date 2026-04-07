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

def debug_log(msg):
    pass

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
    def __init__(self, page: ft.Page, torrent_file=None, magnet_link=None):
        self.page = page
        self.page.title = "SwiftSeed"
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.DARK
        
        # Set window icon
        icon_path = resource_path(os.path.join("assets", "icon.ico"))
        self.page.window.icon = icon_path
        
        # Explicitly set window title bar (ensures taskbar shows correct name)
        self.page.window.title_bar_hidden = False
        self.page.window.title_bar_buttons_hidden = False

        # Window configuration for glass theme

        self.page.window.width = 1200

        self.page.window.height = 800

        self.page.window.min_width = 800

        self.page.window.min_height = 600
        
        # System Tray Setup
        self.page.window.prevent_close = True
        self.page.on_window_event = self._on_window_event  # Page-level event
        
        # Modern Flet (0.21.0+) specific close handler
        try:
            self.page.window.on_close = lambda _: self._show_exit_dialog()
            print("DEBUG: Successfully set page.window.on_close")
        except Exception as ex:
            print(f"DEBUG: Could not set page.window.on_close: {ex}")
        
        self.page.window.on_event = self._on_window_event # Generic window events
        self.tray_icon = None  # Will be initialized after UI setup
        
        # Force window icon using Win32 API (Aggressive Mode)
        if sys.platform == 'win32':
            def force_icon_aggressive():
                try:
                    import win32gui
                    import win32con
                    import time
                    
                    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon_debug.log")
                    
                    def log(msg):
                        try:
                            with open(log_file, "a") as f:
                                f.write(f"{time.strftime('%H:%M:%S')} - {msg}\n")
                        except: pass

                    log("Starting aggressive icon enforcement...")
                    
                    # Get absolute path to icon
                    if getattr(sys, 'frozen', False):
                        base_path = sys._MEIPASS
                    else:
                        base_path = os.path.dirname(os.path.abspath(__file__))
                    
                    icon_path = os.path.join(base_path, "assets", "icon.ico")
                    
                    if not os.path.exists(icon_path):
                        log(f"! Icon not found at {icon_path}")
                        return

                    # Load icons once
                    h_icon_small = win32gui.LoadImage(
                        0, icon_path, win32con.IMAGE_ICON,
                        16, 16, win32con.LR_LOADFROMFILE
                    )
                    h_icon_large = win32gui.LoadImage(
                        0, icon_path, win32con.IMAGE_ICON,
                        32, 32, win32con.LR_LOADFROMFILE
                    )

                    log("Icons loaded successfully")
                    
                    # Keep trying to find and patch the window
                    while True:
                        def callback(hwnd, windows):
                            if win32gui.IsWindowVisible(hwnd):
                                title = win32gui.GetWindowText(hwnd)
                                if "SwiftSeed" in title:
                                    windows.append(hwnd)
                            return True
                        
                        windows = []
                        win32gui.EnumWindows(callback, windows)
                        
                        if windows:
                            log(f"Found {len(windows)} windows")
                        
                        for hwnd in windows:
                            try:
                                # Set per-window icon
                                win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, h_icon_small)
                                win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_BIG, h_icon_large)
                                
                                # Set class icon
                                try:
                                    win32gui.SetClassLong(hwnd, -14, h_icon_large) # GCL_HICON
                                    win32gui.SetClassLong(hwnd, -34, h_icon_small) # GCL_HICONSM
                                except:
                                    pass
                                
                                # Force refresh
                                win32gui.InvalidateRect(hwnd, None, True)
                            except Exception as e:
                                log(f"Error setting icon for hwnd {hwnd}: {e}")
                        
                        # Check every 1 second
                        time.sleep(1)
                        
                except Exception as e:
                    try:
                        with open("icon_error.log", "w") as f:
                            f.write(str(e))
                    except: pass
            
            # Run in background thread
            import threading
            threading.Thread(target=force_icon_aggressive, daemon=True).start()

        # Initialize managers
        self.settings_manager = SettingsManager()

        # Ensure 'academictorrents' is enabled if it's missing (Fix for existing users)
        # This is critical because we just re-added/fixed it
        current_enabled = self.settings_manager.get_enabled_providers()
        if 'academictorrents' not in current_enabled:
            current_enabled.append('academictorrents')
            self.settings_manager.set_enabled_providers(current_enabled)

        self.bookmark_manager = BookmarkManager()
        self.history_manager = SearchHistoryManager()
        self.provider_manager = CustomProviderManager()
        self.download_manager = TorrentManager(self.settings_manager)
        
        # Pre-cache Academic Torrents database in background for faster first search
        def precache_academic():
            try:
                from providers.additional import AcademicTorrentsProvider
                from models.category import Category
                provider = AcademicTorrentsProvider()
                # Trigger a dummy search to cache the database
                provider.search("", Category.ALL)
                print("Academic Torrents database pre-cached successfully")
            except Exception as e:
                print(f"Academic Torrents pre-cache failed: {e}")
        
        threading.Thread(target=precache_academic, daemon=True).start()
        
        # Store pending torrent file if provided
        self.pending_torrent_file = torrent_file
        self.pending_magnet_link = magnet_link
        
        # Load settings and apply theme
        saved_theme = self.settings_manager.get('theme', 'dark')
        saved_base_mode = self.settings_manager.get('base_mode', 'dark')
        # Normalize to lowercase for consistent comparison
        saved_base_mode_lower = saved_base_mode.lower() if saved_base_mode else 'dark'
        
        # Apply base mode
        if saved_base_mode_lower == 'glass':
            self.page.theme_mode = ft.ThemeMode.DARK
            self.page.bgcolor = '#15141A'
            self.page.window.bgcolor = ft.Colors.TRANSPARENT
            opacity = self.settings_manager.get('window_opacity', 0.95)
            self.page.window.opacity = max(0.9, min(1.0, opacity)) # Clamp between 0.9 and 1.0
            self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE, font_family='SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif')
        elif saved_base_mode_lower == 'light':
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.page.window.opacity = 1.0
            self.page.theme = None
        else: # Dark or default
            self.page.theme_mode = ft.ThemeMode.DARK
            self.page.window.opacity = 1.0
            self.page.theme = None
            
        # Apply color theme if selected (overrides default theme seed)
        if saved_theme and saved_theme not in ['dark', 'light', 'glass', 'glass_dark', 'glass_light']:
             color_seed = {
                'blue': ft.Colors.BLUE,
                'green': ft.Colors.GREEN,
                'purple': ft.Colors.PURPLE,
                'orange': ft.Colors.ORANGE,
                'red': ft.Colors.RED,
                'teal': ft.Colors.TEAL
            }.get(saved_theme)
             if color_seed:
                 self.page.theme = ft.Theme(color_scheme_seed=color_seed)
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
        elif saved_theme == 'glass_dark':

            self.page.theme_mode = ft.ThemeMode.DARK

            self.page.bgcolor = '#15141A'

            self.page.window.bgcolor = ft.Colors.TRANSPARENT

            self.page.window.opacity = self.settings_manager.get('window_opacity', 0.92)

            self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE, font_family='SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif')

        elif saved_theme == 'glass_light':

            self.page.theme_mode = ft.ThemeMode.LIGHT

            self.page.bgcolor = '#F5F5F7'

            self.page.window.bgcolor = ft.Colors.TRANSPARENT

            self.page.window.opacity = self.settings_manager.get('window_opacity', 0.92)

            self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE, font_family='SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif')

        else:
            # Default to dark mode
            self.page.theme_mode = ft.ThemeMode.DARK
            self.page.theme = None
            
        # Fix scrollbar behavior (prevent auto-expand)
        scrollbar_theme = ft.ScrollbarTheme(
            thickness=10,
            radius=5,
            thumb_visibility=True,
            track_visibility=False,
            interactive=True,
            cross_axis_margin=2,
            track_color=ft.Colors.TRANSPARENT,
        )
        
        if self.page.theme:
            self.page.theme.scrollbar_theme = scrollbar_theme
        else:
            self.page.theme = ft.Theme(scrollbar_theme=scrollbar_theme)
            # Ensure we have a color scheme seed if we created a new theme
            if not self.page.theme.color_scheme_seed:
                self.page.theme.color_scheme_seed = ft.Colors.BLUE
        
        # State
        debug_log("Calling get_all_providers()")
        self.providers = get_all_providers()
        debug_log(f"get_all_providers() returned {len(self.providers)} providers")
        
        # Apply saved provider URLs
        for provider in self.providers:
            # print(f"DEBUG: Processing provider {provider.info.id}")
            saved_url = self.settings_manager.get_provider_url(provider.info.id)
            if saved_url:
                provider.info.url = saved_url
        debug_log("Finished processing provider URLs")
        self.current_results = []
        self.bookmarked_names = self.bookmark_manager.get_bookmarked_names()
        self.search_in_progress = False  # Flag to prevent view switching during search
        self.view_switch_locked = False  # Flag to prevent rapid view switching (2 sec cooldown)
        self.ui_lock = threading.Lock()  # Lock for safe UI updates
        self.refreshed_tabs = set() # Track which tabs are updated to current style for lazy loading
        self.view_refresh_version = 0  # Version counter to cancel stale background refreshes
        self.displayed_count = {}  # Track how many results are currently displayed per provider {'All': 50, 'ProviderX': 10, ...}
        
        # Sort Options State
        self.current_sort = self.settings_manager.get('default_sort', 'seeders')
        self.sort_options = [
            ("Seeds", "seeders"),
            ("Peers", "peers"),
            ("Size", "size"),
            ("Name", "name"),
        ]
        
        # Filter State
        self.active_provider_filters = set()   # Empty = show all providers
        self.active_category_filters = set()   # Empty = show all categories
        self.filter_min_seeds = 0
        self.filter_min_peers = 0
        self.filter_min_size = 0       # In bytes
        self.filter_max_size = 0       # 0 = no limit
        self.filters_visible = False
        self.category_filter_options = [
            ("🎬 Movies", "Movies"),
            ("📺 TV / Series", "TV"),
            ("🎌 Anime", "Anime"),
            ("🎮 Games", "Games"),
            ("📚 Books", "Books"),
            ("🎵 Music", "Music"),
            ("💻 Apps", "Apps"),
            ("🔞 Adult", "Adult"),
            ("📦 Other", "Other"),
        ]
        
        # Track window visibility and focus timing for professional tray behavior
        self.is_window_visible = True
        self.is_window_focused = True
        self.last_focus_time = time.time()
        self.last_blur_time = 0
        self.exit_dialog = None
        self.exit_checkbox = None
        
        # UI Components
        debug_log("Starting _setup_ui")
        try:
            self._setup_ui()
            debug_log("Finished _setup_ui")
        except Exception as e:
            debug_log(f"Error in _setup_ui: {e}")
            import traceback
            traceback.print_exc()
        
        # Start system tray in background thread
        threading.Thread(target=self._create_tray_icon, daemon=True).start()
        
        # Eagerly cache the window handle so tray toggle always has it
        def _cache_hwnd():
            if sys.platform != 'win32':
                return
            time.sleep(2)  # Wait for window to fully appear
            self._find_hwnd_ctypes()
        threading.Thread(target=_cache_hwnd, daemon=True).start()
        
        # Show first-run file association prompt if needed
        self._check_and_show_file_association_prompt()
        
        # If a torrent file was provided via command line, open it
        if self.pending_torrent_file:
            print(f"Opening torrent file from command line: {self.pending_torrent_file}")
            # Use a small delay to ensure UI is fully loaded
            def open_file():
                time.sleep(0.5)  # Small delay to ensure page is ready
                self._open_torrent_file(self.pending_torrent_file)
            threading.Thread(target=open_file, daemon=True).start()
        
        # If a magnet link was provided via command line, open it
        elif self.pending_magnet_link:
            print(f"Opening magnet link from command line: {self.pending_magnet_link}")
            # Use a small delay to ensure UI is fully loaded
            def open_magnet():
                time.sleep(0.5)  # Small delay to ensure page is ready
                self._open_magnet_link(self.pending_magnet_link)
            threading.Thread(target=open_magnet, daemon=True).start()
        
        
    
    def _toggle_window_taskbar_like(self, icon=None, item=None):
        """Toggle window visibility from tray icon click.
        Moves window offscreen instead of hiding it, so Flutter never
        suspends its render surface — no white flash on restore.
        """
        # Debounce: ignore clicks within 600ms of the last toggle
        now = time.time()
        last_toggle = getattr(self, '_last_toggle_time', 0)
        if now - last_toggle < 0.6:
            return
        self._last_toggle_time = now
        
        try:
            my_hwnd = getattr(self, '_cached_hwnd', None)
            
            if sys.platform == 'win32' and not my_hwnd:
                my_hwnd = self._find_hwnd_ctypes()
            
            if not self.is_window_visible:
                # --- RESTORE: move window back from offscreen ---
                self.is_window_visible = True
                self.is_window_focused = True
                
                if sys.platform == 'win32' and my_hwnd:
                    self._win32_restore_from_offscreen(my_hwnd)
                
                # Sync Flet taskbar state
                def _sync_restore():
                    try:
                        self.page.window.skip_task_bar = False
                        self.page.window.minimized = False
                        self.page.update()
                    except:
                        pass
                
                try:
                    self.page.run_thread(_sync_restore)
                except Exception:
                    threading.Thread(target=_sync_restore, daemon=True).start()
                
                self.last_focus_time = time.time()
                
            else:
                # --- HIDE: move window offscreen ---
                self.is_window_visible = False
                self.is_window_focused = False
                
                if sys.platform == 'win32' and my_hwnd:
                    self._win32_move_offscreen(my_hwnd)
                
                # Sync Flet taskbar state
                def _sync_hide():
                    try:
                        self.page.window.skip_task_bar = True
                        self.page.update()
                    except:
                        pass
                
                try:
                    self.page.run_thread(_sync_hide)
                except Exception:
                    threading.Thread(target=_sync_hide, daemon=True).start()
                
        except Exception as e:
            print(f"ERROR: Toggle failed: {e}")
    
    def _find_hwnd_ctypes(self):
        """Find our window handle using ctypes (no pywin32 dependency)"""
        try:
            import ctypes
            from ctypes import wintypes
            
            user32 = ctypes.windll.user32
            EnumWindows = user32.EnumWindows
            GetWindowTextW = user32.GetWindowTextW
            GetWindowTextLengthW = user32.GetWindowTextLengthW
            
            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            
            results = []
            
            def enum_callback(hwnd, lParam):
                length = GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value.lower()
                    if "swiftseed" in title:
                        results.append(hwnd)
                return True
            
            EnumWindows(WNDENUMPROC(enum_callback), 0)
            
            if results:
                self._cached_hwnd = results[0]
                print(f"DEBUG: Cached hwnd (ctypes) = {self._cached_hwnd}")
                return self._cached_hwnd
        except Exception as ex:
            print(f"DEBUG: ctypes hwnd lookup failed: {ex}")
        return None
    
    def _win32_move_offscreen(self, hwnd):
        """Move window offscreen to 'hide' without destroying render surface"""
        try:
            import ctypes
            from ctypes import wintypes
            
            user32 = ctypes.windll.user32
            
            # Save current position before moving offscreen
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            self._saved_window_pos = (rect.left, rect.top, 
                                       rect.right - rect.left, 
                                       rect.bottom - rect.top)
            
            # Move offscreen (keeps Flutter rendering, no white flash)
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            SWP_NOACTIVATE = 0x0010
            user32.SetWindowPos(hwnd, 0, -32000, -32000, 0, 0,
                               SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE)
        except Exception as ex:
            print(f"DEBUG: Move offscreen failed: {ex}")
    
    def _win32_restore_from_offscreen(self, hwnd):
        """Restore window from offscreen position — instant, no flash"""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            
            # Get saved position, or center on screen
            saved = getattr(self, '_saved_window_pos', None)
            if saved:
                x, y, w, h = saved
            else:
                # Fallback: center on primary monitor
                screen_w = user32.GetSystemMetrics(0)
                screen_h = user32.GetSystemMetrics(1)
                w, h = 1200, 800
                x = (screen_w - w) // 2
                y = (screen_h - h) // 2
            
            # Move back to saved position
            SWP_NOZORDER = 0x0004
            SWP_NOACTIVATE = 0x0010
            user32.SetWindowPos(hwnd, 0, x, y, w, h, SWP_NOZORDER)
            
            # Ensure visible and focused
            SW_RESTORE = 9
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
        except Exception as ex:
            print(f"DEBUG: Restore from offscreen failed: {ex}")
    
    def _win32_show_window(self, hwnd):
        """Show and focus a window using ctypes"""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.ShowWindow(hwnd, 5)  # SW_SHOW
            user32.SetForegroundWindow(hwnd)
        except Exception as ex:
            print(f"DEBUG: ctypes show failed: {ex}")
    
    def _win32_hide_window(self, hwnd):
        """Hide a window using ctypes"""
        try:
            import ctypes
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
        except Exception as ex:
            print(f"DEBUG: ctypes hide failed: {ex}")

    def _force_focus_native(self):
        """Aggressively bring window to front using native APIs"""
        # 1. Flet standard (Non-blocking update)
        def flet_focus():
            try:
                self.page.window.minimized = False
                self.page.window.focused = True
                self.page.update()
            except: pass
        import threading
        threading.Thread(target=flet_focus, daemon=True).start()
        
        # 2. Native Win32 (more reliable when backgrounded)
        if sys.platform == 'win32':
            def win32_focus_task():
                import time, sys
                time.sleep(0.05)
                try:
                    import win32gui
                    import win32con
                    my_hwnd = getattr(self, '_cached_hwnd', None)
                    if not my_hwnd:
                        def callback(hwnd, extra):
                            title = win32gui.GetWindowText(hwnd).lower()
                            if "swiftseed" in title:
                                extra.append(hwnd)
                            return True
                        win_list = []
                        win32gui.EnumWindows(callback, win_list)
                        if win_list: my_hwnd = win_list[0]
                    
                    if my_hwnd:
                        win32gui.ShowWindow(my_hwnd, win32con.SW_RESTORE)
                        win32gui.ShowWindow(my_hwnd, win32con.SW_SHOW)
                        win32gui.BringWindowToTop(my_hwnd)
                        win32gui.SetForegroundWindow(my_hwnd)
                except: pass
            threading.Thread(target=win32_focus_task, daemon=True).start()

    def _create_tray_icon(self):
        """Create and run system tray icon (runs in separate thread)"""
        self.tray_icon = None
        try:
            try:
                from pystray import Icon, MenuItem as item, Menu
                from PIL import Image, ImageDraw
            except ImportError:
                print("System Tray dependencies missing. Attempting auto-install...")
                import sys
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pystray", "Pillow"])
                from pystray import Icon, MenuItem as item, Menu
                from PIL import Image, ImageDraw
            
            # Try to load the icon from assets, fallback to simple created icon
            import os
            icon_path = resource_path(os.path.join("assets", "icon.ico"))
            if os.path.exists(icon_path):
                try:
                    image = Image.open(icon_path)
                    # Resize to 64x64 if needed
                    if image.size != (64, 64):
                        image = image.resize((64, 64), Image.Resampling.LANCZOS)
                except Exception as e:
                    print(f"Error loading icon: {e}")
                    # Create fallback icon
                    image = self._create_fallback_icon()
            else:
                # Create fallback icon
                image = self._create_fallback_icon()
            
            def quit_app(icon=None, item=None):
                """Exit from tray - uses the same _exit_app as the dialog button"""
                print("PROCESS: Tray Exit clicked.")
                self._exit_app()
            
            # Setup the icon and menu
            icon = Icon(
                "SwiftSeed",
                image,
                "SwiftSeed",
                menu=Menu(
                    item('Open/Close SwiftSeed', self._toggle_window_taskbar_like, default=True),
                    item('Exit', quit_app)
                )
            )
            
            # NOTE: Do NOT set icon.action — the default=True menu item already
            # handles left-click. Setting icon.action too causes double-firing.
            self.tray_icon = icon
            self.tray_icon.run()
            
        except Exception as e:
            print(f"Error creating system tray icon: {e}")
            import traceback
            traceback.print_exc()
            self.tray_icon = None
    
    def _create_fallback_icon(self):
        """Create a simple fallback icon if the icon file is not found"""
        from PIL import Image, ImageDraw
        
        width = 64
        height = 64
        # Create a blue icon with white "S" (for SwiftSeed)
        image = Image.new('RGB', (width, height), color=(41, 98, 255))
        d = ImageDraw.Draw(image)
        # Draw a simple rectangle to make it recognizable
        d.rectangle((width // 4, height // 4, width * 3 // 4, height *  3 // 4), fill=(255, 255, 255))
        return image
    
    def _check_and_show_file_association_prompt(self):
        """Check if we should show the file association prompt and show it if needed"""
        try:
            from managers.file_association_manager import FileAssociationManager
            
            file_manager = FileAssociationManager()
            
            # Only show if running as executable
            if not file_manager.is_running_as_executable():
                return
            
            # Check if prompt has already been shown or user chose "never ask"
            prompt_shown = self.settings_manager.get('file_associations_prompt_shown', False)
            never_ask = self.settings_manager.get('file_associations_never_ask', False)
            
            if prompt_shown or never_ask:
                return
            
            # Check if already registered
            is_torrent = file_manager.is_torrent_handler()
            is_magnet = file_manager.is_magnet_handler()
            
            if is_torrent and is_magnet:
                # Already registered, no need to prompt
                self.settings_manager.set('file_associations_prompt_shown', True)
                return
            
            # Show the prompt
            def on_yes(e):
                success, message = file_manager.register_all()
                if success:
                    self._show_snack("✓ SwiftSeed is now your default torrent handler!")
                else:
                    self._show_snack(f"⚠️ {message}")
                self.settings_manager.set('file_associations_prompt_shown', True)
                dialog.open = False
                self.page.update()
            
            def on_not_now(e):
                self.settings_manager.set('file_associations_prompt_shown', True)
                dialog.open = False
                self.page.update()
            
            def on_never(e):
                self.settings_manager.set('file_associations_prompt_shown', True)
                self.settings_manager.set('file_associations_never_ask', True)
                dialog.open = False
                self.page.update()
            
            dialog = ft.AlertDialog(
                title=ft.Text("Set SwiftSeed as Default Torrent Handler?"),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(
                            "Would you like to set SwiftSeed as your default application for:",
                            size=14
                        ),
                        ft.Container(height=10),
                        ft.Row([
                            ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=20, color=ft.Colors.BLUE),
                            ft.Text("• .torrent files", size=13),
                        ]),
                        ft.Row([
                            ft.Icon(ft.Icons.LINK, size=20, color=ft.Colors.BLUE),
                            ft.Text("• magnet: links", size=13),
                        ]),
                        ft.Container(height=10),
                        ft.Text(
                            "This will allow you to:",
                            size=13,
                            weight=ft.FontWeight.BOLD
                        ),
                        ft.Text("✓ Double-click .torrent files to open them", size=12),
                        ft.Text("✓ Click magnet links to open them in SwiftSeed", size=12),
                        ft.Container(height=5),
                        ft.Text(
                            "You can change this anytime in Settings > File Associations",
                            size=11,
                            italic=True,
                            color=ft.Colors.GREY
                        ),
                    ], tight=True),
                    width=450,
                    padding=10
                ),
                actions=[
                    ft.TextButton("Never Ask Again", on_click=on_never),
                    ft.TextButton("Not Now", on_click=on_not_now),
                    ft.ElevatedButton(
                        "Yes, Set as Default",
                        icon=ft.Icons.CHECK,
                        on_click=on_yes,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.GREEN_700,
                            color=ft.Colors.WHITE,
                        )
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            # Add delay to ensure UI is fully loaded
            def show_delayed():
                time.sleep(1)  # 1 second delay
                self.page.overlay.append(dialog)
                dialog.open = True
                self.page.update()
            
            threading.Thread(target=show_delayed, daemon=True).start()
            
        except Exception as e:
            print(f"Error showing file association prompt: {e}")
            import traceback
            traceback.print_exc()

    def _on_window_event(self, e):
        """Handle window events - show confirmation dialog on close"""
        # Ignore all events if we are already in the exit sequence
        if getattr(self, '_is_exiting', False):
            return

        # Get all possible identifiers
        e_data = str(getattr(e, 'data', '') or '').lower()
        e_name = str(getattr(e, 'name', '') or '').lower()
        e_type = str(getattr(e, 'type', '') or '').lower()
        
        # Check against multiple common closed/close event names across Flet versions
        if any(x in e_data for x in ["close", "destroy"]) or \
           any(x in e_name for x in ["close", "destroy"]) or \
           any(x in e_type for x in ["close", "destroy"]):
            if self.settings_manager.get('show_close_confirmation', True):
                self._show_exit_dialog()
            else:
                action = self.settings_manager.get('default_close_action', 'minimize')
                if action == 'exit':
                    self._exit_app()
                else:
                    self._minimize_to_tray()
            return # Don't process focus for close events
        
        # Track focus and minimize state from window events
        if any(x in e_type or x in e_name for x in ["focus"]):
            self.is_window_focused = True
            self.last_focus_time = time.time()
        elif any(x in e_type or x in e_name for x in ["blur", "minimize", "hide"]):
            self.is_window_focused = False
            self.last_blur_time = time.time()
        elif any(x in e_type or x in e_name for x in ["restore"]):
            self.is_window_focused = True
            self.is_window_visible = True
            self.last_focus_time = time.time()
            
    def _show_exit_dialog(self):
        """Show the premium exit confirmation dialog"""
        try:
            if not self.exit_checkbox:
                self.exit_checkbox = ft.Checkbox(
                    label="Remember my choice and don't ask again",
                    value=False,
                    label_style=ft.TextStyle(size=13, color=ft.Colors.BLUE_200)
                )

            if not self.exit_dialog:
                self.exit_dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Row([
                        ft.Row([
                            ft.Icon(ft.Icons.EXIT_TO_APP_ROUNDED, color=ft.Colors.BLUE_400, size=24),
                            ft.Text("SwiftSeed - Close Options", size=18, weight=ft.FontWeight.W_600)
                        ], spacing=10),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE_ROUNDED,
                            icon_size=20,
                            tooltip="Cancel",
                            on_click=lambda _: self._close_dialog(self.exit_dialog)
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("How would you like to close SwiftSeed?", size=14, weight=ft.FontWeight.W_500),
                            ft.Container(height=5),
                            ft.Text("Choose 'Minimize to Tray' to keep the app running in the background for active downloads, or 'Exit' to completely shut down and save state.", 
                                    size=12, color=ft.Colors.GREY_400),
                            ft.Container(height=5),
                            self.exit_checkbox,
                        ], tight=True, spacing=10),
                        width=400,
                    ),
                    actions=[
                        ft.Row([
                            ft.TextButton(
                                "Minimize to Tray",
                                icon=ft.Icons.MINIMIZE_ROUNDED,
                                on_click=lambda _: self._minimize_to_tray(),
                            ),
                            ft.ElevatedButton(
                                "Exit SwiftSeed",
                                icon=ft.Icons.POWER_SETTINGS_NEW_ROUNDED,
                                bgcolor=ft.Colors.RED_700,
                                color=ft.Colors.WHITE,
                                on_click=lambda _: self._exit_app(),
                            ),
                        ], alignment=ft.MainAxisAlignment.END, spacing=10)
                    ],
                    actions_padding=15,
                    shape=ft.RoundedRectangleBorder(radius=12),
                )
            
            # Use page.open() if available (modern Flet 0.21.0+)
            if hasattr(self.page, 'open'):
                self.page.open(self.exit_dialog)
            else:
                # Fallback to overlay for older versions
                if self.exit_dialog not in self.page.overlay:
                    self.page.overlay.append(self.exit_dialog)
                self.exit_dialog.open = True
            
            self.page.update()
        except Exception as e:
            print(f"Error showing exit dialog: {e}")
            import traceback
            traceback.print_exc()

    def _close_dialog(self, dialog):
        """Helper to close any dialog across Flet versions"""
        if not dialog:
            return
            
        try:
            if hasattr(self.page, 'close'):
                self.page.close(dialog)
            else:
                dialog.open = False
            self.page.update()
        except:
            pass

    def _minimize_to_tray(self):
        """Minimize the application to the system tray"""
        if hasattr(self, 'exit_checkbox') and self.exit_checkbox and self.exit_checkbox.value:
            self.settings_manager.set('show_close_confirmation', False)
            self.settings_manager.set('default_close_action', 'minimize')

        if self.exit_dialog:
            if hasattr(self.page, 'close'):
                self.page.close(self.exit_dialog)
            else:
                self.exit_dialog.open = False
        
        # Cache the window handle BEFORE hiding so toggle can find it later
        if sys.platform == 'win32' and not getattr(self, '_cached_hwnd', None):
            self._find_hwnd_ctypes()
            
        self.page.window.visible = False
        self.page.window.skip_task_bar = True
        self.is_window_visible = False
        self.is_window_focused = False
        self.page.update()
        
        if getattr(self, 'tray_icon', None):
            print("App minimized to system tray")
        else:
            print("App minimized but tray icon not present (recovery may be difficult)")

    def _hide_ui_instantly(self):
        """Aggressively and instantly hide all UI components"""
        print("PROCESS: Hiding UI instantly...")
        
        # Method A: Native Win32 via ctypes (instant)
        if sys.platform == 'win32':
            my_hwnd = getattr(self, '_cached_hwnd', None)
            if my_hwnd:
                self._win32_hide_window(my_hwnd)
            
        # Method B: Flet state sync in background thread
        def flet_hide_worker():
            try:
                if hasattr(self, 'exit_dialog') and self.exit_dialog:
                    self.exit_dialog.open = False
                self.page.window.visible = False
                self.page.window.skip_task_bar = True
                self.page.update()
            except: pass
        
        threading.Thread(target=flet_hide_worker, daemon=True).start()

    def _exit_app(self):
        """Standard exit handler (e.g. from UI button or window close)"""
        if hasattr(self, 'exit_checkbox') and self.exit_checkbox and self.exit_checkbox.value:
            self.settings_manager.set('show_close_confirmation', False)
            self.settings_manager.set('default_close_action', 'exit')

        if hasattr(self, '_is_exiting') and self._is_exiting:
            return
        self._is_exiting = True
        
        # Hide everything immediately
        self._hide_ui_instantly()
        
        # Start cleanup
        threading.Thread(target=self._exit_app_background_only, daemon=True).start()

    def _exit_app_background_only(self):
        """Performs only the background cleanup and process termination"""
        print("PROCESS: Beginning background shutdown (no UI)...")
        
        # 1. Stop tray icon (if not already stopped)
        if getattr(self, 'tray_icon', None):
            try: self.tray_icon.stop()
            except: pass

        try:
            # 2. Shutdown download manager (critical for resume data)
            if hasattr(self, 'download_manager'):
                print("PROCESS: Saving torrent states (background)...")
                try: self.download_manager.shutdown()
                except: pass
            
            # 3. Final definitive exit
            print("PROCESS: Finalizing process exit (Safe Exit).")
            import os
            
            # For Windows, also kill the flet UI process specifically to be sure the UI is gone
            if sys.platform == 'win32':
                try: 
                    import subprocess
                    subprocess.Popen("taskkill /F /IM flet.exe /T", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                except: pass

            # Safe hard exit
            os._exit(0)
        except Exception as e:
            print(f"CRITICAL: Background exit failure: {e}")
            import os
            os._exit(1)
    
    def _open_torrent_file(self, file_path):
        """Open a .torrent file"""
        try:
            # Navigate to downloads tab
            self.rail.selected_index = 3
            self._set_nav_index(3)
            
            # Call downloads_view to handle the file
            if hasattr(self, 'downloads_view'):
                self.downloads_view.add_torrent_file(file_path)
        except Exception as e:
            print(f"Error opening torrent file: {e}")
            import traceback
            traceback.print_exc()
    
    def _open_magnet_link(self, magnet_link):
        """Open a magnet link"""
        try:
            # Navigate to downloads tab
            self.rail.selected_index = 3
            self._set_nav_index(3)
            
            # Call downloads_view to handle the magnet
            if hasattr(self, 'downloads_view'):
                self.downloads_view.handle_magnet_from_external(magnet_link)
        except Exception as e:
            print(f"Error opening magnet link: {e}")
            import traceback
            traceback.print_exc()
        # Persistent SnackBar for notifications
        self.page.snack_bar = ft.SnackBar(content=ft.Text(""), duration=4000)
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
        debug_log("Building search view")
        self.search_view = self._build_search_view()
        debug_log("Building bookmarks view")
        self.bookmarks_view = self._build_bookmarks_view()
        debug_log("Building history view")
        self.history_view = self._build_history_view()
        debug_log("Building downloads view")
        self.downloads_view = DownloadsView(self.page, self.download_manager)
        debug_log("Building settings view")
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
        
        # Initialize pagination state
        self.current_page = 1
        
        # Setup resize handler
        self.page.on_resize = self._on_resize
        
        # Initial layout update
        self._update_layout()

    def _on_resize(self, e):
        self._update_layout()
        
    def _update_layout(self):
        debug_log("Inside _update_layout")
        # Define mobile breakpoint
        is_mobile = self.page.width < 800
        
        # Only update if mode changed or controls are empty
        if is_mobile != self.is_mobile or not self.page.controls:
            self.is_mobile = is_mobile
            self.page.controls.clear()
            
            # Check for glass theme
            base_mode = self.settings_manager.get('base_mode')
            is_glass = base_mode == 'Glass'
            
            if is_mobile:
                # Mobile Layout: Body + Bottom Nav Bar
                self.rail.visible = False
                self.mobile_nav.visible = True
                self._update_mobile_nav_state()
                
                content = ft.Column([
                    self.body,
                    self.mobile_nav
                ], expand=True, spacing=0)
            else:
                # Desktop Layout: Side Rail + Body
                self.rail.visible = True
                self.mobile_nav.visible = False
                
                # Make rail transparent for glass theme
                if is_glass:
                    self.rail.bgcolor = ft.Colors.TRANSPARENT
                else:
                    self.rail.bgcolor = None
                
                content = ft.Row([
                    self.rail,
                    ft.VerticalDivider(width=1, color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE) if is_glass else ft.Colors.GREY_800),
                    self.body,
                ], expand=True, spacing=0)
            
            # Apply Gradient Background for Glass Theme
            if is_glass:
                bg_gradient = ft.LinearGradient(
                    begin=ft.Alignment.TOP_LEFT,
                    end=ft.Alignment.BOTTOM_RIGHT,
                    colors=["#0F0F13", "#1A1320", "#251838", "#2D1B3D"] if True else ["#E0E0E0", "#F5F5F7", "#FFFFFF"],
                )
                self.page.add(
                    ft.Container(
                        content=content,
                        expand=True,
                        gradient=bg_gradient,
                    )
                )
            else:
                self.page.add(content)
                
            debug_log(f"Calling page.update(). is_glass={is_glass}, is_mobile={is_mobile}")
            self.page.update()
            debug_log("page.update() returned")

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
                    fit=ft.BoxFit.CONTAIN,
                ),
                ft.Container(height=10),
                ft.Text("SwiftSeed", size=40, weight=ft.FontWeight.BOLD, color="primary"),
                ft.Text("Version 2.5", size=20, weight=ft.FontWeight.W_500),
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
                
                ft.Container(height=10),
                
                # Support Links
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "Check Updates", 
                            icon=ft.Icons.UPDATE, 
                            on_click=lambda e: webbrowser.open("https://github.com/sayandey021/SwiftSeed/releases")
                        ),
                        ft.ElevatedButton(
                            "Report Bug", 
                            icon=ft.Icons.BUG_REPORT, 
                            on_click=lambda e: webbrowser.open("https://github.com/sayandey021/SwiftSeed/issues"),
                            style=ft.ButtonStyle(color=ft.Colors.RED_400)
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
                ft.Container(
                    content=ft.Image(
                        src=resource_path(os.path.join("assets", "kofi_button.png")),
                        height=50,
                        fit=ft.BoxFit.CONTAIN,
                    ),
                    on_click=lambda e: webbrowser.open("https://ko-fi.com/sayandey"),
                    ink=True,
                    border_radius=10,
                    tooltip="Support me on Ko-fi",
                    padding=5
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
            content_padding=ft.padding.only(left=20, top=13, right=0, bottom=25),
            height=50,
            suffix=ft.Container(
                content=ft.IconButton(
                    icon=ft.Icons.CLEAR,
                    tooltip="Clear search",
                    icon_size=18,
                    on_click=lambda e: self._clear_search_field(e)
                ),
                padding=ft.padding.only(left=0, top=0, right=15, bottom=0)
            )
        )
        
        self.category_dropdown = ft.Dropdown(
            width=150,
            options=[ft.dropdown.Option(c.display_name) for c in Category],
            value="All",
            border_radius=10,
            content_padding=ft.Padding(15, 12, 15, 12),
        )
        self.category_dropdown.on_change = lambda _: self._perform_search(None) if self.search_field.value else None
        
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
            visible=False,
            style=ft.ButtonStyle(
                color=ft.Colors.RED_400,
                icon_color=ft.Colors.RED_400,
            )
        )

        self.load_more_btn = ft.ElevatedButton(
            "Load More Results",
            icon=ft.Icons.REFRESH,
            on_click=self._load_more,
            visible=False,
            height=40,
        )
        
        self.progress_bar = ft.ProgressBar(visible=False)
        
        # ============ SORT TAGS ============
        self.sort_tags_row = ft.Row(
            spacing=8,
            controls=[
                self._create_sort_tag(label, sort_id) 
                for label, sort_id in self.sort_options
            ]
        )
        
        # ============ FILTER PANEL ============
        # --- Provider filter chips (populated dynamically after search) ---
        self.provider_filter_row = ft.Row(
            spacing=6,
            controls=[],
            wrap=True,
        )
        
        # --- Category / File-type filter chips ---
        self.category_filter_row = ft.Row(
            spacing=6,
            controls=[
                self._create_category_chip(label, cat_id)
                for label, cat_id in self.category_filter_options
            ],
            wrap=True,
        )
        
        # --- Min Seeds / Min Peers inputs ---
        self.min_seeds_field = ft.TextField(
            label="Min Seeds",
            width=110,
            height=40,
            dense=True,
            text_size=12,
            label_style=ft.TextStyle(size=11),
            border_radius=8,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_filter_range_change,
            value="",
        )
        self.min_peers_field = ft.TextField(
            label="Min Peers",
            width=110,
            height=40,
            dense=True,
            text_size=12,
            label_style=ft.TextStyle(size=11),
            border_radius=8,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_filter_range_change,
            value="",
        )
        self.min_size_field = ft.TextField(
            label="Min Size (MB)",
            width=120,
            height=40,
            dense=True,
            text_size=12,
            label_style=ft.TextStyle(size=11),
            border_radius=8,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_filter_range_change,
            value="",
        )
        self.max_size_field = ft.TextField(
            label="Max Size (GB)",
            width=120,
            height=40,
            dense=True,
            text_size=12,
            label_style=ft.TextStyle(size=11),
            border_radius=8,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_filter_range_change,
            value="",
        )
        
        # Reset filters button
        self.reset_filters_btn = ft.TextButton(
            "Reset All Filters",
            icon=ft.Icons.FILTER_ALT_OFF,
            on_click=self._reset_all_filters,
            style=ft.ButtonStyle(
                color=ft.Colors.RED_300,
                icon_color=ft.Colors.RED_300,
            ),
        )
        
        # Active filter count badge
        self.active_filter_count = ft.Text("", size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
        self.filter_badge = ft.Container(
            content=self.active_filter_count,
            bgcolor=ft.Colors.RED_600,
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=5, vertical=1),
            visible=False,
        )
        
        # Filter toggle button
        self.filter_toggle_btn = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.FILTER_LIST, size=16, color=ft.Colors.GREY_400),
                ft.Text("Filters", size=12, color=ft.Colors.GREY_400, weight=ft.FontWeight.W_500),
                self.filter_badge,
            ], spacing=4, tight=True),
            on_click=self._toggle_filters,
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.15, ft.Colors.WHITE)),
            visible=False,  # Hidden until search results
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )
        
        # The collapsible filter panel
        self.filter_panel = ft.Container(
            content=ft.Column([
                # Sort row
                ft.Row([
                    ft.Text("Sort by:", size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.W_500),
                    self.sort_tags_row,
                ], spacing=10),
                # Divider
                ft.Container(
                    height=1,
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
                    margin=ft.margin.symmetric(vertical=4),
                ),
                # Category filters
                ft.Row([
                    ft.Text("File Type:", size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.W_500),
                ], spacing=10),
                self.category_filter_row,
                # Divider
                ft.Container(
                    height=1,
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
                    margin=ft.margin.symmetric(vertical=4),
                ),
                # Provider filters
                ft.Row([
                    ft.Text("Providers:", size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.W_500),
                ], spacing=10),
                self.provider_filter_row,
                # Divider
                ft.Container(
                    height=1,
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
                    margin=ft.margin.symmetric(vertical=4),
                ),
                # Range filters
                ft.Row([
                    ft.Text("Range:", size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.W_500),
                    self.min_seeds_field,
                    self.min_peers_field,
                    self.min_size_field,
                    self.max_size_field,
                ], spacing=8, wrap=True),
                # Reset button
                ft.Row([
                    ft.Container(expand=True),
                    self.reset_filters_btn,
                ]),
            ], spacing=6, tight=True),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.WHITE)),
            visible=False,  # Collapsed by default
            animate=ft.Animation(250, ft.AnimationCurve.EASE_OUT),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        
        # Wrap sort_section for backward compatibility (now points to filter_panel)
        self.sort_section = self.filter_panel
        # ===================================
        
        self.all_results_list = ft.ListView(expand=True, spacing=10, padding=10)
        
        # ============ MODERN DRAGGABLE TAB BAR ============
        # Track selected tab index and tabs list
        self.selected_tab_index = 0
        self.tab_contents = [self.all_results_list]  # Content views for each tab
        self.tab_names = ["All"]  # Tab names
        
        # Drag state for momentum scrolling
        self.tab_drag_start_x = 0
        self.tab_scroll_offset = 0
        self.tab_drag_velocity = 0
        self.is_dragging_tabs = False
        
        # Create individual tab button
        def create_tab_button(name, index):
            is_selected = (index == self.selected_tab_index)
            
            btn = ft.Container(
                content=ft.Text(
                    name,
                    size=13,
                    weight=ft.FontWeight.W_600 if is_selected else ft.FontWeight.W_400,
                    color=ft.Colors.PRIMARY if is_selected else ft.Colors.GREY_400,
                ),
                padding=ft.padding.symmetric(horizontal=8, vertical=6),
                border_radius=0,
                bgcolor=ft.Colors.TRANSPARENT,
                border=ft.border.only(
                    bottom=ft.BorderSide(2, ft.Colors.PRIMARY) if is_selected else ft.BorderSide(0, ft.Colors.TRANSPARENT)
                ),
                on_click=lambda e, idx=index: self._select_tab(idx),
                on_hover=lambda e: self._on_tab_hover(e),
                animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
                data={"index": index, "name": name},
            )
            return btn
        
        self._create_tab_button = create_tab_button
        
        # Initial tab button
        self.tab_buttons = [create_tab_button("All", 0)]
        
        # Scrollable tabs row - hidden scrollbar for clean look
        self.tabs_row = ft.Row(
            controls=self.tab_buttons,
            spacing=0,
            scroll=ft.ScrollMode.HIDDEN,  # Hidden scrollbar, drag and wheel still work
        )
        
        # Drag scrolling using delta (Flet handles bounds)
        self.is_dragging_tabs = False
        
        def on_pan_start(e: ft.DragStartEvent):
            self.is_dragging_tabs = True
        
        def on_pan_update(e: ft.DragUpdateEvent):
            if self.is_dragging_tabs:
                # Use delta scrolling - Flet handles bounds naturally
                try:
                    self.tabs_row.scroll_to(delta=-e.delta_x, duration=0)
                except Exception:
                    pass
        
        def on_pan_end(e: ft.DragEndEvent):
            self.is_dragging_tabs = False
        
        # Wrap in gesture detector for drag support
        self.draggable_tabs = ft.GestureDetector(
            content=self.tabs_row,
            on_pan_start=on_pan_start,
            on_pan_update=on_pan_update,
            on_pan_end=on_pan_end,
            drag_interval=10,
        )
        
        # Left gradient fade indicator (shows more tabs to the left)
        self.left_fade = ft.Container(
            width=30,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.CENTER_LEFT,
                end=ft.Alignment.CENTER_RIGHT,
                colors=[
                    ft.Colors.with_opacity(0.9, "#1a1a2e"),
                    ft.Colors.TRANSPARENT,
                ],
            ),
            visible=False,
        )
        
        # Right gradient fade indicator (shows more tabs to the right)
        self.right_fade = ft.Container(
            width=30,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.CENTER_LEFT,
                end=ft.Alignment.CENTER_RIGHT,
                colors=[
                    ft.Colors.TRANSPARENT,
                    ft.Colors.with_opacity(0.9, "#1a1a2e"),
                ],
            ),
            visible=False,
        )
        
        # Navigation buttons for tabs - scroll by selecting prev/next tab
        def scroll_tabs_left(e):
            if self.selected_tab_index > 0:
                self._select_tab(self.selected_tab_index - 1)
        
        def scroll_tabs_right(e):
            if self.selected_tab_index < len(self.tab_names) - 1:
                self._select_tab(self.selected_tab_index + 1)
        
        self.tab_nav_left = ft.IconButton(
            icon=ft.Icons.CHEVRON_LEFT,
            icon_size=18,
            icon_color=ft.Colors.GREY_400,
            tooltip="Previous tab",
            on_click=scroll_tabs_left,
            visible=False,
            style=ft.ButtonStyle(
                padding=5,
                shape=ft.CircleBorder(),
                bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            ),
        )
        self.tab_nav_right = ft.IconButton(
            icon=ft.Icons.CHEVRON_RIGHT,
            icon_size=18,
            icon_color=ft.Colors.GREY_400,
            tooltip="Next tab",
            on_click=scroll_tabs_right,
            visible=False,
            style=ft.ButtonStyle(
                padding=5,
                shape=ft.CircleBorder(),
                bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            ),
        )
        
        # Combined tab bar - clean look with just draggable tabs (no buttons)
        self.modern_tab_bar = ft.Container(
            content=self.draggable_tabs,
            height=45,
            padding=0,
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.2, ft.Colors.GREY_600))),
        )
        
        # Content container for selected tab
        self.tab_content_container = ft.Container(
            content=self.all_results_list,
            expand=True,
        )
        
        # For backward compatibility, keep search_tabs reference pointing to a wrapper
        # This will be used for tab change detection in existing code
        self.search_tabs = type('ModernTabsWrapper', (), {
            'tabs': self.tab_names,  # Will be synced
            'selected_index': 0,
            'update': lambda: None,
        })()
        
        # ============ END MODERN TAB BAR ============
        self.status_text = ft.Text("Ready to search", 
                              color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400)
        
        # Keep track of provider tabs: {provider_name: {'tab': ft.Tab, 'list': ft.ListView}}
        self.provider_tabs_map = {}
        
        # View style selector - Card, Compact, Table
        self.current_view_style = self.settings_manager.get('search_view_style', 'card')
        
        # Helper to get button style
        def get_btn_style(is_selected):
            if is_selected:
                return ft.ButtonStyle(
                    bgcolor=ft.Colors.PRIMARY,
                    icon_color=ft.Colors.WHITE,
                )
            else:
                return ft.ButtonStyle(
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREY),
                )
        
        # Store buttons as instance variables for proper updates
        self.card_btn = ft.IconButton(
            icon=ft.Icons.VIEW_AGENDA,
            tooltip="Card View",
            icon_color=ft.Colors.WHITE if self.current_view_style == 'card' else None,
            style=get_btn_style(self.current_view_style == 'card'),
        )
        self.compact_btn = ft.IconButton(
            icon=ft.Icons.VIEW_LIST,
            tooltip="Compact List View",
            icon_color=ft.Colors.WHITE if self.current_view_style == 'compact' else None,
            style=get_btn_style(self.current_view_style == 'compact'),
        )
        self.table_btn = ft.IconButton(
            icon=ft.Icons.TABLE_ROWS,
            tooltip="Table View",
            icon_color=ft.Colors.WHITE if self.current_view_style == 'table' else None,
            style=get_btn_style(self.current_view_style == 'table'),
        )
        
        def set_view_style(style):
            def handler(e):
                # Skip if search is in progress to avoid race conditions
                if self.search_in_progress:
                    self._show_snack("Please wait for search to complete")
                    return
                
                # Skip if view switching is locked (2 sec cooldown)
                if self.view_switch_locked:
                    return
                
                # Skip if this style is already selected
                if self.current_view_style == style:
                    return
                
                # Lock view switching for 2 seconds
                self.view_switch_locked = True
                
                # Update style immediately for responsive UI
                self.current_view_style = style
                self.settings_manager.set('search_view_style', style)
                
                # Update button styles and icon colors immediately
                self.card_btn.style = get_btn_style(style == 'card')
                self.card_btn.icon_color = ft.Colors.WHITE if style == 'card' else None
                self.compact_btn.style = get_btn_style(style == 'compact')
                self.compact_btn.icon_color = ft.Colors.WHITE if style == 'compact' else None
                self.table_btn.style = get_btn_style(style == 'table')
                self.table_btn.icon_color = ft.Colors.WHITE if style == 'table' else None
                
                # Disable all view buttons during cooldown
                self.card_btn.disabled = True
                self.compact_btn.disabled = True
                self.table_btn.disabled = True
                
                try:
                    self.card_btn.update()
                    self.compact_btn.update()
                    self.table_btn.update()
                    self.page.update()
                except AssertionError:
                    pass  # Controls not fully attached yet
                
                # Refresh results with new style in background thread for responsive UI
                if self.current_results:
                    def refresh_in_background():
                        try:
                            self._refresh_results_view()
                        except Exception as ex:
                            print(f"Error refreshing view style: {ex}")
                    self.page.run_thread(refresh_in_background)
                
                # Unlock view switching after 2 seconds
                def unlock_view_switch():
                    time.sleep(2)
                    self.view_switch_locked = False
                    # Re-enable buttons
                    self.card_btn.disabled = False
                    self.compact_btn.disabled = False
                    self.table_btn.disabled = False
                    try:
                        self.card_btn.update()
                        self.compact_btn.update()
                        self.table_btn.update()
                        self.page.update()
                    except AssertionError:
                        pass  # Controls not fully attached yet
                self.page.run_thread(unlock_view_switch)
            return handler
        
        self.card_btn.on_click = set_view_style('card')
        self.compact_btn.on_click = set_view_style('compact')
        self.table_btn.on_click = set_view_style('table')
        
        self.view_style_buttons = ft.Row([
            ft.Text("View:", size=12, color=ft.Colors.GREY_500),
            ft.Container(
                content=self.card_btn,
                border_radius=5,
            ),
            ft.Container(
                content=self.compact_btn,
                border_radius=5,
            ),
            ft.Container(
                content=self.table_btn,
                border_radius=5,
            ),
        ], spacing=2)

        return ft.Column(
            [
                ft.Text("SwiftSeed", size=30, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [self.search_field, self.search_btn],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row([
                    self.status_text,
                    ft.Container(expand=True),
                    self.filter_toggle_btn,
                    self.view_style_buttons,
                    self.clear_results_btn
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.filter_panel,
                self.progress_bar,
                ft.Divider(),
                # Results list (all results shown, filtered via filter panel)
                self.all_results_list,
            ],
            expand=True,
        )

    def _select_tab(self, index):
        """Handle tab selection with visual updates"""
        if index < 0 or index >= len(self.tab_names):
            return
        
        # Skip if already selected
        if index == self.selected_tab_index:
            return
        
        self.selected_tab_index = index
        self.search_tabs.selected_index = index
        
        # Update tab button visuals (this also updates nav visibility)
        self._rebuild_tab_buttons()
        
        # Update content container immediately for responsive feel
        if index < len(self.tab_contents):
            self.tab_content_container.content = self.tab_contents[index]
        
        # Scroll the selected tab into view with shorter duration
        if len(self.tab_buttons) > 0:
            try:
                approx_position = max(0, (index - 2) * 100)
                self.tabs_row.scroll_to(offset=approx_position, duration=100)
            except (Exception, AssertionError):
                pass
        
        # Single batch update for all components - do this first for immediate response
        try:
            self.page.update()
        except (Exception, AssertionError):
            pass
        
        # Ensure the selected tab content is forcibly updated
        if index < len(self.tab_contents):
            try:
                self.tab_contents[index].update()
            except (Exception, AssertionError):
                pass
                
        # Trigger real lazy loading or force a UI refresh even in search
        def lazy_load_tab():
            try:
                time.sleep(0.05)
                self._on_search_tab_change(None)
            except Exception:
                pass
        
        self.page.run_thread(lazy_load_tab)

    def _on_tab_hover(self, e):
        """Handle hover effects on tabs"""
        container = e.control
        is_selected = container.data.get("index") == self.selected_tab_index
        
        if e.data == "true":  # Hover enter
            if not is_selected:
                container.bgcolor = ft.Colors.with_opacity(0.05, ft.Colors.PRIMARY)
                container.border = ft.border.only(
                    bottom=ft.BorderSide(2, ft.Colors.with_opacity(0.5, ft.Colors.PRIMARY))
                )
        else:  # Hover exit
            if not is_selected:
                container.bgcolor = ft.Colors.TRANSPARENT
                container.border = ft.border.only(
                    bottom=ft.BorderSide(0, ft.Colors.TRANSPARENT)
                )
        
        try:
            container.update()
        except Exception:
            pass

    def _rebuild_tab_buttons(self):
        """Rebuild all tab buttons with current selection state"""
        # If buttons already exist and count matches, just update visual state
        if len(self.tab_buttons) == len(self.tab_names):
            for i, btn in enumerate(self.tab_buttons):
                is_selected = (i == self.selected_tab_index)
                # Update only visual properties
                btn.content.weight = ft.FontWeight.W_600 if is_selected else ft.FontWeight.W_400
                btn.content.color = ft.Colors.PRIMARY if is_selected else ft.Colors.GREY_400
                btn.bgcolor = ft.Colors.TRANSPARENT
                btn.border = ft.border.only(
                    bottom=ft.BorderSide(2, ft.Colors.PRIMARY) if is_selected else ft.BorderSide(0, ft.Colors.TRANSPARENT)
                )
        else:
            # Full rebuild only when tab count changes
            self.tab_buttons.clear()
            
            for i, name in enumerate(self.tab_names):
                is_selected = (i == self.selected_tab_index)
                btn = ft.Container(
                    content=ft.Text(
                        name,
                        size=13,
                        weight=ft.FontWeight.W_600 if is_selected else ft.FontWeight.W_400,
                        color=ft.Colors.PRIMARY if is_selected else ft.Colors.GREY_400,
                    ),
                    padding=ft.padding.symmetric(horizontal=8, vertical=6),
                    border_radius=0,
                    bgcolor=ft.Colors.TRANSPARENT,
                    border=ft.border.only(
                        bottom=ft.BorderSide(2, ft.Colors.PRIMARY) if is_selected else ft.BorderSide(0, ft.Colors.TRANSPARENT)
                    ),
                    on_click=lambda e, idx=i: self._select_tab(idx),
                    on_hover=lambda e: self._on_tab_hover(e),
                    animate=ft.Animation(100, ft.AnimationCurve.EASE_OUT),
                    data={"index": i, "name": name},
                )
                self.tab_buttons.append(btn)
            
            self.tabs_row.controls = self.tab_buttons
        
        # Update nav buttons visibility - only show if there's somewhere to go
        can_go_left = self.selected_tab_index > 0
        can_go_right = self.selected_tab_index < len(self.tab_names) - 1
        
        self.tab_nav_left.visible = can_go_left
        self.tab_nav_right.visible = can_go_right
        self.left_fade.visible = can_go_left
        self.right_fade.visible = can_go_right

    def _create_sort_tag(self, label, sort_id):
        """Create an individual interactive sort tag"""
        is_selected = (self.current_sort == sort_id)
        
        return ft.Container(
            content=ft.Text(
                label,
                size=11,
                color=ft.Colors.WHITE if is_selected else ft.Colors.GREY_400,
                weight=ft.FontWeight.W_600 if is_selected else ft.FontWeight.NORMAL,
            ),
            bgcolor=ft.Colors.PRIMARY if is_selected else ft.Colors.with_opacity(0.1, ft.Colors.GREY),
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            border_radius=20,
            on_click=lambda e, sid=sort_id: self._apply_sort(sid),
            on_hover=self._on_sort_tag_hover,
            data=sort_id,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )

    def _on_sort_tag_hover(self, e):
        if e.control.data == self.current_sort:
            return
        
        if e.data == "true":
            e.control.bgcolor = ft.Colors.with_opacity(0.2, ft.Colors.PRIMARY)
        else:
            e.control.bgcolor = ft.Colors.with_opacity(0.1, ft.Colors.GREY)
        e.control.update()

    def _create_category_chip(self, label, cat_id):
        """Create an interactive category filter chip"""
        is_selected = cat_id in self.active_category_filters
        
        return ft.Container(
            content=ft.Text(
                label,
                size=11,
                color=ft.Colors.WHITE if is_selected else ft.Colors.GREY_400,
                weight=ft.FontWeight.W_600 if is_selected else ft.FontWeight.NORMAL,
            ),
            bgcolor=ft.Colors.DEEP_PURPLE if is_selected else ft.Colors.with_opacity(0.1, ft.Colors.GREY),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_radius=20,
            border=ft.border.all(1, ft.Colors.DEEP_PURPLE_300 if is_selected else ft.Colors.TRANSPARENT),
            on_click=lambda e, cid=cat_id: self._toggle_category_filter(cid),
            on_hover=self._on_filter_chip_hover,
            data={"type": "category", "id": cat_id},
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )

    def _create_provider_chip(self, provider_name):
        """Create an interactive provider filter chip"""
        is_selected = provider_name in self.active_provider_filters
        
        return ft.Container(
            content=ft.Text(
                provider_name,
                size=11,
                color=ft.Colors.WHITE if is_selected else ft.Colors.GREY_400,
                weight=ft.FontWeight.W_600 if is_selected else ft.FontWeight.NORMAL,
            ),
            bgcolor=ft.Colors.TEAL_700 if is_selected else ft.Colors.with_opacity(0.1, ft.Colors.GREY),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_radius=20,
            border=ft.border.all(1, ft.Colors.TEAL_300 if is_selected else ft.Colors.TRANSPARENT),
            on_click=lambda e, pn=provider_name: self._toggle_provider_filter(pn),
            on_hover=self._on_filter_chip_hover,
            data={"type": "provider", "id": provider_name},
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )

    def _on_filter_chip_hover(self, e):
        """Hover effect for filter chips"""
        chip_data = e.control.data
        chip_type = chip_data.get("type", "")
        chip_id = chip_data.get("id", "")
        
        # Check if selected
        if chip_type == "category":
            is_selected = chip_id in self.active_category_filters
        elif chip_type == "provider":
            is_selected = chip_id in self.active_provider_filters
        else:
            return
        
        if is_selected:
            return  # Don't change hover on selected chips
        
        if e.data == "true":
            e.control.bgcolor = ft.Colors.with_opacity(0.2, ft.Colors.PRIMARY)
        else:
            e.control.bgcolor = ft.Colors.with_opacity(0.1, ft.Colors.GREY)
        try:
            e.control.update()
        except:
            pass

    def _toggle_filters(self, e):
        """Toggle filter panel visibility"""
        self.filters_visible = not self.filters_visible
        self.filter_panel.visible = self.filters_visible
        
        # Update toggle button appearance
        if self.filters_visible:
            self.filter_toggle_btn.bgcolor = ft.Colors.with_opacity(0.15, ft.Colors.PRIMARY)
            self.filter_toggle_btn.border = ft.border.all(1, ft.Colors.with_opacity(0.4, ft.Colors.PRIMARY))
        else:
            self.filter_toggle_btn.bgcolor = ft.Colors.with_opacity(0.08, ft.Colors.WHITE)
            self.filter_toggle_btn.border = ft.border.all(1, ft.Colors.with_opacity(0.15, ft.Colors.WHITE))
        
        try:
            self.filter_toggle_btn.update()
            self.filter_panel.update()
            self.page.update()
        except (AssertionError, Exception):
            pass

    def _toggle_category_filter(self, cat_id):
        """Toggle a category filter on/off"""
        if cat_id in self.active_category_filters:
            self.active_category_filters.discard(cat_id)
        else:
            self.active_category_filters.add(cat_id)
        
        # Rebuild category chips
        self.category_filter_row.controls = [
            self._create_category_chip(label, cid)
            for label, cid in self.category_filter_options
        ]
        
        self._update_filter_badge()
        self._apply_filters_and_refresh()

    def _toggle_provider_filter(self, provider_name):
        """Toggle a provider filter on/off"""
        if provider_name in self.active_provider_filters:
            self.active_provider_filters.discard(provider_name)
        else:
            self.active_provider_filters.add(provider_name)
        
        # Rebuild provider chips
        self._rebuild_provider_chips()
        
        self._update_filter_badge()
        self._apply_filters_and_refresh()

    def _rebuild_provider_chips(self):
        """Rebuild provider filter chips from current results"""
        # Get unique provider names from current results
        provider_names = sorted(set(t.provider_name for t in self.current_results))
        self.provider_filter_row.controls = [
            self._create_provider_chip(pn) for pn in provider_names
        ]

    def _on_filter_range_change(self, e):
        """Handle changes to numeric range filter fields (debounced via thread)"""
        # Parse value from the field
        try:
            val = int(e.control.value) if e.control.value.strip() else 0
        except ValueError:
            return  # Ignore non-numeric input
        
        # Determine which field changed
        if e.control == self.min_seeds_field:
            self.filter_min_seeds = val
        elif e.control == self.min_peers_field:
            self.filter_min_peers = val
        elif e.control == self.min_size_field:
            self.filter_min_size = val * (1024 ** 2)  # MB to bytes
        elif e.control == self.max_size_field:
            self.filter_max_size = val * (1024 ** 3)  # GB to bytes
        
        self._update_filter_badge()
        self._apply_filters_and_refresh()

    def _reset_all_filters(self, e=None):
        """Reset all filters to default state"""
        self.active_provider_filters.clear()
        self.active_category_filters.clear()
        self.filter_min_seeds = 0
        self.filter_min_peers = 0
        self.filter_min_size = 0
        self.filter_max_size = 0
        
        # Clear text fields
        self.min_seeds_field.value = ""
        self.min_peers_field.value = ""
        self.min_size_field.value = ""
        self.max_size_field.value = ""
        
        # Rebuild filter chips
        self.category_filter_row.controls = [
            self._create_category_chip(label, cid)
            for label, cid in self.category_filter_options
        ]
        self._rebuild_provider_chips()
        
        self._update_filter_badge()
        self._apply_filters_and_refresh()

    def _update_filter_badge(self):
        """Update the active filter count badge on the toggle button"""
        count = len(self.active_provider_filters) + len(self.active_category_filters)
        if self.filter_min_seeds > 0:
            count += 1
        if self.filter_min_peers > 0:
            count += 1
        if self.filter_min_size > 0:
            count += 1
        if self.filter_max_size > 0:
            count += 1
        
        if count > 0:
            self.active_filter_count.value = str(count)
            self.filter_badge.visible = True
        else:
            self.filter_badge.visible = False
        
        try:
            self.filter_badge.update()
            self.filter_toggle_btn.update()
        except (AssertionError, Exception):
            pass

    def _get_filtered_results(self, results=None):
        """Apply all active filters to results and return filtered list"""
        if results is None:
            results = self.current_results
        
        if not results:
            return []
        
        filtered = list(results)
        
        # Filter by provider
        if self.active_provider_filters:
            filtered = [t for t in filtered if t.provider_name in self.active_provider_filters]
        
        # Filter by category / file type
        if self.active_category_filters:
            def matches_category(torrent):
                cat_name = torrent.category.display_name if (hasattr(torrent, 'category') and torrent.category) else "Other"
                # Handle TV/Series alias
                if cat_name == "Series":
                    return "TV" in self.active_category_filters or "Series" in self.active_category_filters
                return cat_name in self.active_category_filters
            filtered = [t for t in filtered if matches_category(t)]
        
        # Filter by min seeds
        if self.filter_min_seeds > 0:
            filtered = [t for t in filtered if t.seeders >= self.filter_min_seeds]
        
        # Filter by min peers
        if self.filter_min_peers > 0:
            filtered = [t for t in filtered if t.peers >= self.filter_min_peers]
        
        # Filter by min size
        if self.filter_min_size > 0:
            filtered = [t for t in filtered if self._parse_size(t.size) >= self.filter_min_size]
        
        # Filter by max size
        if self.filter_max_size > 0:
            filtered = [t for t in filtered if self._parse_size(t.size) <= self.filter_max_size]
        
        return filtered

    def _apply_filters_and_refresh(self):
        """Apply current filters and refresh the results view"""
        if not self.current_results:
            return
        
        # Sort the filtered results
        filtered = self._get_filtered_results()
        self._sort_results(filtered)
        
        # Update status text
        total = len(self.current_results)
        showing = len(filtered)
        if showing < total:
            self.status_text.value = f"Showing {showing} of {total} results (filtered)"
        else:
            self.status_text.value = f"Found {total} results"
        
        # Refresh all visible lists
        self._refresh_results_view()
        
        try:
            self.page.update()
        except (AssertionError, Exception):
            pass

    def _on_header_hover(self, e):
        """Hover effect for table headers"""
        if e.data == "true":
            e.control.bgcolor = ft.Colors.with_opacity(0.1, ft.Colors.PRIMARY)
        else:
            e.control.bgcolor = ft.Colors.TRANSPARENT
        try:
            e.control.update()
        except: pass

    def _apply_sort(self, sort_id):
        """Update results sorting immediately"""
        if not self.current_results:
            return
            
        self.current_sort = sort_id
        self.settings_manager.set('default_sort', sort_id)
        
        # Update sort tags UI
        for tag in self.sort_tags_row.controls:
            sid = tag.data
            is_selected = (sid == sort_id)
            tag.bgcolor = ft.Colors.PRIMARY if is_selected else ft.Colors.with_opacity(0.1, ft.Colors.GREY)
            tag.content.color = ft.Colors.WHITE if is_selected else ft.Colors.GREY_400
            tag.content.weight = ft.FontWeight.W_600 if is_selected else ft.FontWeight.NORMAL
            try:
                tag.update()
            except: pass
            
        # Perform sort
        self._sort_results(self.current_results)
        
        # Refresh UI
        self._refresh_results_view()
        self.page.update()

    def _sort_results(self, results):
        """Helper to sort results by current preference"""
        if not results: return
        
        if self.current_sort == "seeders":
            results.sort(key=lambda t: t.seeders if t.seeders >= 0 else -1, reverse=True)
        elif self.current_sort == "peers":
            results.sort(key=lambda t: t.peers if t.peers >= 0 else -1, reverse=True)
        elif self.current_sort == "size":
            results.sort(key=lambda t: self._parse_size(t.size), reverse=True)
        elif self.current_sort == "name":
            results.sort(key=lambda t: t.name.lower())

    def _parse_size(self, size_str):
        """Convert size string (e.g. 1.2 GB) to bytes for sorting"""
        if not size_str or size_str == "Unknown":
            return 0
        try:
            size_str = size_str.upper().strip()
            parts = size_str.split()
            if not parts: return 0
            
            value = float(parts[0])
            if len(parts) > 1:
                unit = parts[1][0] # G, M, K, B
                multipliers = {"B": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
                value *= multipliers.get(unit, 1)
            return value
        except:
            return 0

    def _clear_search_field(self, e):
        self.search_field.value = ""
        self.search_field.update()

    def _clear_results(self, e):
        # Clear main results
        self.all_results_list.controls.clear()
        
        # Clear all provider tab lists
        for provider_name, tab_data in self.provider_tabs_map.items():
            if 'list' in tab_data:
                tab_data['list'].controls.clear()
        
        # Reset tabs to just "All" for modern tab bar
        self.tab_names = ["All"]
        self.tab_contents = [self.all_results_list]
        self.selected_tab_index = 0
        self.search_tabs.selected_index = 0
        self._rebuild_tab_buttons()
        self.tab_content_container.content = self.all_results_list
        
        self.provider_tabs_map = {}
        self.current_results = []
        self.displayed_count = {}  # Reset displayed counts
        self.refreshed_tabs = set()  # Reset refreshed tabs tracking
        self.status_text.value = "Ready to search"
        self.clear_results_btn.visible = False
        self.load_more_btn.visible = False
        self.filter_panel.visible = False # Hide filter panel
        self.filter_toggle_btn.visible = False # Hide filter toggle
        self.filters_visible = False
        self._reset_all_filters() # Reset all filters
        self.tab_nav_left.visible = False  # Hide nav buttons
        self.tab_nav_right.visible = False
        self.left_fade.visible = False
        self.right_fade.visible = False
        self.current_page = 1
        self._current_tab_scroll = 0
        
        # Reset scroll position to show tabs from start
        try:
            self.tabs_row.scroll_to(offset=0, duration=0)
        except Exception:
            pass
        
        # Force UI refresh
        try:
            self.all_results_list.update()
            self.tabs_row.update()
            self.tab_content_container.update()
            self.page.update()
        except (AssertionError, Exception):
            pass

    def _load_more(self, e):
        print(f"DEBUG: Load more clicked. requesting page {self.current_page + 1}")
        self.current_page += 1
        self._perform_search(e, append=True)



    def _perform_search(self, e, append=False):
        print(f"DEBUG: _perform_search called. query={self.search_field.value}, append={append}")
        query = self.search_field.value
        if not query:
            return

        category_name = self.category_dropdown.value
        category = Category.from_string(category_name)
        
        if not append:
            self.current_page = 1
            self.history_manager.add_search(query, category_name)
            self.all_results_list.controls.clear()
            
            # Reset tabs for new search (modern tab bar)
            self.tab_names = ["All"]
            self.tab_contents = [self.all_results_list]
            self.selected_tab_index = 0
            self.search_tabs.selected_index = 0
            self._current_tab_scroll = 0  # Reset scroll position
            self._rebuild_tab_buttons()
            self.tab_content_container.content = self.all_results_list
            
            # Reset tabs scroll to start
            try:
                self.tabs_row.scroll_to(offset=0, duration=0)
            except Exception:
                pass
            
            self.provider_tabs_map = {} # Clear provider map
            self.refreshed_tabs = set() # Reset for new search
            self.current_results = [] # Clear results for new search
            self.displayed_count = {}  # Reset displayed counts
            
            self.status_text.value = f"Searching for '{query}'..."
            self.load_more_btn.visible = False
        else:
            self.status_text.value = f"Loading page {self.current_page}..."
            self.load_more_btn.disabled = True

        self.progress_bar.visible = True
        self.search_btn.disabled = True
        self.clear_results_btn.visible = False
        self.filter_panel.visible = False # Temporarily hide filter panel during search
        self.filter_toggle_btn.visible = False # Hide toggle during search
        self.search_in_progress = True  # Lock view switching during search
        # Disable view style buttons during search
        self.card_btn.disabled = True
        self.compact_btn.disabled = True
        self.table_btn.disabled = True
        if not append:
            self._select_tab(0)  # Switch to All tab on new search
        self.page.update()

        # Run in thread
        def search_task():
            results = []
            enabled_providers = self.settings_manager.get_enabled_providers()
            
            if not enabled_providers:
                print("No providers enabled!")
            
            # Create a list of providers to search
            providers_to_search = []
            for p in self.providers:
                if p.info.id in enabled_providers:
                    # If user selected ALL, search everything
                    if category == Category.ALL:
                        providers_to_search.append(p)
                    # If provider is general (ALL), always search it
                    elif p.info.specialized_category == Category.ALL:
                        providers_to_search.append(p)
                    # If provider is specialized and matches, search it
                    elif p.info.specialized_category == category:
                        providers_to_search.append(p)
                    # Specialized aliases: TV/SERIES consistency
                    elif category in [Category.TV, Category.SERIES] and p.info.specialized_category in [Category.TV, Category.SERIES]:
                        providers_to_search.append(p)
            
            if not providers_to_search:
                print("No eligible providers for this category.")
                self._update_results_ui([], empty_title="No Relevant Providers", empty_subtitle=f"None of your enabled providers specialize in {category_name}. Please search in 'All' or enable more providers.")
                self.search_in_progress = False  # Unlock view switching
                return

            # Use ThreadPoolExecutor for parallel searching
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            def search_provider(provider):
                """Search a single provider and return results"""
                try:
                    print(f"Searching {provider.info.name} (Page {self.current_page})...")
                    # Try passing page
                    try:
                        return provider.search(query, category, page=self.current_page)
                    except TypeError:
                        # Fallback for providers not supporting pagination
                        if self.current_page == 1:
                            return provider.search(query, category)
                        else:
                            return [] # Skip if they don't support paging
                except Exception as err:
                    print(f"Error searching {provider.info.name}: {err}")
                    return []
            
            # Create a progress tracker to update UI every second while searching
            search_active = True
            def update_live_status():
                start_time = time.time()
                while search_active:
                    elapsed = int(time.time() - start_time)
                    # Don't overwrite if search just finished
                    if not search_active: break
                    
                    found_count = len(results)
                    self.status_text.value = f"Searching ({elapsed}s)... Found {found_count} results"
                    try:
                        self.page.update()
                    except: pass
                    time.sleep(1)
            
            self.page.run_thread(update_live_status)

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
                            # Also update current_results progressively for tab switching
                            if not append:
                                self.current_results = results.copy()
                            else:
                                self.current_results.extend(provider_results)
                            # Update UI with partial results for faster feedback
                            self.status_text.value = f"Found {len(results)} results so far..."
                            
                            # Add new results to UI immediately (progressive loading)
                            # We pass 'results' (local accumulator) so UI knows we have items and doesn't show "No Results"
                            self._update_results_ui(results, append=append, new_results_count=len(provider_results), progressive_results=provider_results)
                            
                    except Exception as exc:
                        print(f"{provider.info.name} generated an exception: {exc}")
            
            search_active = False # Stop the progress tracker thread
            
            # Final sort based on current preference
            self._sort_results(results)
            
            if append:
                # Add to existing
                self.current_results.extend(results)
            else:
                self.current_results = results
            
            # Update status and button states
            # (Progressive additions above will be overwritten by a clean paginated rebuild below)
            self.status_text.value = f"Found {len(self.current_results)} results"
            self.clear_results_btn.visible = len(self.current_results) > 0
            self.load_more_btn.visible = len(results) > 0
            self.load_more_btn.disabled = False
            self.progress_bar.visible = False
            self.search_btn.disabled = False
            self.search_in_progress = False  # Unlock view switching
            # Re-enable view style buttons
            self.card_btn.disabled = False
            self.compact_btn.disabled = False
            self.table_btn.disabled = False
            
            # Show filter toggle if results found
            if self.current_results:
                 self.filter_toggle_btn.visible = True
                 # Show filter panel if it was open
                 if self.filters_visible:
                     self.filter_panel.visible = True
                 # Populate provider filter chips from results
                 self._rebuild_provider_chips()
            
            # Rebuild cleanly paginated view (replaces the unpaginated progressive load output)
            self._refresh_results_view()

            self.page.update()
            
            # Start background scraper for unknown stats (Academic/RARBG)
            # Only scrape ones with seeders == -1
            unknown_torrents = [t for t in self.current_results if t.seeders == -1]
            if unknown_torrents:
                self.page.run_thread(self._scrape_stats, unknown_torrents)

        self.page.run_thread(search_task)

    def _update_results_ui(self, results, append=False, new_results_count=0, empty_title="No results found", empty_subtitle="Check your enabled providers in Settings", progressive_results=None):
        # Note: Progress bar and button states are managed by search_task's final step
        # This function only updates the result list UI and status text
        # View style buttons are disabled during search, so no lock needed
        self.status_text.value = f"Found {len(results)} results so far..."
        
        if not results:
            if not append:
                self.all_results_list.controls.clear()
                self.all_results_list.controls.append(
                    ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.SEARCH_OFF, size=50, 
                                color=ft.Colors.GREY_400 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_600),
                        ft.Text(empty_title, size=20, 
                                color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400),
                        ft.Text(empty_subtitle, size=12, 
                                color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.Alignment.CENTER,
                    padding=50,
                    data="no_results_view"  # Tag for identification
                )
            )
        else:
            # Remove any existing load more button container OR no results view
            to_remove = []
            for control in self.all_results_list.controls:
                # Remove load more button container
                if isinstance(control, ft.Container) and control.content == self.load_more_btn:
                    to_remove.append(control)
                # Remove no results view
                elif control.data == "no_results_view":
                    to_remove.append(control)
            
            for control in to_remove:
                self.all_results_list.controls.remove(control)
            
            # Helper to manage list properties
            def set_list_props(list_view):
                if self.current_view_style == 'table':
                    list_view.spacing = 0
                    list_view.padding = ft.padding.only(left=5, top=5, bottom=5, right=20)
                elif self.current_view_style == 'compact':
                    list_view.spacing = 3
                    list_view.padding = ft.padding.only(left=5, top=5, bottom=5, right=20)
                else:
                    list_view.spacing = 10
                    list_view.padding = ft.padding.only(left=10, top=10, bottom=10, right=15)

            set_list_props(self.all_results_list)

            # --- Process Results for "All" Tab ---
            # If progressive_results is provided, these are the NEW items to add (or all items if not append)
            # If we are just refreshing UI (not searching), results has everything
            
            items_to_process = progressive_results if progressive_results is not None else results
            
            if not append and progressive_results is None:
                # Full refresh case
                self.all_results_list.controls.clear()
                # Clear provider tabs content OR reset them if we want to be strict
                # Since we reset tabs in _perform_search for new searches, we might just be clearing content here
                # if this is called e.g. from _refresh_results_view or a manual refresh
                for p_data in self.provider_tabs_map.values():
                    p_data['list'].controls.clear()

            # Add to All list
            if self.current_view_style == 'table':
                # Table head for "All" list if fresh
                if not append and progressive_results is None: # Only if full refresh
                     self.all_results_list.controls.extend(self._create_table_view(items_to_process, with_header=True))
                elif append:
                     self.all_results_list.controls.extend(self._create_table_view(items_to_process, with_header=False))
                else:
                     # Progressive Search Update - "All" list might need header if empty
                     has_header = len(self.all_results_list.controls) > 0
                     self.all_results_list.controls.extend(self._create_table_view(items_to_process, with_header=not has_header))

            elif self.current_view_style == 'compact':
                for torrent in items_to_process:
                    self.all_results_list.controls.append(self._create_compact_row(torrent))
            else:
                for torrent in items_to_process:
                    self.all_results_list.controls.append(self._create_torrent_card(torrent))

            # --- Process Results for Provider Tabs ---
            # Group items by provider
            from collections import defaultdict
            provider_groups = defaultdict(list)
            for torrent in items_to_process:
                 provider_groups[torrent.provider_name].append(torrent)
            
            for provider_name, provider_items in provider_groups.items():
                if provider_name not in self.provider_tabs_map:
                    # Create new tab for modern tab bar
                    p_list = ft.ListView(expand=True, spacing=10, padding=10)
                    set_list_props(p_list)
                    
                    # Add to modern tab bar
                    self.tab_names.append(provider_name)
                    self.tab_contents.append(p_list)
                    self.provider_tabs_map[provider_name] = {'list': p_list}
                    
                    # Rebuild tab buttons to include new tab
                    self._rebuild_tab_buttons()
                    
                    # Show nav buttons when we have multiple tabs
                    if len(self.tab_names) > 3:
                        self.tab_nav_left.visible = True
                        self.tab_nav_right.visible = True
                        self.left_fade.visible = True
                        self.right_fade.visible = True
                
                # Add items to provider list
                p_list = self.provider_tabs_map[provider_name]['list']
                
                if self.current_view_style == 'table':
                    # Check if list has header
                    has_header = len(p_list.controls) > 0
                    p_list.controls.extend(self._create_table_view(provider_items, with_header=not has_header))
                elif self.current_view_style == 'compact':
                    for torrent in provider_items:
                        p_list.controls.append(self._create_compact_row(torrent))
                else:
                    for torrent in provider_items:
                        p_list.controls.append(self._create_torrent_card(torrent))

            # Update Load More button logic - only on "All" tab for now or all?
            # Typically load more applies to the query, affecting all. Putting it in "All" is standard.
            max_per_provider = self.settings_manager.get('max_results_per_provider', 50)
            display_limit = self.displayed_count.get("All", max_per_provider)
            has_more = len(self.current_results) > display_limit
            
            if self.load_more_btn.visible and not has_more:
                # Add a container for button to center it
                self.all_results_list.controls.append(
                    ft.Container(content=self.load_more_btn, alignment=ft.Alignment.CENTER, padding=10)
                )
        try:
            self.page.update()
        except (AssertionError, Exception) as _err:
            print(f"Warning: UI update error in _update_results_ui: {_err}")

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

    def _scrape_stats(self, torrents):
        """Background task to scrape real stats for unknown torrents."""
        try:
            from utils.tracker_scraper import TrackerScraper
            
            # Extract info hashes
            hashes = [t.info_hash for t in torrents if t.info_hash]
            if not hashes: return
            
            # Show scrap indicator? No, keep it subtle.
            
            scraper = TrackerScraper(timeout=2)
            # Use a few common trackers (UDP)
            trackers = [
                "udp://tracker.opentrackr.org:1337/announce",
                "udp://open.stealth.si:80/announce",
                "udp://tracker.torrent.eu.org:451/announce",
                "udp://explicit.tracker.fixme.ovh:2710/announce" # For porn?
            ]
            
            found_stats = {}
            # Limit torrents per batch to avoid overwhelming
            max_batch = 50
            if len(hashes) > max_batch:
                hashes = hashes[:max_batch]
                
            for tracker in trackers:
                if len(found_stats) >= len(hashes): break # All found
                
                # Filter ones we still need
                needed_hashes = [h for h in hashes if h not in found_stats]
                if not needed_hashes: break
                
                stats = scraper.scrape_udp(tracker, needed_hashes)
                if stats:
                    found_stats.update(stats)
            
            # Update objects
            updated_count = 0
            for t in torrents:
                if t.info_hash in found_stats:
                    s, p = found_stats[t.info_hash]
                    # Only update if valid numbers
                    if s >= 0:
                        t.seeders = s
                        t.peers = p
                        updated_count += 1
            
            if updated_count > 0:
                print(f"Scraped stats for {updated_count} torrents")
                # Refresh UI to show new numbers with proper pagination
                self.page.run_thread(self._refresh_results_view)
                
        except Exception as e:
            print(f"Scrape stats failed: {e}")

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
        
        # Category color mapping
        category_colors = {
            "Anime": ft.Colors.PINK_400,
            "Movies": ft.Colors.BLUE_400,
            "TV": ft.Colors.PURPLE_400,
            "Series": ft.Colors.PURPLE_400,
            "Adult": ft.Colors.RED_900,  # Renamed from Porn
            "Porn": ft.Colors.RED_900,   # Keep for backwards compatibility
            "Games": "#1e3a8a",  # Dark blue (Tailwind blue-900)
            "Software": ft.Colors.CYAN_400,
            "Apps": ft.Colors.CYAN_400,
            "Books": ft.Colors.AMBER_700,
            "Music": ft.Colors.TEAL_400,
            "All": ft.Colors.BLUE_GREY_600,
            "Unknown": ft.Colors.GREY,
            "Other": ft.Colors.GREY_600,
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

        # Theme-specific styling
        base_mode = self.settings_manager.get('base_mode')
        is_glass = base_mode == 'Glass'
        is_dark_glass = True
        
        if is_glass:
            # Premium Glass Card Style - Solid Cards as requested
            # Darker, solid background for contrast, no blur on card itself
            card_bgcolor = "#252525" if is_dark_glass else "#F0F0F0" 
            card_opacity = 1.0 # Solid card
            border = ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.WHITE if is_dark_glass else ft.Colors.BLACK))
            blur_effect = None # No blur on the card
            
            # Gradient Button Style (Purple -> Pink)
            download_btn = ft.Container(
                content=ft.ElevatedButton(
                    "Download",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=lambda _, t=torrent: self._start_download(t),
                    style=ft.ButtonStyle(
                        color=ft.Colors.WHITE,
                        bgcolor={"": ft.Colors.TRANSPARENT},
                        shape=ft.RoundedRectangleBorder(radius=8),
                        elevation=0,
                    ),
                ),
                gradient=ft.LinearGradient(colors=["#a855f7", "#ec4899"]),
                border_radius=8,
            )
        else:
            # Standard Style
            card_bgcolor = None
            card_opacity = 1.0
            border = None
            blur_effect = None
            download_btn = ft.ElevatedButton(
                "Download",
                icon=ft.Icons.DOWNLOAD,
                on_click=lambda _, t=torrent: self._start_download(t),
                bgcolor=ft.Colors.GREEN_700,
                color=ft.Colors.WHITE
            )

        card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.DOWNLOAD, color=icon_color),
                        title=ft.Text(torrent.name, weight=ft.FontWeight.BOLD),
                        subtitle=ft.Column([
                            ft.Text(f"{torrent.size} • {('N/A' if torrent.seeders == -1 else torrent.seeders)} Seeds • {('N/A' if torrent.peers == -1 else torrent.peers)} Peers • {torrent.provider_name}"),
                            ft.Row(tags, spacing=5)
                        ], spacing=2),
                        trailing=ft.IconButton(
                            icon=bookmark_icon,
                            icon_color=bookmark_color,
                            on_click=lambda e, t=torrent: self._toggle_bookmark(e, t)
                        ),
                    ),
                    ft.Row([
                        download_btn,
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
                bgcolor=card_bgcolor,
                border=border,
                border_radius=10,
                blur=blur_effect,
                opacity=card_opacity if is_glass else 1.0,
            ),
            elevation=0 if is_glass else 1,
        )
        card.data = torrent
        return card

    def _create_compact_row(self, torrent: Torrent):
        """Create a compact list row for a torrent result"""
        try:
            is_dead = torrent.seeders == 0
            is_healthy = torrent.seeders >= 50
            if torrent.seeders == -1:
                seed_color = ft.Colors.BLUE # Unknown
                seed_text = "S:?"
                peer_text = "P:?"
            else:
                seed_color = ft.Colors.RED if is_dead else (ft.Colors.GREEN if is_healthy else ft.Colors.ORANGE)
                seed_text = f"S:{torrent.seeders}"
                peer_text = f"P:{torrent.peers}"
            
            is_bookmarked = torrent.name in self.bookmarked_names
            
            category_name = torrent.category.display_name if (hasattr(torrent, 'category') and torrent.category) else "?"
            
            provider_str = torrent.provider_name[:3].upper() if torrent.provider_name else "UNK"
            
            # Safe styling for text to ensure visibility
            # text_color = ft.Colors.ON_SURFACE_VARIANT (might fail)
            
            row = ft.Container(
                content=ft.Row([
                    # Health indicator
                    ft.Container(
                        content=ft.Icon(ft.Icons.CIRCLE, size=10, color=seed_color),
                        width=20,
                    ),
                    # Name - expandable
                    ft.Text(torrent.name, size=13, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, weight=ft.FontWeight.W_500),
                    # Size
                    ft.Text(torrent.size, size=11, width=70, text_align=ft.TextAlign.RIGHT, 
                           color=ft.Colors.GREY_500),
                    # Seeds/Peers
                    ft.Text(seed_text, size=11, width=50, color=seed_color, weight=ft.FontWeight.BOLD),
                    ft.Text(peer_text, size=11, width=40, color=ft.Colors.BLUE),
                    # Provider
                    ft.Container(
                        content=ft.Text(provider_str, size=9, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                        bgcolor=ft.Colors.BLUE_GREY_600,
                        padding=ft.padding.symmetric(horizontal=4, vertical=2),
                        border_radius=3,
                        width=35,
                        alignment=ft.Alignment.CENTER,
                    ),
                    # Category
                    ft.Container(
                        content=ft.Text(category_name[:4], size=9, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                        bgcolor=ft.Colors.BLUE_600, # Use static color instead of primary for safety
                        padding=ft.padding.symmetric(horizontal=4, vertical=2),
                        border_radius=3,
                        width=40,
                        alignment=ft.Alignment.CENTER,
                    ),
                    # Actions Row for explicit spacing
                    ft.Row([
                        # Bookmark
                        ft.IconButton(
                            icon=ft.Icons.STAR if is_bookmarked else ft.Icons.STAR_BORDER,
                            icon_size=16,
                            icon_color=ft.Colors.AMBER if is_bookmarked else ft.Colors.GREY_400,
                            on_click=lambda e, t=torrent: self._toggle_bookmark(e, t),
                            tooltip="Bookmark",
                            style=ft.ButtonStyle(padding=0),
                            width=30,
                            height=30,
                        ),
                        # Download
                        ft.IconButton(
                            icon=ft.Icons.DOWNLOAD,
                            icon_size=16,
                            icon_color=ft.Colors.GREEN,
                            on_click=lambda e, t=torrent: self._start_download(t),
                            tooltip="Download",
                            style=ft.ButtonStyle(padding=0),
                            width=30,
                            height=30,
                        ),
                        # Magnet
                        ft.IconButton(
                            icon=ft.Icons.LINK,
                            icon_size=16,
                            on_click=lambda e, t=torrent: self._copy_magnet(t),
                            tooltip="Copy Magnet",
                            style=ft.ButtonStyle(padding=0),
                            width=30,
                            height=30,
                        ),
                        # Open Site
                        ft.IconButton(
                            icon=ft.Icons.OPEN_IN_NEW,
                            icon_size=16,
                            on_click=lambda e, t=torrent: self._open_url(t),
                            tooltip="Open Site",
                            style=ft.ButtonStyle(padding=0),
                            width=30,
                            height=30,
                        ),
                    ], spacing=2, width=130, alignment=ft.MainAxisAlignment.END),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.only(left=8, top=5, bottom=5, right=35),  # Extra right padding for scrollbar
                bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.GREY), # Safe subtle background
                border_radius=5,
                border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.GREY)),
            )
            row.data = torrent
            return row
            
        except Exception as e:
            print(f"Error creating compact row: {e}")
            return ft.Container(content=ft.Text(f"Error rendering row: {e}", color=ft.Colors.RED, size=10))

    def _create_table_view(self, results, with_header=True):
        """Create table view as individual row containers for smooth scrolling"""
        if not results:
            return []
        
        try:
            items = []
            
            # Table header row
            if with_header:
                header = ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Text("Name", weight=ft.FontWeight.BOLD, size=12), 
                            expand=True,
                            on_click=lambda _: self._apply_sort("name"),
                            on_hover=lambda e: self._on_header_hover(e)
                        ),
                        ft.Container(
                            content=ft.Text("Size", weight=ft.FontWeight.BOLD, size=11, text_align=ft.TextAlign.RIGHT), 
                            width=70, 
                            on_click=lambda _: self._apply_sort("size"),
                            on_hover=lambda e: self._on_header_hover(e)
                        ),
                        ft.Container(
                            content=ft.Text("S", weight=ft.FontWeight.BOLD, size=11, text_align=ft.TextAlign.CENTER), 
                            width=40, 
                            on_click=lambda _: self._apply_sort("seeders"),
                            on_hover=lambda e: self._on_header_hover(e),
                            tooltip="Sort by Seeds"
                        ),
                        ft.Container(
                            content=ft.Text("P", weight=ft.FontWeight.BOLD, size=11, text_align=ft.TextAlign.CENTER), 
                            width=40, 
                            on_click=lambda _: self._apply_sort("peers"),
                            on_hover=lambda e: self._on_header_hover(e),
                            tooltip="Sort by Peers"
                        ),
                        ft.Text("Source", weight=ft.FontWeight.BOLD, size=11, width=80, text_align=ft.TextAlign.CENTER),
                        ft.Container(width=130),  # Actions placeholder (matches row width)
                    ], spacing=5),
                    padding=ft.padding.only(left=10, top=8, bottom=8, right=30),
                    bgcolor=ft.Colors.GREY_200 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_800,
                    border_radius=ft.border_radius.only(top_left=5, top_right=5),
                )
                items.append(header)
            
            # Data rows
            for i, torrent in enumerate(results):
                is_dead = torrent.seeders == 0
                is_healthy = torrent.seeders >= 50
                
                if torrent.seeders == -1:
                    seed_color = ft.Colors.BLUE
                    seed_str = "?"
                    peer_str = "?"
                else:
                    seed_color = ft.Colors.RED if is_dead else (ft.Colors.GREEN if is_healthy else ft.Colors.ORANGE)
                    seed_str = str(torrent.seeders)
                    peer_str = str(torrent.peers)
                
                provider_str = torrent.provider_name if torrent.provider_name else "?"
                
                # Alternating row background
                row_bg = ft.Colors.with_opacity(0.03, ft.Colors.GREY) if i % 2 == 0 else ft.Colors.TRANSPARENT
                
                # Check if bookmarked
                is_bookmarked = self.bookmark_manager.is_bookmarked(torrent.name)
                
                row = ft.Container(
                    content=ft.Row([
                        ft.Text(torrent.name, size=12, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, tooltip=torrent.name),
                        ft.Text(torrent.size, size=11, width=70, text_align=ft.TextAlign.RIGHT, color=ft.Colors.GREY_500),
                        ft.Text(seed_str, size=11, width=40, text_align=ft.TextAlign.CENTER, color=seed_color, weight=ft.FontWeight.BOLD),
                        ft.Text(peer_str, size=11, width=40, text_align=ft.TextAlign.CENTER, color=ft.Colors.BLUE),
                        ft.Text(provider_str, size=10, width=80, text_align=ft.TextAlign.CENTER, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Row([
                            ft.IconButton(
                                ft.Icons.STAR if is_bookmarked else ft.Icons.STAR_BORDER,
                                icon_size=16, 
                                icon_color=ft.Colors.AMBER if is_bookmarked else None,
                                on_click=lambda e, t=torrent: self._toggle_bookmark(e, t), 
                                tooltip="Remove Bookmark" if is_bookmarked else "Bookmark",
                                style=ft.ButtonStyle(padding=2),
                                width=30,
                                height=30,
                            ),
                            ft.IconButton(ft.Icons.DOWNLOAD, icon_size=16, icon_color=ft.Colors.GREEN,
                                         on_click=lambda e, t=torrent: self._start_download(t), tooltip="Download",
                                         style=ft.ButtonStyle(padding=2),
                                         width=30,
                                         height=30,
                            ),
                            ft.IconButton(ft.Icons.LINK, icon_size=16, 
                                         on_click=lambda e, t=torrent: self._copy_magnet(t), tooltip="Copy Magnet",
                                         style=ft.ButtonStyle(padding=2),
                                         width=30,
                                         height=30,
                            ),
                            ft.IconButton(ft.Icons.OPEN_IN_NEW, icon_size=16, 
                                         on_click=lambda e, t=torrent: self._open_url(t), tooltip="Open Site",
                                         style=ft.ButtonStyle(padding=2),
                                         width=30,
                                         height=30,
                            ),
                        ], spacing=2, width=130),
                    ], spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.only(left=10, top=6, bottom=6, right=30),
                    bgcolor=row_bg,
                    border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.with_opacity(0.1, ft.Colors.GREY))),
                )
                items.append(row)
            
            return items
            
        except Exception as e:
            print(f"Error creating table view: {e}")
            return [ft.Container(content=ft.Text(f"Error rendering table: {e}", color=ft.Colors.RED))]

    def _rebuild_list(self, list_view, items, provider_name=None):
        """Helper to rebuild a result list with current view style and apply display limit"""
        list_view.controls.clear()
        
        # Apply filters to items (for "All" tab, apply all filters; for provider tabs, apply non-provider filters)
        if provider_name is None or provider_name == "All":
            items = self._get_filtered_results(items)
        else:
            # For provider-specific tabs, skip provider filter but apply others
            filtered = list(items)
            if self.active_category_filters:
                def matches_cat(t):
                    cn = t.category.display_name if (hasattr(t, 'category') and t.category) else "Other"
                    if cn == "Series":
                        return "TV" in self.active_category_filters or "Series" in self.active_category_filters
                    return cn in self.active_category_filters
                filtered = [t for t in filtered if matches_cat(t)]
            if self.filter_min_seeds > 0:
                filtered = [t for t in filtered if t.seeders >= self.filter_min_seeds]
            if self.filter_min_peers > 0:
                filtered = [t for t in filtered if t.peers >= self.filter_min_peers]
            if self.filter_min_size > 0:
                filtered = [t for t in filtered if self._parse_size(t.size) >= self.filter_min_size]
            if self.filter_max_size > 0:
                filtered = [t for t in filtered if self._parse_size(t.size) <= self.filter_max_size]
            items = filtered
        
        # Get the max results per provider from settings
        max_per_provider = self.settings_manager.get('max_results_per_provider', 50)
        
        # Determine which provider this is for
        if provider_name is None:
            provider_name = "All"
        
        # Get or initialize displayed count for this provider
        if provider_name not in self.displayed_count:
            self.displayed_count[provider_name] = max_per_provider
        
        # Limit items to display
        display_limit = self.displayed_count.get(provider_name, max_per_provider)
        limited_items = items[:display_limit]
        has_more = len(items) > display_limit
        
        # Set list properties based on style
        if self.current_view_style == 'table':
            list_view.spacing = 0
            list_view.padding = ft.padding.only(left=5, top=5, bottom=5, right=20)
            list_view.controls.extend(self._create_table_view(limited_items, with_header=True))
        elif self.current_view_style == 'compact':
            list_view.spacing = 3
            list_view.padding = ft.padding.only(left=5, top=5, bottom=5, right=20)
            for torrent in limited_items:
                list_view.controls.append(self._create_compact_row(torrent))
        else:
            list_view.spacing = 10
            list_view.padding = ft.padding.only(left=10, top=10, bottom=10, right=15)
            for torrent in limited_items:
                list_view.controls.append(self._create_torrent_card(torrent))
        
        # Add "Show More" button if there are more results to show
        if has_more:
            remaining = len(items) - display_limit
            show_more_btn = ft.TextButton(
                f"Show {min(remaining, max_per_provider)} more results ({remaining} remaining)",
                icon=ft.Icons.EXPAND_MORE,
                on_click=lambda e, pn=provider_name, lv=list_view, itms=items: self._show_more_results(pn, lv, itms),
            )
            list_view.controls.append(
                ft.Container(content=show_more_btn, alignment=ft.Alignment.CENTER, padding=10)
            )
        
        # Re-add load more button if needed (only for All Results list - this fetches more from providers)
        if list_view == self.all_results_list and self.load_more_btn.visible and not has_more:
             list_view.controls.append(ft.Container(content=self.load_more_btn, alignment=ft.Alignment.CENTER, padding=10))
    
    def _show_more_results(self, provider_name, list_view, all_items):
        """Show more results for a specific provider"""
        # Get the max results per provider from settings
        max_per_provider = self.settings_manager.get('max_results_per_provider', 50)
        
        # Increase the displayed count
        current_count = self.displayed_count.get(provider_name, max_per_provider)
        self.displayed_count[provider_name] = current_count + max_per_provider
        
        # Rebuild the list with the new limit
        self._rebuild_list(list_view, all_items, provider_name)
        
        try:
            list_view.update()
            self.page.update()
        except (AssertionError, Exception):
            pass

    def _on_search_tab_change(self, e):
         """Handle tab change to verify if lazy refresh is needed"""
         try:
             tab_index = self.selected_tab_index
             # Check if we need to refresh the view style for this tab
             if tab_index == 0:
                 # All tab
                 if "All" not in self.refreshed_tabs:
                     self._rebuild_list(self.all_results_list, self.current_results, "All")
                     self.refreshed_tabs.add("All")
                     try:
                         self.all_results_list.update()
                     except (Exception, AssertionError):
                         pass
             else:
                 # Provider tab
                 if tab_index < len(self.tab_names):
                     provider_name = self.tab_names[tab_index]
                     
                     if provider_name not in self.refreshed_tabs and provider_name in self.provider_tabs_map:
                          p_results = [t for t in self.current_results if t.provider_name == provider_name]
                          p_list = self.provider_tabs_map[provider_name]['list']
                          self._rebuild_list(p_list, p_results, provider_name)
                          self.refreshed_tabs.add(provider_name)
                          try:
                              p_list.update()
                          except (Exception, AssertionError):
                              pass
             
             # Ensure page reflects changes (important when called from background thread)
             try:
                 self.page.update()
             except (Exception, AssertionError):
                 pass
         except Exception as ex:
             print(f"Error in tab change: {ex}")

    def _refresh_results_view(self):
        """Refresh the results list with current view style (Lazy implementation)"""
        print(f"DEBUG _refresh_results_view: style={self.current_view_style}, results_count={len(self.current_results) if self.current_results else 0}")
        
        if not self.current_results:
            return
        
        # Increment version to cancel any pending background refresh
        self.view_refresh_version += 1
        current_version = self.view_refresh_version
        
        # 1. Reset refreshed state
        self.refreshed_tabs.clear()
        
        # 2. Rebuild ONLY active tab immediately
        try:
            active_index = self.selected_tab_index
            if active_index == 0:
                # All results tab
                self._rebuild_list(self.all_results_list, self.current_results, "All")
                self.refreshed_tabs.add("All")
                self.all_results_list.update()
            else:
                # Provider tab
                if active_index < len(self.tab_names):
                    provider_name = self.tab_names[active_index]
                    if provider_name in self.provider_tabs_map:
                        p_results = [t for t in self.current_results if t.provider_name == provider_name]
                        p_list = self.provider_tabs_map[provider_name]['list']
                        self._rebuild_list(p_list, p_results, provider_name)
                        self.refreshed_tabs.add(provider_name)
                        p_list.update()
        except Exception as e:
            print(f"Error refreshing view: {e}")
            
        try:
            self.page.update()
        except AssertionError:
            pass

        # 3. Queue background refresh for inactive tabs (pass version to check for cancellation)
        self.page.run_thread(self._process_background_refreshes, current_version)

    def _process_background_refreshes(self, version):
        """Update inactive tabs in the background to prevent lag when switching later"""
        import time
        try:
            # Small delay to let main UI settle
            time.sleep(0.3)
            
            # Check if this refresh is still valid (not superseded by a newer one)
            if version != self.view_refresh_version:
                print(f"Background refresh cancelled (version {version} < {self.view_refresh_version})")
                return
            
            # 1. Check "All" tab
            if "All" not in self.refreshed_tabs:
                 # Check version again before expensive operation
                 if version != self.view_refresh_version:
                     return
                 self._rebuild_list(self.all_results_list, self.current_results, "All")
                 self.refreshed_tabs.add("All")
                 print("Background: Refreshed 'All' tab")
            
            # 2. Check Provider tabs
            # Create a copy of keys to avoid modification issues
            provider_names = list(self.provider_tabs_map.keys())
            
            for provider_name in provider_names:
                # Check version before each tab refresh
                if version != self.view_refresh_version:
                    print(f"Background refresh cancelled during provider tabs (version {version} < {self.view_refresh_version})")
                    return
                    
                if provider_name not in self.refreshed_tabs:
                    # Filter results
                    p_results = [t for t in self.current_results if t.provider_name == provider_name]
                    # Get list control
                    if provider_name in self.provider_tabs_map:
                        p_list = self.provider_tabs_map[provider_name]['list']
                        # Rebuild
                        self._rebuild_list(p_list, p_results, provider_name)
                        self.refreshed_tabs.add(provider_name)
                        print(f"Background: Refreshed '{provider_name}' tab")
                    
                    # Yield to main thread briefly
                    time.sleep(0.02)
                    
        except Exception as e:
            print(f"Background refresh error: {e}")

    def _get_result_item(self, torrent):
        """Get the appropriate result item based on current view style"""
        if self.current_view_style == 'compact':
            return self._create_compact_row(torrent)
        else:
            return self._create_torrent_card(torrent)

    def _show_snack(self, message, is_error=False):
        """Standard snackbar implementation for SwiftSeed"""
        try:
            print(f"DEBUG _show_snack: {message}")
            snack = ft.SnackBar(
                content=ft.Text(message, color=ft.Colors.WHITE),
                bgcolor=ft.Colors.GREEN_700 if not is_error else ft.Colors.RED_700,
                duration=3000
            )
            if hasattr(self.page, 'open'):
                self.page.open(snack)
            else:
                self.page.overlay.append(snack)
                snack.open = True
            self.page.update()
        except Exception as ex:
            print(f"Snackbar failed: {ex}")

    def _ensure_magnet(self, torrent):
        """Ensure torrent has a magnet link, fetching it if necessary"""
        magnet = torrent.get_magnet_uri()
        if not magnet:
            desc_url = getattr(torrent, 'description_url', None)
            if desc_url and desc_url.startswith('http'):
                self._show_snack("Fetching magnet link from source...")
                try:
                    import requests
                    from bs4 import BeautifulSoup
                    import urllib3
                    import re
                    urllib3.disable_warnings()
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }
                    
                    resp = requests.get(desc_url, headers=headers, timeout=15, verify=False)
                    if 'nnmclub' in desc_url and resp.encoding == 'ISO-8859-1':
                        resp.encoding = 'windows-1251'
                    
                    if resp.status_code == 200:
                        magnet_found = None
                        try:
                            soup = BeautifulSoup(resp.text, 'html.parser')
                            mag = soup.select_one('a[href^="magnet:"]')
                            if mag:
                                magnet_found = mag['href']
                        except: pass
                        
                        if not magnet_found:
                            match = re.search(r'magnet:\?xt=urn:btih:[a-zA-Z0-9]{32,40}(?:&[a-zA-Z0-9_=%-]*)*', resp.text)
                            if match:
                                magnet_found = match.group(0)
                                
                        if magnet_found:
                            torrent.magnet_uri = magnet_found
                            return magnet_found
                except Exception as e:
                    print(f"On-demand fetch failed: {e}")
        return magnet

    def _start_download(self, torrent):
        """Show file selection dialog before starting download"""
        # Determine if we should show a loading dialog before starting the thread
        # (Already handled by background_add_and_poll starting with a dialog)
        
        # Create a mutable container for the download object
        download_container = {'download': None, 'error': None}
        
        def cancel_loading(e=None):
            loading_dlg.open = False
            self.page.update()
            # Remove the download if it was created
            if download_container['download']:
                self.download_manager.remove_download(download_container['download'].id, delete_files=True)

        # Show loading dialog IMMEDIATELY
        loading_dlg = ft.AlertDialog(
            title=ft.Text("Starting Download"),
            content=ft.Column([
                ft.ProgressRing(),
                ft.Text("Initializing download process... Please wait.", size=12),
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
        
        def background_add_and_poll():
            try:
                # 1. Fetch missing magnet link in background
                magnet = self._ensure_magnet(torrent)
                print(f"DEBUG background_add_and_poll: magnet fetched={bool(magnet)}")
                
                if not magnet:
                    loading_dlg.open = False
                    self.page.update()
                    # Error handled by checking final_uri below
                
                # Determine if this is a torrent file URL or magnet link
                is_torrent_file_url = bool(magnet and (magnet.startswith('http://') or magnet.startswith('https://')))
                
                # Resolve download via provider if needed (e.g. E-Hentai, Skidrow)
                resolution_error = None
                
                if hasattr(self, 'providers'):
                    provider_id = getattr(torrent, 'provider_id', None)
                    provider = next((p for p in self.providers if p.info.id == provider_id), None) if provider_id else None
                    if provider:
                        try:
                            resolved = provider.resolve_download(torrent)
                            if resolved and resolved != torrent.magnet_uri:
                                import os
                                print(f"DEBUG: Provider resolved: {resolved}")
                                if os.path.exists(resolved):
                                    torrent.file_path = resolved
                                elif resolved.startswith('magnet:') or resolved.startswith('http'):
                                    torrent.magnet_uri = resolved
                                else:
                                    resolution_error = "Provider returned invalid download link"
                            elif not resolved and not torrent.magnet_uri:
                                resolution_error = "No download link found on source page"
                        except Exception as ex:
                            print(f"Provider resolution failed: {ex}")
                            resolution_error = f"Failed to fetch download link: {str(ex)[:50]}"
                
                # Check if we have a valid URI after resolution
                final_uri = getattr(torrent, 'file_path', None) or torrent.magnet_uri
                if not final_uri or (not final_uri.startswith('magnet:') and not final_uri.startswith('http') and not os.path.exists(final_uri)):
                    loading_dlg.open = False
                    self.page.update()
                    
                    # Show error dialog with option to open source page
                    def open_source(e):
                        error_dlg.open = False
                        self.page.update()
                        if hasattr(torrent, 'description_url') and torrent.description_url:
                            webbrowser.open(torrent.description_url)
                    
                    def close_error(e):
                        error_dlg.open = False
                        self.page.update()
                    
                    error_msg = resolution_error or "No magnet link or torrent file available"
                    error_dlg = ft.AlertDialog(
                        title=ft.Row([
                            ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED, size=24),
                            ft.Text("Download Not Available", weight=ft.FontWeight.BOLD),
                        ]),
                        content=ft.Column([
                            ft.Text(error_msg, size=13),
                            ft.Container(height=10),
                            ft.Text(
                                "This torrent source may require:\n"
                                "• Manual download from the website\n"
                                "• Login/registration on the source site\n"
                                "• The torrent may no longer be available",
                                size=11,
                                color=ft.Colors.GREY_600
                            ),
                        ], tight=True),
                        actions=[
                            ft.TextButton("Open Source Page", on_click=open_source, icon=ft.Icons.OPEN_IN_NEW),
                            ft.TextButton("Close", on_click=close_error),
                        ],
                        actions_alignment=ft.MainAxisAlignment.END
                    )
                    
                    self.page.overlay.append(error_dlg)
                    error_dlg.open = True
                    self.page.update()
                    return
 
                # Add torrent (this may download .torrent file for HTTP URLs)
                print(f"DEBUG: Adding download in background thread...")
                download = self.download_manager.add_download(torrent)
                
                if not download:
                    error_msg = "Failed to download torrent file" if is_torrent_file_url else "Failed to add download"
                    download_container['error'] = error_msg
                    loading_dlg.open = False
                    self.page.update()
                    
                    # Show error dialog instead of just snackbar
                    def close_add_err(ev):
                        add_err_dlg.open = False
                        self.page.update()
                    
                    def open_source_add(ev):
                        add_err_dlg.open = False
                        self.page.update()
                        if hasattr(torrent, 'description_url') and torrent.description_url:
                            webbrowser.open(torrent.description_url)
                    
                    def retry_add(ev):
                        add_err_dlg.open = False
                        self.page.update()
                        self._start_download(torrent)
                    
                    add_err_dlg = ft.AlertDialog(
                        title=ft.Row([
                            ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED, size=24),
                            ft.Text("Download Failed", weight=ft.FontWeight.BOLD),
                        ]),
                        content=ft.Column([
                            ft.Text(error_msg, size=13),
                            ft.Container(height=10),
                            ft.Text(
                                "The torrent may be unavailable or the link is broken.\n"
                                "You can try again or download manually from the source.",
                                size=11,
                                color=ft.Colors.GREY_600
                            ),
                        ], tight=True),
                        actions=[
                            ft.TextButton("Retry", on_click=retry_add, icon=ft.Icons.REFRESH),
                            ft.TextButton("Open Source", on_click=open_source_add, icon=ft.Icons.OPEN_IN_NEW),
                            ft.TextButton("Close", on_click=close_add_err),
                        ],
                        actions_alignment=ft.MainAxisAlignment.END
                    )
                    
                    self.page.overlay.append(add_err_dlg)
                    add_err_dlg.open = True
                    self.page.update()
                    return
                
                download_container['download'] = download
                
                # Check if it's a duplicate
                if not getattr(download, 'is_newly_added', True):
                    loading_dlg.open = False
                    self.page.update()
                    self._show_snack("ℹ️ Torrent already exists in downloads")
                    download.visible = True
                    
                    # Switch to downloads tab
                    self.rail.selected_index = 3
                    class MockEvent:
                        def __init__(self, control):
                            self.control = control
                    self._on_nav_change(MockEvent(self.rail))
                    return
                
                # Hide from list until confirmed
                download.visible = False
                
                # Update dialog text
                try:
                    loading_dlg.content.controls[1].value = "Processing file list..."
                    self.page.update()
                except:
                    pass
                
                start_time = time.time()
                found = False
                
                # Check if metadata is already available (for torrent files)
                if download.has_metadata:
                    print("Metadata already available (torrent file)")
                    download.update_files()  # Ensure files are populated
                    if download.files and len(download.files) > 0:
                        found = True
                
                if not found:
                    # Give libtorrent time to start connecting
                    print("Waiting for peers and metadata...")
                    time.sleep(2)
                
                # Wait up to 180 seconds for metadata (skip if already found)
                while not found and time.time() - start_time < 180:
                    if not loading_dlg.open:
                        return

                    if download.has_metadata:
                        found = True
                        break
                    
                    try:
                        if not download.handle.is_valid():
                            loading_dlg.open = False
                            self.page.update()
                            self._show_snack("❌ Download handle became invalid. Please try again.")
                            if download_container['download']:
                                self.download_manager.remove_download(download_container['download'].id, delete_files=True)
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
                    
                    def on_confirm(selected_files, download_path=None):
                        print(f"DEBUG [on_confirm]: Called with {len(selected_files)} files, path={download_path}")
                        indices = [f['index'] for f in selected_files]
                        print(f"DEBUG [on_confirm]: Indices: {indices}")
                        
                        # Finalize download: This moves the download from temp folder to the final download folder
                        # and sets the selected files logic.
                        print(f"DEBUG [on_confirm]: Calling finalize_download with download.id={download.id}")
                        new_item = self.download_manager.finalize_download(download.id, indices, download_path=download_path)
                        print(f"DEBUG [on_confirm]: finalize_download returned: {new_item}")
                        
                        if new_item:
                            self._show_snack("Download started!")
                            # Update visibility if needed, though new item logic handles it
                        else:
                            self._show_snack("Failed to start download.")
                            return
                        
                        # Switch to downloads tab
                        self.rail.selected_index = 3
                        class MockEvent:
                            def __init__(self, control):
                                self.control = control
                        self._on_nav_change(MockEvent(self.rail))

                    def on_cancel(e):
                        # Only remove if it's not visible (meaning it was just added and not confirmed yet)
                        # If it's visible, it means it was already in the list (duplicate add attempt)
                        if not download.visible:
                            self.download_manager.remove_download(download.id, delete_files=True)
                        download_dlg.open = False
                        self.page.update()
                        
                    from ui.download_dialog import DownloadDialog
                    download_dlg = DownloadDialog(self.page, download, self.download_manager, on_confirm, on_cancel=on_cancel, files=files)
                    
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
                        self.page.run_thread(background_add_and_poll)
                    
                    def on_cancel_retry(e):
                        retry_dlg.open = False
                        self.page.update()
                        if download_container['download']:
                            self.download_manager.remove_download(download_container['download'].id, delete_files=True)
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
                print(f"Error in background_add_and_poll: {e}")
                import traceback
                traceback.print_exc()
                loading_dlg.open = False
                self.page.update()
                
                # Show error dialog to user
                def close_err_dlg(ev):
                    err_dlg.open = False
                    self.page.update()
                
                def open_source_page(ev):
                    err_dlg.open = False
                    self.page.update()
                    if hasattr(torrent, 'description_url') and torrent.description_url:
                        webbrowser.open(torrent.description_url)
                
                def retry_download(ev):
                    err_dlg.open = False
                    self.page.update()
                    # Restart the download process
                    self._start_download(torrent)
                
                error_message = str(e)[:200] if str(e) else "An unknown error occurred"
                
                err_dlg = ft.AlertDialog(
                    title=ft.Row([
                        ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED, size=24),
                        ft.Text("Download Failed", weight=ft.FontWeight.BOLD),
                    ]),
                    content=ft.Column([
                        ft.Text("Failed to start the download.", size=13),
                        ft.Container(height=5),
                        ft.Container(
                            content=ft.Text(error_message, size=11, color=ft.Colors.GREY_600, selectable=True),
                            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.RED),
                            padding=10,
                            border_radius=5,
                        ),
                        ft.Container(height=10),
                        ft.Text(
                            "You can try again or manually download from the source.",
                            size=11,
                            color=ft.Colors.GREY_500
                        ),
                    ], tight=True),
                    actions=[
                        ft.TextButton("Retry", on_click=retry_download, icon=ft.Icons.REFRESH),
                        ft.TextButton("Open Source", on_click=open_source_page, icon=ft.Icons.OPEN_IN_NEW),
                        ft.TextButton("Close", on_click=close_err_dlg),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END
                )
                
                self.page.overlay.append(err_dlg)
                err_dlg.open = True
                self.page.update()

        self.page.run_thread(background_add_and_poll)

    def _set_clipboard_data(self, data):
        """Helper to set clipboard data handling legacy, modern, and async Flet versions"""
        # 1. Modern Page.clipboard.set (Flet 0.8+, returns coroutine)
        try:
            if hasattr(self.page, "clipboard"):
                res = self.page.clipboard.set(data)
                import inspect
                if inspect.iscoroutine(res):
                    try:
                        self.page.run_task(res)
                    except:
                        # Fallback for older asyncio handle
                        import asyncio
                        import threading
                        threading.Thread(target=lambda: asyncio.run(res), daemon=True).start()
                return True
        except Exception as e:
            print(f"Modern clipboard set failed: {e}")

        # 2. Legacy Page.set_clipboard
        try:
            res = self.page.set_clipboard(data)
            import inspect
            if inspect.iscoroutine(res):
                self.page.run_task(res)
            return True
        except Exception as e:
            print(f"Legacy set_clipboard failed: {e}")
            
        return False

    def _copy_magnet(self, torrent):
        """Copies magnet link to clipboard with background fetching if needed"""
        def copy_task():
            try:
                # 1. Fetch
                magnet = self._ensure_magnet(torrent)
                
                if magnet:
                    # 2. Copy
                    if self._set_clipboard_data(magnet):
                        self._show_snack("Magnet copied")
                    else:
                        self._show_snack("Failed to copy", is_error=True)
                else:
                    self._show_snack("No magnet link found", is_error=True)
            except Exception as e:
                print(f"Copy task error: {e}")
                self._show_snack("Error copying", is_error=True)

        self.page.run_thread(copy_task)

    def _open_url(self, torrent):
        if hasattr(torrent, 'description_url') and torrent.description_url:
            webbrowser.open(torrent.description_url)
            self._show_snack("Opening in browser...")
        else:
            self._show_snack("No URL available")

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

    def _open_torrent_file(self, file_path):
        """Open a .torrent file and show the download dialog"""
        try:
            print(f"Opening torrent file: {file_path}")
            
            # Validate file exists and is a torrent
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                self._show_snack(f"File not found: {file_path}")
                return
                
            if not file_path.lower().endswith('.torrent'):
                print(f"Not a .torrent file: {file_path}")
                self._show_snack("Invalid file type. Please select a .torrent file.")
                return
            
            # Parse torrent file using libtorrent
            import libtorrent as lt
            ti = lt.torrent_info(file_path)
            
            files = []
            for i in range(ti.num_files()):
                file_entry = ti.files().at(i)
                files.append({
                    'index': i,
                    'name': file_entry.path,
                    'size': self.download_manager.format_size(file_entry.size),
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
                self.download_manager.format_size(ti.total_size())
            )
            
            def on_confirm(torrent, selected_files, download_path=None):
                # Extract indices
                indices = [f['index'] for f in selected_files]
                
                if self.download_manager.add_download(torrent, indices, download_path=download_path):
                    self._show_snack("Torrent added!")
                    # Switch to downloads tab
                    self.rail.selected_index = 3
                    class MockEvent:
                        def __init__(self, control):
                            self.control = control
                    self._on_nav_change(MockEvent(self.rail))
                else:
                    self._show_snack("Failed to add torrent")
            
            # Show dialog
            from ui.download_dialog import DownloadDialog
            dlg = DownloadDialog(self.page, torrent_obj, self.download_manager, on_confirm, files=files)
            self.page.overlay.append(dlg)
            dlg.open = True
            self.page.update()
            
        except Exception as ex:
            print(f"Error opening torrent file: {ex}")
            import traceback
            traceback.print_exc()
            self._show_snack(f"Error opening torrent file: {str(ex)}")


    # --- BOOKMARKS VIEW ---
    def _build_bookmarks_view(self):
        self.bookmarks_list = ft.ReorderableListView(
            expand=True, 
            spacing=10, 
            padding=10,
            on_reorder=self._on_bookmark_reorder,
            show_default_drag_handles=False
        )
        
        # Load bookmark view style from settings (default to card)
        self.bookmark_view_style = self.settings_manager.get('bookmark_view_style', 'card')
        
        # Helper to get button style
        def get_btn_style(is_selected):
            if is_selected:
                return ft.ButtonStyle(
                    bgcolor=ft.Colors.PRIMARY,
                    color=ft.Colors.WHITE,
                )
            else:
                return ft.ButtonStyle(
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREY),
                )
        
        # View style buttons
        self.bookmark_card_btn = ft.IconButton(
            icon=ft.Icons.VIEW_AGENDA,
            tooltip="Card View",
            icon_color=ft.Colors.WHITE if self.bookmark_view_style == 'card' else None,
            style=get_btn_style(self.bookmark_view_style == 'card'),
        )
        self.bookmark_compact_btn = ft.IconButton(
            icon=ft.Icons.VIEW_LIST,
            tooltip="Compact View",
            icon_color=ft.Colors.WHITE if self.bookmark_view_style == 'compact' else None,
            style=get_btn_style(self.bookmark_view_style == 'compact'),
        )
        
        def set_bookmark_view_style(style):
            def handler(e):
                if self.bookmark_view_style == style:
                    return
                    
                self.bookmark_view_style = style
                self.settings_manager.set('bookmark_view_style', style)
                
                self.bookmark_card_btn.style = get_btn_style(style == 'card')
                self.bookmark_card_btn.icon_color = ft.Colors.WHITE if style == 'card' else None
                self.bookmark_compact_btn.style = get_btn_style(style == 'compact')
                self.bookmark_compact_btn.icon_color = ft.Colors.WHITE if style == 'compact' else None
                
                try:
                    # Clear and update UI BEFORE rebuilding to ensure ReorderableListView fresh state
                    self.bookmarks_list.controls = []
                    self.bookmarks_list.update()
                    
                    self.bookmark_card_btn.update()
                    self.bookmark_compact_btn.update()
                except:
                    pass
                self._refresh_bookmarks()
            return handler
        
        self.bookmark_card_btn.on_click = set_bookmark_view_style('card')
        self.bookmark_compact_btn.on_click = set_bookmark_view_style('compact')
        
        bookmark_view_buttons = ft.Row([
            ft.Text("View:", size=12, color=ft.Colors.GREY_500),
            ft.Container(content=self.bookmark_card_btn, border_radius=5),
            ft.Container(content=self.bookmark_compact_btn, border_radius=5),
        ], spacing=2)
        
        # Clear all button
        self.clear_all_bookmarks_btn = ft.TextButton(
            "Clear All",
            icon=ft.Icons.DELETE_SWEEP,
            on_click=self._clear_all_bookmarks,
            style=ft.ButtonStyle(color=ft.Colors.RED_400),
        )
        
        return ft.Column(
            [
                ft.Text("Bookmarks", size=30, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.Container(expand=True),
                    bookmark_view_buttons,
                    self.clear_all_bookmarks_btn,
                ], alignment=ft.MainAxisAlignment.END),
                ft.Divider(),
                self.bookmarks_list
            ],
            expand=True
        )

    def _refresh_bookmarks(self):
        try:
            # Re-initialize explicitly if needed or at least ensure a clean slate
            self.bookmarks_list.controls = []
            bookmarks = self.bookmark_manager.get_bookmarks()
            
            if not bookmarks:
                self.bookmarks_list.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.BOOKMARK_BORDER, size=60, color=ft.Colors.GREY_600),
                            ft.Text("No bookmarks yet", size=18, weight=ft.FontWeight.BOLD),
                            ft.Text("Add torrents to your bookmarks to see them here", color=ft.Colors.GREY_500),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.Alignment.CENTER,
                        padding=100
                    )
                )
            else:
                new_controls = []
                for b in bookmarks:
                    # Safely get values
                    name = b.get('name', 'Unknown')
                    size = b.get('size', '?')
                    seeders = b.get('seeders', 0)
                    peers = b.get('peers', 0)
                    provider = b.get('provider', 'Unknown')
                    
                    # Determine health color
                    is_dead = seeders == 0
                    is_healthy = seeders >= 50
                    seed_color = ft.Colors.RED if is_dead else (ft.Colors.GREEN if is_healthy else ft.Colors.ORANGE)
                    
                    # Card View
                    if self.bookmark_view_style == 'card':
                        # Determine health color
                        is_dead = seeders == 0
                        is_healthy = seeders >= 50
                        health_color = ft.Colors.RED if is_dead else (ft.Colors.GREEN if is_healthy else ft.Colors.ORANGE)
                        
                        # Category badge
                        cat_name = b.get('category', 'Unknown') or 'Unknown'
                        category_colors = {
                            "Anime": ft.Colors.PINK_400,
                            "Movies": ft.Colors.BLUE_400,
                            "TV": ft.Colors.PURPLE_400,
                            "Series": ft.Colors.PURPLE_400,
                            "Adult": ft.Colors.RED_900,
                            "Games": "#1e3a8a",
                            "Software": ft.Colors.CYAN_400,
                            "Apps": ft.Colors.CYAN_400,
                            "Books": ft.Colors.AMBER_700,
                            "Music": ft.Colors.TEAL_400,
                            "All": ft.Colors.BLUE_GREY_600,
                            "Unknown": ft.Colors.GREY,
                        }
                        cat_color = category_colors.get(cat_name, ft.Colors.BLUE_GREY)

                        card = ft.Card(
                            content=ft.Container(
                                content=ft.Row([
                                    # Drag handle on far left
                                    ft.ReorderableDragHandle(
                                        ft.Container(
                                            content=ft.Icon(ft.Icons.DRAG_HANDLE, color=ft.Colors.GREY_500, size=20),
                                            padding=ft.padding.only(left=5, right=5)
                                        )
                                    ),
                                    # Main content column
                                    ft.Column([
                                        ft.ListTile(
                                            leading=ft.Icon(ft.Icons.DOWNLOAD, color=health_color),
                                            title=ft.Text(name, weight=ft.FontWeight.BOLD, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                                            subtitle=ft.Column([
                                                ft.Text(f"{size} • {('N/A' if seeders == -1 else seeders)} Seeds • {('N/A' if peers == -1 else peers)} Peers • {provider}"),
                                                ft.Container(
                                                    content=ft.Text(cat_name, size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                                                    bgcolor=cat_color,
                                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                                    border_radius=4
                                                )
                                            ], spacing=5),
                                            trailing=ft.IconButton(
                                                ft.Icons.DELETE,
                                                icon_size=20,
                                                icon_color=ft.Colors.RED_700,
                                                tooltip="Delete bookmark",
                                                on_click=lambda e, n=name: self._delete_bookmark(n)
                                            )
                                        ),
                                        # Action buttons at bottom right
                                        ft.Container(
                                            content=ft.Row([
                                                ft.ElevatedButton(
                                                    "Download",
                                                    icon=ft.Icons.DOWNLOAD,
                                                    on_click=lambda _, bookmark=b: self._start_bookmark_download(bookmark),
                                                    bgcolor=ft.Colors.GREEN_700,
                                                    color=ft.Colors.WHITE,
                                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                                                ),
                                                ft.OutlinedButton(
                                                    "Magnet", 
                                                    icon=ft.Icons.LINK, 
                                                    on_click=lambda _, bookmark=b: self._copy_bookmark_magnet(bookmark),
                                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                                                ),
                                                ft.OutlinedButton(
                                                    "Open Page", 
                                                    icon=ft.Icons.OPEN_IN_NEW, 
                                                    on_click=lambda _, bookmark=b: self._open_bookmark_url(bookmark),
                                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                                                ),
                                            ], alignment=ft.MainAxisAlignment.END, spacing=10),
                                            padding=ft.padding.only(right=10, bottom=10)
                                        )
                                    ], spacing=0, expand=True)
                                ], spacing=0),
                                padding=5,
                            ),
                            elevation=1,
                            key=f"card_{b.get('id', name)}"
                        )
                        new_controls.append(card)
                    
                    # Compact View
                    else:
                        compact_row = ft.Container(
                            content=ft.Row([
                                # Drag handle on far left
                                ft.ReorderableDragHandle(
                                    ft.Container(
                                        content=ft.Icon(ft.Icons.DRAG_HANDLE, color="#5f6368", size=18),
                                        padding=ft.padding.only(left=5, right=5)
                                    )
                                ),
                                # Health indicator (torrent strength)
                                ft.Container(
                                    content=ft.Icon(ft.Icons.CIRCLE, size=10, color=seed_color),
                                    width=20,
                                ),
                                # Bookmark icon
                                ft.Icon(ft.Icons.BOOKMARK_ROUNDED, color=ft.Colors.AMBER, size=18),
                                # Title (expanded to fill space)
                                ft.Text(name, size=13, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, tooltip=name),
                                # Column: Size
                                ft.Text(size, size=11, width=80, text_align=ft.TextAlign.RIGHT, color=ft.Colors.GREY_500),
                                # Column: Seeds
                                ft.Text(str(seeders), size=11, width=50, text_align=ft.TextAlign.RIGHT, color=seed_color, weight=ft.FontWeight.BOLD),
                                # Column: Provider
                                ft.Text(provider, size=11, width=120, text_align=ft.TextAlign.RIGHT, color=ft.Colors.GREY_500),
                                # Actions Row
                                ft.Row([
                                    ft.IconButton(
                                        ft.Icons.DOWNLOAD_ROUNDED,
                                        icon_size=20,
                                        icon_color=ft.Colors.GREEN_600,
                                        tooltip="Download",
                                        on_click=lambda _, bookmark=b: self._start_bookmark_download(bookmark)
                                    ),
                                    ft.IconButton(
                                        ft.Icons.LINK_ROUNDED,
                                        icon_size=20,
                                        icon_color=ft.Colors.GREY_400,
                                        tooltip="Copy Magnet",
                                        on_click=lambda _, bookmark=b: self._copy_bookmark_magnet(bookmark)
                                    ),
                                    ft.IconButton(
                                        ft.Icons.DELETE_ROUNDED,
                                        icon_size=20,
                                        icon_color=ft.Colors.RED_600,
                                        tooltip="Delete",
                                        on_click=lambda e, n=name: self._delete_bookmark(n)
                                    ),
                                ], spacing=0),
                            ], spacing=10),
                            padding=ft.padding.only(left=10, right=10, top=5, bottom=5),
                            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.GREY),
                            border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.GREY)),
                            border_radius=5,
                            margin=ft.margin.only(bottom=4),
                            key=f"compact_{b.get('id', name)}"
                        )
                        new_controls.append(compact_row)
                
                self.bookmarks_list.controls = new_controls
                        
            try:
                self.bookmarks_list.update()
                self.page.update()
            except:
                pass
        except Exception as e:
            print(f"Error refreshing bookmarks: {e}")
            import traceback
            traceback.print_exc()

    def _on_bookmark_reorder(self, e):
        """Handle drag-and-drop reordering of bookmarks"""
        try:
            # 1. Update the UI controls list
            item = self.bookmarks_list.controls.pop(e.old_index)
            self.bookmarks_list.controls.insert(e.new_index, item)
            
            # 2. Update the database in background
            def sync_db():
                self.bookmark_manager.reorder_bookmarks(e.old_index, e.new_index)
            
            self.page.run_thread(sync_db)
            
            # 3. Reflect changes in UI
            self.bookmarks_list.update()
        except Exception as ex:
            print(f"Error reordering bookmarks: {ex}")

    def _start_bookmark_download(self, bookmark):
        """Start download from a bookmark"""
        try:
            # Create a mock torrent object from bookmark data
            class BookmarkTorrent:
                def __init__(self, b):
                    self.name = b.get('name', 'Unknown')
                    self.size = b.get('size', '0 B')
                    self.seeders = b.get('seeders', 0)
                    self.peers = b.get('peers', 0)
                    self.provider_name = b.get('provider', 'Unknown')
                    self.magnet_uri = b.get('magnet_uri', '')
                    self.description_url = b.get('description_url', '')
                    # provider_id might be missing in history/bookmarks DB
                    self.provider_id = b.get('provider_id', '')
                    
                    # Extract info hash safely
                    if self.magnet_uri and 'btih:' in self.magnet_uri:
                        try:
                            self.info_hash = self.magnet_uri.split('btih:')[1].split('&')[0]
                        except:
                            self.info_hash = str(b.get('id', 'unknown'))
                    else:
                        self.info_hash = str(b.get('id', 'unknown'))
                
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
            self.page.clipboard.set(magnet)
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
            # Check all lists (All + Provider Tabs)
            lists_to_update = [self.all_results_list] + [d['list'] for d in self.provider_tabs_map.values()]
            
            for list_view in lists_to_update:
                for control in list_view.controls:
                    if hasattr(control, 'data') and hasattr(control.data, 'name') and control.data.name == name:
                        # Find the star icon button in the card and update it
                        # Card -> Container -> Column -> ListTile -> trailing (IconButton)
                        try:
                            container = control.content
                            column = container.content
                            list_tile = column.controls[0]
                            # ... (rest of search logic logic needs to be robust for different view types)
                            # Actually, let's just re-render is safer but updating icon is faster
                            # Since we have different view structures (card/compact/table), it's complex to path-find.
                            # But we did it before for Cards.
                            pass # For now, skip complex update, the user can refresh if needed or we rebuild.
                        except Exception as ex:
                            pass
            
            # Simple full result refresh is easier to maintain consistency
            if self.current_results:
                self._refresh_results_view()
            
            try:
                self.all_results_list.update()
            except:
                pass
            

            
            try:
                self._show_snack("Bookmark deleted")
            except:
                pass
        except Exception as ex:
            print(f"Delete bookmark error: {ex}")

    def _clear_all_bookmarks(self, e):
        """Clear all bookmarks with confirmation"""
        def confirm_clear(e):
            self.bookmark_manager.clear_all()
            self.bookmarked_names.clear()
            self._refresh_bookmarks()
            self._show_snack("All bookmarks cleared")
            dialog.open = False
            self.page.update()
        
        def cancel_clear(e):
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Clear All Bookmarks?"),
            content=ft.Text("This will permanently delete all your bookmarks. This action cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_clear),
                ft.TextButton("Clear All", on_click=confirm_clear, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    # --- HISTORY VIEW ---
    def _build_history_view(self):
        self.history_list = ft.ListView(expand=True, spacing=5, padding=5)
        return ft.Column(
            [
                ft.Row([
                    ft.Text("Search History", size=30, weight=ft.FontWeight.BOLD),
                    ft.IconButton(ft.Icons.DELETE_SWEEP, on_click=self._clear_history, tooltip="Clear All", icon_color=ft.Colors.RED)
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
                    alignment=ft.Alignment.CENTER,
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
            ], tight=True, spacing=3),
            value=current_theme_val,
            on_change=on_theme_change
        )

        # Built-in Provider Toggles with Category & Safety
        provider_toggles = ft.Column(spacing=3)
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
                padding=5,
                border=ft.border.all(1, ft.Colors.GREY_800),
                border_radius=8,
            )
            provider_toggles.controls.append(provider_card)

        # Custom Providers Section
        self.custom_providers_list = ft.Column(spacing=3)
        
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
                theme_selector,
                ft.Divider(),
                
                # Built-in Providers
                ft.Text("Built-in Providers", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Each provider shows: Category (content type), Safety status (safe / caution), and URL", 
                       color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400, size=11),
                provider_toggles,
                ft.Divider(),
                
                # Custom Providers
                ft.Row([
                    ft.Text("Custom Providers (Torznab)", size=20, weight=ft.FontWeight.BOLD),
                    add_provider_btn
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text("Add Jackett, Prowlarr, or other Torznab-compatible indexers", 
                       color=ft.Colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_400, size=12),
                self.custom_providers_list,
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            tight=True,
            spacing=3,
            padding=5
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
                        ], spacing=3),
                        padding=8
                    )
                )
                self.custom_providers_list.controls.append(card)
        
        self.page.update()


def main(page: ft.Page):
    # Set Windows App User Model ID for proper taskbar branding
    # This ensures Windows shows "SwiftSeed" in the taskbar jump list instead of "Flet"
    if sys.platform == 'win32':
        try:
            import ctypes
            # Set the App User Model ID to a unique identifier for SwiftSeed
            # Format: CompanyName.ProductName.SubProduct.VersionInformation
            app_id = 'SayanDey.SwiftSeed.TorrentClient.v5'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            print(f"Windows App User Model ID set to: {app_id}")
            
            # Clear the jump list to prevent Flet entries
            try:
                from comtypes import CoInitialize, CoUninitialize
                from comtypes.client import CreateObject
                
                CoInitialize()
                try:
                    # Clear recent items and custom categories from jump list
                    dest_list = CreateObject("{77f10cf0-3db5-4966-b520-b7c54fd35ed6}", interface="{92CA9DCD-5622-4bba-A805-5E9F541BD8C9}")
                    dest_list.DeleteList(None)  # Clear all jump list items
                    print("Jump list cleared")
                except Exception as e:
                    print(f"Could not clear jump list: {e}")
                finally:
                    CoUninitialize()
            except ImportError:
                print("comtypes not available, skipping jump list clear")
            


        except Exception as e:
            print(f"Failed to set App User Model ID: {e}")
    
    # Check for command line arguments (.torrent file path or magnet link)
    torrent_file = None
    magnet_link = None
    
    if len(sys.argv) > 1:
        potential_arg = sys.argv[1]
        
        # Check if it's a magnet link
        if potential_arg.lower().startswith('magnet:'):
            magnet_link = potential_arg
            print(f"Command line magnet link detected: {magnet_link[:80]}...")
        # Check if it's a valid .torrent file
        elif potential_arg.lower().endswith('.torrent') and os.path.exists(potential_arg):
            torrent_file = os.path.abspath(potential_arg)
            print(f"Command line torrent file detected: {torrent_file}")
        else:
            print(f"Invalid or non-existent argument: {potential_arg}")
    
    app = TorrentSearchApp(page, torrent_file=torrent_file, magnet_link=magnet_link)
    
    # Store global reference for instance communication
    global _app_instance
    _app_instance = app


# Global app instance reference for single instance communication
_app_instance = None

def instance_message_handler(message):
    """
    Handle messages from other instances of the application.
    Called when another instance tries to open a file or show the window.
    """
    if not _app_instance:
        return
    
    action = message.get('action')
    
    if action == 'open_torrent':
        # Another instance wants to open a torrent file
        file_path = message.get('file_path')
        if file_path and os.path.exists(file_path):
            print(f"Opening torrent from another instance: {file_path}")
            
            # Bring window to front
            _app_instance.page.window.visible = True
            _app_instance.page.window.skip_task_bar = False
            _app_instance.page.window.minimized = False
            _app_instance.is_window_visible = True
            _app_instance.page.update()
            
            # Navigate to downloads tab
            _app_instance.rail.selected_index = 3
            _app_instance._set_nav_index(3)
            
            # Open the torrent file
            _app_instance._open_torrent_file(file_path)
    
    elif action == 'open_magnet':
        # Another instance wants to open a magnet link
        magnet_link = message.get('magnet_link')
        if magnet_link and magnet_link.startswith('magnet:'):
            print(f"Opening magnet from another instance: {magnet_link[:80]}...")
            
            # Bring window to front
            _app_instance.page.window.visible = True
            _app_instance.page.window.skip_task_bar = False
            _app_instance.page.window.minimized = False
            _app_instance.is_window_visible = True
            _app_instance.page.update()
            
            # Navigate to downloads tab
            _app_instance.rail.selected_index = 3
            _app_instance._set_nav_index(3)
            
            # Open the magnet link
            _app_instance._open_magnet_link(magnet_link)
            
    elif action == 'show_window':
        # Another instance just wants to show the window
        print("Bringing window to front (requested by another instance)")
        _app_instance.page.window.visible = True
        _app_instance.page.window.skip_task_bar = False
        _app_instance.page.window.minimized = False
        _app_instance.is_window_visible = True
        _app_instance.page.update()


if __name__ == "__main__":
    # Set Windows App User Model ID BEFORE starting Flet
    if sys.platform == 'win32':
        try:
            import ctypes
            app_id = 'SayanDey.SwiftSeed.TorrentClient.v5'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            print(f"[Pre-Init] Windows App User Model ID set to: {app_id}")
        except Exception as e:
            print(f"[Pre-Init] Failed to set App User Model ID: {e}")
            
    # --- SINGLE INSTANCE CHECK ---
    try:
        from managers.single_instance_manager import SingleInstanceManager
        
        instance_manager = SingleInstanceManager("SwiftSeed", 48213)
        
        # Check if we're the primary instance
        is_primary = instance_manager.check_and_acquire()
        
        if not is_primary:
            # Another instance is running - send the file/magnet to it
            print("Another instance is already running. Sending to existing instance...")
            
            # Get argument from command line if any
            if len(sys.argv) > 1:
                arg = sys.argv[1]
                
                # Check if it's a magnet link
                if arg.lower().startswith('magnet:'):
                    print(f"Sending magnet link to existing instance: {arg[:80]}...")
                    message = {
                        'action': 'open_magnet',
                        'magnet_link': arg
                    }
                    instance_manager.send_to_primary(message)
                # Check if it's a torrent file
                elif os.path.exists(arg):
                    print(f"Sending torrent file to existing instance: {arg}")
                    message = {
                        'action': 'open_torrent',
                        'file_path': os.path.abspath(arg)
                    }
                    instance_manager.send_to_primary(message)
                else:
                    print(f"Invalid argument: {arg}")
            else:
                # Just bring the existing window to front
                message = {'action': 'show_window'}
                instance_manager.send_to_primary(message)
            
            print("Message sent to existing instance. Exiting.")
            sys.exit(0)
        
        print("This is the primary instance. Starting application...")
        
        # Set up message handler for the instance manager
        # We use the global instance_message_handler defined above
        instance_manager.check_and_acquire(on_message_callback=instance_message_handler)
        
    except Exception as e:
        print(f"Error in single instance check: {e}")
        # Continue anyway if check fails
    # -----------------------------
    
    # Start the app with explicit name configuration
    try:
        ft.app(
            target=main, 
            assets_dir="assets",
            name="SwiftSeed",
            view=ft.AppView.FLET_APP
        )
    finally:
        # Release lock when app exits
        try:
            if 'instance_manager' in locals():
                instance_manager.release()
        except:
            pass
