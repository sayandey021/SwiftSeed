"""
flet_dnd.py - Native Windows OLE/COM IDropTarget Drag-and-Drop for Flet Desktop Applications.
"""

import sys
import time
import threading
import ctypes
from typing import List, Callable, Optional

IS_WINDOWS = (sys.platform == 'win32')

if IS_WINDOWS:
    import pythoncom
    import win32com.server.util
    from win32com.shell import shell
    try:
        import win32gui
        _HAS_WIN32GUI = True
    except ImportError:
        _HAS_WIN32GUI = False

# OLE Drop Effects
DROPEFFECT_NONE = 0
DROPEFFECT_COPY = 1

class FletDropTarget:
    """
    COM IDropTarget interface implementation for Flet/Flutter windows.
    """
    _com_interfaces_ = [pythoncom.IID_IDropTarget] if IS_WINDOWS else []
    _public_methods_ = ['DragEnter', 'DragOver', 'DragLeave', 'Drop']

    def __init__(self, on_drop_dispatch: Callable[[List[str]], None], is_active_callback: Optional[Callable[[], bool]] = None):
        self.on_drop_dispatch = on_drop_dispatch
        self.is_active_callback = is_active_callback

    def _is_active(self) -> bool:
        if self.is_active_callback:
            try:
                return bool(self.is_active_callback())
            except Exception as e:
                print(f"[flet_dnd] Error in is_active_callback: {e}")
                return True
        return True

    def _extract_files(self, dataObject) -> List[str]:
        files = []
        try:
            # win32con.CF_HDROP = 15
            formatetc = (15, None, pythoncom.DVASPECT_CONTENT, -1, pythoncom.TYMED_HGLOBAL)
            medium = dataObject.GetData(formatetc)
            data = medium.data
            
            if isinstance(data, bytes):
                import struct
                # DROPFILES struct is 20 bytes
                pFiles, pt_x, pt_y, fNC, fWide = struct.unpack('<IIIII', data[:20])
                file_data = data[pFiles:]
                if fWide:
                    files_str = file_data.decode('utf-16le')
                else:
                    files_str = file_data.decode('mbcs')
                # Split by null terminator and filter out empty strings
                files = [f for f in files_str.split('\0') if f]
        except Exception as e:
            print(f"[flet_dnd] Error extracting dropped files: {e}")
        return files

    def DragEnter(self, dataObject, grfKeyState, pt, pdwEffect):
        try:
            print("[flet_dnd] DragEnter fired")
            if not self._is_active():
                return DROPEFFECT_NONE
            files = self._extract_files(dataObject)
            if files:
                return DROPEFFECT_COPY
        except Exception as e:
            print(f"[flet_dnd] DragEnter error: {e}")
        return DROPEFFECT_NONE

    def DragOver(self, grfKeyState, pt, pdwEffect):
        try:
            if not self._is_active():
                return DROPEFFECT_NONE
            return DROPEFFECT_COPY
        except Exception as e:
            print(f"[flet_dnd] DragOver error: {e}")
            return DROPEFFECT_NONE

    def DragLeave(self):
        print("[flet_dnd] DragLeave fired")
        return 0

    def Drop(self, dataObject, grfKeyState, pt, pdwEffect):
        try:
            print("[flet_dnd] Drop fired")
            if not self._is_active():
                return DROPEFFECT_NONE
            files = self._extract_files(dataObject)
            if files:
                self.on_drop_dispatch(files)
                return DROPEFFECT_COPY
        except Exception as e:
            print(f"[flet_dnd] Drop error: {e}")
        return DROPEFFECT_NONE


def _find_window_hwnds(title: str) -> List[int]:
    if not IS_WINDOWS:
        return []
        
    user32 = ctypes.windll.user32
    top_hwnd = user32.FindWindowW(None, title)
    if not top_hwnd and _HAS_WIN32GUI:
        try:
            top_hwnd = win32gui.FindWindow(None, title)
        except Exception:
            pass
            
    if not top_hwnd:
        return []

    hwnds = [top_hwnd]
    flutter_hwnds = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def enum_child_callback(hwnd, lparam):
        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)
        cname = class_name.value.upper()
        hwnds.append(hwnd)
        if "FLUTTER" in cname or "VIEW" in cname:
            flutter_hwnds.append(hwnd)
        return True

    cb = WNDENUMPROC(enum_child_callback)
    user32.EnumChildWindows(top_hwnd, cb, 0)
    
    combined = flutter_hwnds + hwnds
    return list(dict.fromkeys(combined))


class FletDnD:
    def __init__(self, page, on_files_dropped: Callable[[List[str]], None], is_active_callback: Optional[Callable[[], bool]] = None):
        self.page = page
        self.on_files_dropped = on_files_dropped
        self.is_active_callback = is_active_callback
        self.registered_hwnds: List[int] = []
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        if IS_WINDOWS:
            self._start()

    def _dispatch_dropped_files(self, file_paths: List[str]):
        if not file_paths:
            return

        def _runner():
            try:
                self.on_files_dropped(file_paths)
            except Exception as e:
                print(f"[flet_dnd] Exception in on_files_dropped: {e}")

        if hasattr(self.page, "run_thread"):
            self.page.run_thread(_runner)
        elif hasattr(self.page, "call_from_thread"):
            self.page.call_from_thread(_runner)
        elif hasattr(self.page, "run_task"):
            async def _async_wrapper(): _runner()
            self.page.run_task(_async_wrapper)
        else:
            _runner()

    def _start(self):
        self._thread = threading.Thread(target=self._worker, daemon=True, name="FletDnDWorker")
        self._thread.start()

    def _worker(self):
        try:
            pythoncom.OleInitialize()
        except Exception as e:
            print(f"[flet_dnd] OleInitialize failed: {e}")
            return

        title = getattr(self.page, "title", "SwiftSeed")
        hwnds = []
        start_time = time.time()
        
        while not hwnds and (time.time() - start_time < 15.0) and not self._stop_event.is_set():
            hwnds = _find_window_hwnds(title)
            if not hwnds:
                time.sleep(0.2)

        if not hwnds:
            print(f"[flet_dnd] Could not find HWND for '{title}'")
            return

        target = FletDropTarget(
            on_drop_dispatch=self._dispatch_dropped_files,
            is_active_callback=self.is_active_callback
        )
        wrapped_target = win32com.server.util.wrap(target, pythoncom.IID_IDropTarget)

        registered = []
        for hwnd in hwnds:
            try:
                pythoncom.RevokeDragDrop(hwnd)
            except Exception:
                pass
            try:
                pythoncom.RegisterDragDrop(hwnd, wrapped_target)
                registered.append(hwnd)
                print(f"[flet_dnd] Registered on HWND: {hwnd}")
            except Exception as e:
                print(f"[flet_dnd] RegisterDragDrop failed on {hwnd}: {e}")

        self.registered_hwnds = registered

        try:
            while not self._stop_event.is_set():
                if pythoncom.PumpWaitingMessages() != 0:
                    break
                time.sleep(0.02)
        finally:
            for hwnd in self.registered_hwnds:
                try:
                    pythoncom.RevokeDragDrop(hwnd)
                except Exception:
                    pass

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)


def setup_flet_dnd(page, on_files_dropped, is_active_callback=None) -> FletDnD:
    return FletDnD(page, on_files_dropped, is_active_callback)
