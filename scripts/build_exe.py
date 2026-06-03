"""Build script for creating Windows executable using PyInstaller."""

import PyInstaller.__main__
import os
import sys
import glob
import shutil

# Get the directory of this script
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(base_dir, 'src')
main_file = os.path.join(src_dir, 'main.py')


def find_python_dlls():
    """Find ALL DLLs from the Python installation directory.
    
    The libtorrent .pyd was built from source and links against MSVC runtime
    DLLs from the msvc_runtime package. These include DLLs like
    msvcp140_atomic_wait.dll, vccorlib140.dll, vcruntime140_threads.dll, etc.
    that do NOT exist on fresh Windows installs. We must bundle ALL of them.
    """
    python_dir = os.path.dirname(sys.executable)
    dlls_dir = os.path.join(python_dir, 'DLLs')
    scripts_dir = os.path.join(python_dir, 'Scripts')
    
    found_dlls = set()
    search_dirs = [python_dir, dlls_dir, scripts_dir]
    
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            for f in os.listdir(search_dir):
                if f.lower().endswith('.dll'):
                    full_path = os.path.join(search_dir, f)
                    if os.path.isfile(full_path):
                        # Use lowercase name as key to avoid duplicates
                        found_dlls.add(full_path)
    
    return list(found_dlls)


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
'''
    with open(hook_path, 'w', encoding='utf-8') as f:
        f.write(hook_code)
    print(f"Created runtime hook: {hook_path}")
    return hook_path


def post_build_copy_dlls():
    """Post-build step: ensure all libtorrent DLLs are in the dist directory.
    
    The .pyd file for libtorrent dynamically links against OpenSSL and MSVC
    runtime DLLs. On fresh Windows installs these may not be present, so we
    must co-locate them with the .pyd file.
    """
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
        # Copy to BOTH _internal/ and _internal/libtorrent/
        # The .pyd needs these DLLs co-located to reliably find them
        for dst_dir in [dist_internal, dist_lt_dir]:
            dst = os.path.join(dst_dir, dll_name)
            if not os.path.exists(dst):
                shutil.copy2(dll_path, dst)
                print(f"  Copied {dll_name} to {os.path.basename(dst_dir)}/")
    
    # Copy ALL MSVC runtime DLLs into the libtorrent directory too
    # The msvc_runtime pip package installs additional DLLs that libtorrent
    # may depend on but aren't present on fresh Windows installs
    msvc_dlls = [
        'vcruntime140.dll', 'vcruntime140_1.dll', 'vcruntime140_threads.dll',
        'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',
        'msvcp140_atomic_wait.dll', 'msvcp140_codecvt_ids.dll',
        'concrt140.dll', 'vcomp140.dll', 'vcamp140.dll', 'vccorlib140.dll',
        'ucrtbase.dll',
    ]
    python_root = os.path.dirname(sys.executable)
    for dll_name in msvc_dlls:
        # Try to find in multiple locations
        for src_dir in [dist_internal, python_root, 
                        os.path.join(python_root, 'Scripts'),
                        'C:/Windows/System32']:
            src = os.path.join(src_dir, dll_name)
            if os.path.exists(src):
                # Copy to both _internal and libtorrent
                for dest_dir in [dist_internal, dist_lt_dir]:
                    dst = os.path.join(dest_dir, dll_name)
                    if not os.path.exists(dst):
                        shutil.copy2(src, dst)
                        print(f"  Copied {dll_name} to {os.path.basename(dest_dir)}/")
                break
    
    print("Post-build DLL copy complete.")

    # NEW: Dynamically resolve and copy exact PE dependencies of the .pyd
    try:
        sys.path.append(os.path.join(base_dir, 'scripts'))
        import check_dll_deps
        pyd_path = os.path.join(dist_lt_dir, '__init__.cp313-win_amd64.pyd')
        if os.path.exists(pyd_path):
            deps = check_dll_deps.get_pe_imports(pyd_path)
            print(f"Dynamic PE dependencies for .pyd: {deps}")
            
            # Search for these missing dependencies
            search_paths = [
                dist_internal, dist_lt_dir,
                python_root, os.path.join(python_root, 'DLLs'), os.path.join(python_root, 'Scripts'),
                'C:/Windows/System32', 'C:/Windows/SysWOW64',
                os.environ.get('PATH', '')
            ]
            # Flatten PATH
            flat_paths = search_paths[:-1] + search_paths[-1].split(os.pathsep)
            
            for dep in deps:
                dep_lower = dep.lower()
                if dep_lower.startswith('api-ms-') or dep_lower.startswith('ext-ms-') or dep_lower in ('kernel32.dll', 'user32.dll', 'advapi32.dll', 'ws2_32.dll', 'crypt32.dll', 'ole32.dll', 'oleaut32.dll', 'ntdll.dll'):
                    continue # Standard system DLLs
                
                # Check if already in dist_lt_dir
                if not os.path.exists(os.path.join(dist_lt_dir, dep)):
                    # Find it
                    found = False
                    for sp in flat_paths:
                        if not sp: continue
                        candidate = os.path.join(sp, dep)
                        if os.path.exists(candidate):
                            shutil.copy2(candidate, os.path.join(dist_lt_dir, dep))
                            if not os.path.exists(os.path.join(dist_internal, dep)):
                                shutil.copy2(candidate, os.path.join(dist_internal, dep))
                            print(f"  [DYNAMIC] Copied missing dependency {dep} from {sp}")
                            found = True
                            break
                    if not found:
                        print(f"  [WARNING] Could not find dynamic dependency: {dep}")
    except Exception as e:
        print(f"Error resolving dynamic dependencies: {e}")


def patch_executable_icons():
    """Patch all flet.exe copies with SwiftSeed icon and version info using rcedit.

    This fixes the taskbar right-click menu showing the Flet logo and description
    instead of SwiftSeed.  Uses rcedit.exe (Electron's resource editor) which is
    far more reliable than pefile for writing version-info strings.
    """
    icon_path = os.path.join(src_dir, "assets", "icon.ico")
    if not os.path.exists(icon_path):
        print(f"Icon not found at {icon_path}, skipping patch.")
        return

    rcedit_path = os.path.join(base_dir, "scripts", "rcedit.exe")
    if not os.path.exists(rcedit_path):
        print(f"rcedit.exe not found at {rcedit_path}, skipping patch.")
        return

    dist_dir = os.path.join(base_dir, "dist", "SwiftSeed")

    # Collect ALL flet.exe / fletd.exe files from both locations
    flet_exes = []
    for root, dirs, files in os.walk(dist_dir):
        for file in files:
            if file.lower() in ("flet.exe", "fletd.exe"):
                flet_exes.append(os.path.join(root, file))

    if not flet_exes:
        print("No Flet executables found in dist, skipping icon patch.")
        return

    print(f"Found {len(flet_exes)} Flet executable(s) to patch:")
    for exe in flet_exes:
        print(f"  {exe}")

    import subprocess

    version_strings = {
        "ProductName": "SwiftSeed",
        "FileDescription": "SwiftSeed Torrent Client",
        "CompanyName": "Sayan Dey",
        "InternalName": "SwiftSeed",
        "OriginalFilename": "SwiftSeed.exe",
        "LegalCopyright": "Copyright (c) 2025 Sayan Dey",
    }

    for flet_exe in flet_exes:
        print(f"\nPatching {flet_exe} ...")

        # 1. Set icon
        result = subprocess.run(
            [rcedit_path, flet_exe, "--set-icon", icon_path],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"  [OK] Icon set")
        else:
            print(f"  [WARN] Icon failed: {result.stderr.strip()}")

        # 2. Set file and product version
        for ver_flag, ver_val in [
            ("--set-file-version", "2.5.0.0"),
            ("--set-product-version", "2.5.0.0"),
        ]:
            result = subprocess.run(
                [rcedit_path, flet_exe, ver_flag, ver_val],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"  [OK] {ver_flag.replace('--set-', '')}: {ver_val}")
            else:
                print(f"  [WARN] {ver_flag} failed: {result.stderr.strip()}")

        # 3. Set all version-info string fields
        for key, val in version_strings.items():
            result = subprocess.run(
                [rcedit_path, flet_exe, "--set-version-string", key, val],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"  [OK] {key}: {val}")
            else:
                print(f"  [WARN] {key} failed: {result.stderr.strip()}")

        print(f"  [DONE] {os.path.basename(flet_exe)} patched")



def build_exe():
    """Build the executable using PyInstaller."""
    
    # Kill any running instances of the app to free up the dist directory
    import subprocess
    import time
    print("Terminating any running instances to release file locks...")
    processes_to_kill = [
        "SwiftSeed.exe",
        "SwiftSeedApp.exe",
        "SwiftSeedAppD.exe",
        "flet.exe",
        "fletd.exe"
    ]
    for proc in processes_to_kill:
        try:
            subprocess.run(["taskkill", "/F", "/IM", proc], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    time.sleep(1)  # Give OS time to release file locks
    
    # Copy torrent file icons from the icon directory to assets
    try:
        icon_dir = os.path.join(base_dir, "icon")
        assets_dir = os.path.join(src_dir, "assets")
        
        file_ico_src = os.path.join(icon_dir, "file.ico")
        file_png_src = os.path.join(icon_dir, "file.png")
        
        if os.path.exists(file_ico_src):
            shutil.copy2(file_ico_src, os.path.join(assets_dir, "file.ico"))
            print(f"Copied {file_ico_src} to assets.")
            
        if os.path.exists(file_png_src):
            shutil.copy2(file_png_src, os.path.join(assets_dir, "file.png"))
            print(f"Copied {file_png_src} to assets.")
    except Exception as e:
        print(f"Error copying file icons: {e}")

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
    
    # Find ALL DLLs from the Python installation to bundle
    # This includes OpenSSL, MSVC runtime (from msvc_runtime package), and others
    python_dlls = find_python_dlls()
    
    # Also explicitly search for MSVC DLLs from System32 as fallback
    python_root = os.path.dirname(sys.executable)
    msvc_dll_names = [
        'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',
        'msvcp140_atomic_wait.dll', 'msvcp140_codecvt_ids.dll',
        'vcruntime140.dll', 'vcruntime140_1.dll', 'vcruntime140_threads.dll',
        'concrt140.dll', 'vcomp140.dll', 'vcamp140.dll', 'vccorlib140.dll',
    ]
    add_binary_args = []
    
    # Add DLLs from Python installation (includes msvc_runtime package DLLs)
    bundled_names = set()
    for dll_path in python_dlls:
        dll_name = os.path.basename(dll_path)
        if dll_name.lower() not in bundled_names:
            add_binary_args.append(f'--add-binary={dll_path};_internal')
            bundled_names.add(dll_name.lower())
            print(f"Will bundle: {dll_name} from {os.path.dirname(dll_path)}")
    
    # Fallback: check System32 for any MSVC DLLs not already found
    for dll_name in msvc_dll_names:
        if dll_name.lower() not in bundled_names:
            sys32_path = os.path.join('C:/Windows/System32', dll_name)
            if os.path.exists(sys32_path):
                add_binary_args.append(f'--add-binary={sys32_path};_internal')
                bundled_names.add(dll_name.lower())
                print(f"Will bundle MSVC (System32): {dll_name}")
    
    # Clean up old build/dist
    dist_path = os.path.join(base_dir, "dist")
    build_path = os.path.join(base_dir, "build")
    
    PyInstaller.__main__.run([
        main_file,
        '--name=SwiftSeed',
        '--onedir',  # Directory structure (better for installers and Flet)
        '--noconsole',  # Hide console window for production
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
    
    # Patch flet.exe taskbar icon
    print("\nPatching executable icons...")
    patch_executable_icons()
    
    print("\n" + "="*60)
    print("Build complete!")
    print(f"Executable location: {os.path.join(base_dir, 'dist', 'SwiftSeed', 'SwiftSeed.exe')}")
    print("="*60)


if __name__ == "__main__":
    print("Building SwiftSeed executable...")
    print("This may take a few minutes...\n")
    build_exe()

