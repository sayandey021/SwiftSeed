"""Build script for creating Windows executable using PyInstaller."""

import PyInstaller.__main__
import os
import sys
import glob
import shutil

# Get the directory of this script
base_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(base_dir, 'src')
main_file = os.path.join(src_dir, 'main.py')


def find_python_dlls():
    """Find OpenSSL and other critical DLLs from the Python installation."""
    python_dir = os.path.dirname(sys.executable)
    dlls_dir = os.path.join(python_dir, 'DLLs')
    
    # DLL patterns to look for (these are needed by libtorrent's .pyd)
    dll_patterns = [
        'libcrypto*.dll',
        'libssl*.dll',
        'libffi*.dll',
        'zlib*.dll',
    ]
    
    found_dlls = []
    search_dirs = [python_dir, dlls_dir]
    
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            for pattern in dll_patterns:
                for dll_path in glob.glob(os.path.join(search_dir, pattern)):
                    if os.path.isfile(dll_path):
                        found_dlls.append(dll_path)
    
    return list(set(found_dlls))  # Remove duplicates


def find_libtorrent_package_dir():
    """Find the libtorrent package directory in site-packages."""
    try:
        import libtorrent
        return os.path.dirname(libtorrent.__file__)
    except ImportError:
        return None


def create_runtime_hook():
    """Create a runtime hook that sets up DLL directories before any imports."""
    hook_path = os.path.join(base_dir, '_runtime_hook_dlls.py')
    hook_code = '''
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
'''
    with open(hook_path, 'w') as f:
        f.write(hook_code)
    print(f"Created runtime hook: {hook_path}")
    return hook_path


def post_build_copy_dlls():
    """Post-build step: ensure all libtorrent DLLs are in the dist directory."""
    dist_lt_dir = os.path.join(base_dir, 'dist', 'SwiftSeed', '_internal', 'libtorrent')
    dist_internal = os.path.join(base_dir, 'dist', 'SwiftSeed', '_internal')
    
    if not os.path.exists(dist_lt_dir):
        os.makedirs(dist_lt_dir, exist_ok=True)
    
    # Copy DLLs from the source libtorrent package
    lt_pkg_dir = find_libtorrent_package_dir()
    if lt_pkg_dir:
        print(f"Checking libtorrent package dir: {lt_pkg_dir}")
        for f in os.listdir(lt_pkg_dir):
            if f.lower().endswith('.dll'):
                src = os.path.join(lt_pkg_dir, f)
                dst = os.path.join(dist_lt_dir, f)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    print(f"  Copied {f} to libtorrent/")
    
    # Also check for a .libs directory (some wheels store DLLs here)
    if lt_pkg_dir:
        libs_dir = os.path.join(os.path.dirname(lt_pkg_dir), 'libtorrent.libs')
        if os.path.exists(libs_dir):
            print(f"Found libtorrent.libs: {libs_dir}")
            for f in os.listdir(libs_dir):
                if f.lower().endswith('.dll'):
                    src = os.path.join(libs_dir, f)
                    # Copy to both libtorrent/ and _internal/
                    for dst_dir in [dist_lt_dir, dist_internal]:
                        dst = os.path.join(dst_dir, f)
                        if not os.path.exists(dst):
                            shutil.copy2(src, dst)
                            print(f"  Copied {f} to {os.path.basename(dst_dir)}/")
    
    # Ensure OpenSSL DLLs from the Python installation are in _internal
    python_dlls = find_python_dlls()
    for dll_path in python_dlls:
        dll_name = os.path.basename(dll_path)
        dst = os.path.join(dist_internal, dll_name)
        if not os.path.exists(dst):
            shutil.copy2(dll_path, dst)
            print(f"  Copied {dll_name} from Python installation to _internal/")
    
    print("Post-build DLL copy complete.")


def build_exe():
    """Build the executable using PyInstaller."""
    
    icon_path = os.path.join(src_dir, "assets", "icon.ico")
    
    # Create runtime hook
    runtime_hook = create_runtime_hook()
    
    # Hidden imports - ensure all dynamic imports are captured
    hidden_imports = [
        'flet',
        'flet.matplotlib_chart',
        'flet_core',
        'libtorrent',
        'win32gui',
        'win32con',
        'win32api',
        'pystray',
        'PIL',
        'PIL._imagingtk',
        'PIL._tkinter_finder',
        'comtypes',
        'comtypes.stream',
        'pywin32_system32',
    ]
    
    # Add our local modules to hidden imports just in case
    local_modules = [
        'models', 'models.category', 'models.torrent', 'models.download',
        'providers', 'providers.base', 'providers.thepiratebay', 'providers.nyaa', 
        'providers.leet', 'providers.torrents_csv', 'providers.yts', 'providers.additional',
        'storage', 'storage.bookmarks', 'storage.settings', 'storage.history', 'storage.custom_providers',
        'managers', 'managers.torrent_manager', 'managers.single_instance_manager', 'managers.file_association_manager',
        'ui', 'ui.downloads_view', 'ui.settings_view', 'ui.download_dialog'
    ]
    
    hidden_imports.extend(local_modules)
    
    # Find OpenSSL DLLs from the Python installation to bundle
    python_dlls = find_python_dlls()
    add_binary_args = [
        # MSVC runtime DLLs
        '--add-binary=C:/Windows/System32/msvcp140.dll;.',
        '--add-binary=C:/Windows/System32/vcruntime140.dll;.',
        '--add-binary=C:/Windows/System32/vcruntime140_1.dll;.',
    ]
    
    # Add Python's OpenSSL DLLs (these are needed by libtorrent .pyd)
    for dll_path in python_dlls:
        dll_name = os.path.basename(dll_path)
        add_binary_args.append(f'--add-binary={dll_path};.')
        print(f"Will bundle: {dll_name} from {dll_path}")
    
    # Clean up old build/dist
    dist_path = os.path.join(base_dir, "dist")
    build_path = os.path.join(base_dir, "build")
    
    PyInstaller.__main__.run([
        main_file,
        '--name=SwiftSeed',
        '--onedir',  # Directory structure (better for installers and Flet)
        '--windowed',  # No console window
        '--clean',
        '--noconfirm',  # Overwrite output directory without asking
        # Add icon
        f'--icon={icon_path}',
        # Add src directory to Python path
        f'--paths={src_dir}',
        # Collect everything for critical packages
        '--collect-all=flet',
        '--collect-all=pystray',
        '--collect-all=libtorrent',
        # Runtime hook to set up DLL paths before any imports
        f'--runtime-hook={runtime_hook}',
        # Hidden imports
        *[f'--hidden-import={imp}' for imp in hidden_imports],
        # Include assets
        f'--add-data={os.path.join(src_dir, "assets")}{os.pathsep}assets',
        # Output directory
        f'--distpath={dist_path}',
        f'--workpath={build_path}',
        f'--specpath={base_dir}',
        # Include DLLs
        *add_binary_args,
        # Add version info
        f'--version-file={os.path.join(base_dir, "version_info.txt")}',
    ])
    
    # Post-build: copy any missing DLLs
    print("\nRunning post-build DLL check...")
    post_build_copy_dlls()
    
    print("\n" + "="*60)
    print("Build complete!")
    print(f"Executable location: {os.path.join(base_dir, 'dist', 'SwiftSeed', 'SwiftSeed.exe')}")
    print("="*60)


if __name__ == "__main__":
    print("Building SwiftSeed executable...")
    print("This may take a few minutes...\n")
    build_exe()

