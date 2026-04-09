
import os
import sys

# This runtime hook runs BEFORE any other imports in the frozen app.
# It ensures DLL search paths are set up properly for libtorrent.

if os.name == 'nt' and getattr(sys, 'frozen', False):
    _base = os.path.dirname(sys.executable)
    _internal = os.path.join(_base, '_internal')
    
    _dll_dirs = [
        os.path.join(_internal, 'libtorrent'),
        _internal,
        _base,
    ]
    
    # Prepend to PATH
    _existing = os.environ.get('PATH', '')
    _new = [p for p in _dll_dirs if os.path.exists(p) and p not in _existing]
    if _new:
        os.environ['PATH'] = os.pathsep.join(_new) + os.pathsep + _existing
    
    # Register with os.add_dll_directory (Python 3.8+)
    for _d in _dll_dirs:
        if os.path.exists(_d):
            try:
                os.add_dll_directory(_d)
            except (AttributeError, OSError):
                pass
    
    # Preload critical DLLs
    import ctypes
    _critical = [
        'vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll',
        'libcrypto-3.dll', 'libssl-3.dll',
        'libcrypto-3-x64.dll', 'libssl-3-x64.dll',
        'zlib1.dll', 'zlib.dll',
    ]
    for _name in _critical:
        for _sd in _dll_dirs:
            _fp = os.path.join(_sd, _name)
            if os.path.exists(_fp):
                try:
                    ctypes.WinDLL(_fp)
                except Exception:
                    pass
                break
