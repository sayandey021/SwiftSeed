
import os
import sys

# This runtime hook runs BEFORE any other imports in the frozen app.
# It ensures DLL search paths are set up properly for libtorrent.

if os.name == 'nt' and getattr(sys, 'frozen', False):
    import ctypes
    import ctypes.wintypes
    
    _base = os.path.dirname(sys.executable)
    _internal = os.path.join(_base, '_internal')
    _lt_dir = os.path.join(_internal, 'libtorrent')
    
    _dll_dirs = [_lt_dir, _internal, _base]
    
    # 1. Prepend to PATH (legacy fallback)
    _existing = os.environ.get('PATH', '')
    _new = [p for p in _dll_dirs if os.path.exists(p) and p not in _existing]
    if _new:
        os.environ['PATH'] = os.pathsep.join(_new) + os.pathsep + _existing
    
    # 2. Register with os.add_dll_directory (Python 3.8+)
    for _d in _dll_dirs:
        if os.path.exists(_d):
            try:
                os.add_dll_directory(_d)
            except (AttributeError, OSError):
                pass
    
    _k32 = ctypes.windll.kernel32
    
    # 3. SetDefaultDllDirectories -- enable user-added dirs for transitive deps
    # LOAD_LIBRARY_SEARCH_DEFAULT_DIRS (0x1000) + LOAD_LIBRARY_SEARCH_USER_DIRS (0x0400)
    try:
        _k32.SetDefaultDllDirectories(0x1000 | 0x0400)
    except Exception:
        pass
    
    # 4. SetDllDirectoryW - affects ALL LoadLibrary calls including transitive deps
    # IMPORTANT: Do NOT reset this -- it must stay active for import libtorrent
    if os.path.exists(_lt_dir):
        _k32.SetDllDirectoryW(_lt_dir)
    
    # 5. Also use kernel32.AddDllDirectory for each search dir
    try:
        _AddDll = _k32.AddDllDirectory
        _AddDll.argtypes = [ctypes.wintypes.LPCWSTR]
        _AddDll.restype = ctypes.c_void_p
        for _d in _dll_dirs:
            if os.path.exists(_d):
                _AddDll(_d)
    except Exception:
        pass
    
    # 6. Use kernel32.LoadLibraryW directly to preload DLLs
    _LoadLib = _k32.LoadLibraryW
    _LoadLib.argtypes = [ctypes.wintypes.LPCWSTR]
    _LoadLib.restype = ctypes.wintypes.HMODULE
    
    _critical = [
        'vcruntime140.dll', 'vcruntime140_1.dll', 'vcruntime140_threads.dll',
        'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',
        'msvcp140_atomic_wait.dll', 'msvcp140_codecvt_ids.dll',
        'concrt140.dll', 'vcomp140.dll', 'vcamp140.dll', 'vccorlib140.dll',
        'ucrtbase.dll',
        'libcrypto-3.dll', 'libssl-3.dll',
        'libcrypto-3-x64.dll', 'libssl-3-x64.dll',
        'zlib1.dll', 'zlib.dll', 'libffi-8.dll',
        'python313.dll', 'python3.dll',
    ]
    for _name in _critical:
        for _sd in _dll_dirs:
            _fp = os.path.join(_sd, _name)
            if os.path.exists(_fp):
                _LoadLib(_fp)
                break
    
    # 7. Preload ALL .dll files in the libtorrent directory
    if os.path.exists(_lt_dir):
        _loaded = set(n.lower() for n in _critical)
        for _f in sorted(os.listdir(_lt_dir)):
            if _f.lower().endswith('.dll') and _f.lower() not in _loaded:
                _LoadLib(os.path.join(_lt_dir, _f))
    
    # 8. Pre-load the .pyd itself so Windows resolves deps with our search order
    _pyd = os.path.join(_lt_dir, '__init__.cp313-win_amd64.pyd')
    if os.path.exists(_pyd):
        _LoadLib(_pyd)
    
    # NOTE: Do NOT reset SetDllDirectoryW here!
    # It must remain active for `import libtorrent` in torrent_manager.py
