"""Build script for creating Windows executable using PyInstaller."""

import PyInstaller.__main__
import os
import sys

# Get the directory of this script
base_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(base_dir, 'src')
main_file = os.path.join(src_dir, 'main.py')


def build_exe():
    """Build the executable using PyInstaller."""
    
    icon_path = os.path.join(src_dir, "assets", "icon.ico")
    
    PyInstaller.__main__.run([
        main_file,
        '--name=SwiftSeed',
        '--onefile',  # Single executable file
        '--windowed',  # No console window
        '--clean',
        # Add icon
        f'--icon={icon_path}',
        # Add src directory to Python path
        f'--paths={src_dir}',
        # Hidden imports for Flet
        '--hidden-import=flet',
        '--hidden-import=flet.matplotlib_chart',
        '--hidden-import=flet_core',
        # Hidden imports for libtorrent
        '--hidden-import=libtorrent',
        # Hidden imports for our modules
        '--hidden-import=models',
        '--hidden-import=models.category',
        '--hidden-import=models.torrent',
        '--hidden-import=models.download',
        '--hidden-import=providers',
        '--hidden-import=providers.base',
        '--hidden-import=providers.thepiratebay',
        '--hidden-import=providers.nyaa',
        '--hidden-import=providers.leet',
        '--hidden-import=providers.torrents_csv',
        '--hidden-import=providers.yts',
        '--hidden-import=storage',
        '--hidden-import=storage.bookmarks',
        '--hidden-import=storage.settings',
        '--hidden-import=storage.history',
        '--hidden-import=storage.custom_providers',
        '--hidden-import=managers',
        '--hidden-import=managers.torrent_manager',
        '--hidden-import=ui',
        '--hidden-import=ui.downloads_view',
        '--hidden-import=ui.settings_view',
        '--hidden-import=ui.download_dialog',
        # Include assets
        f'--add-data={os.path.join(src_dir, "assets")}{os.pathsep}assets',
        # Output directory
        f'--distpath={os.path.join(base_dir, "dist")}',
        f'--workpath={os.path.join(base_dir, "build")}',
        f'--specpath={base_dir}',
        # UPX compression
        '--upx-dir=upx',
    ])
    
    print("\n" + "="*60)
    print("Build complete!")
    print(f"Executable location: {os.path.join(base_dir, 'dist', 'SwiftSeed.exe')}")
    print("="*60)


if __name__ == "__main__":
    print("Building SwiftSeed executable...")
    print("This may take a few minutes...\n")
    build_exe()
