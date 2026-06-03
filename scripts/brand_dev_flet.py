"""
Brand the development Flet client executable (flet.exe) with SwiftSeed's
icon, name, and description. This patches flet.exe in the Python
site-packages so the taskbar shows SwiftSeed branding during development.

Uses rcedit.exe for reliable resource patching (no pefile truncation bugs).

Usage:
    python scripts/brand_dev_flet.py
    python scripts/brand_dev_flet.py --restore
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def find_rcedit():
    """Find rcedit.exe in the scripts directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rcedit = os.path.join(base_dir, "scripts", "rcedit.exe")
    if os.path.exists(rcedit):
        return rcedit
    return None


def get_latest_cached_flet():
    """Find the latest downloaded Flet desktop client in ~/.flet/client."""
    client_dir = Path.home() / ".flet" / "client"
    if not client_dir.exists():
        return None
    
    # Find folders like flet-desktop-full-0.85.2
    versions = []
    for d in client_dir.iterdir():
        if d.is_dir() and d.name.startswith("flet-desktop-"):
            versions.append(d)
            
    if not versions:
        return None
        
    # Sort by name to get the latest
    versions.sort(key=lambda x: x.name, reverse=True)
    
    flet_exe = versions[0] / "flet" / "flet.exe"
    if flet_exe.exists():
        return flet_exe
    return None


def brand_flet_exe():
    """Create a local copy of Flet and patch it with SwiftSeed branding."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(base_dir, "src", "assets", "icon.ico")
    
    if not os.path.exists(icon_path):
        print(f"Error: Icon not found at {icon_path}")
        return False
    
    rcedit = find_rcedit()
    if not rcedit:
        print("Error: rcedit.exe not found in scripts/ directory")
        return False
        
    cached_exe = get_latest_cached_flet()
    if not cached_exe:
        print("Error: Could not find Flet client in ~/.flet/client/")
        print("Please run the app normally once so Flet can download the client.")
        return False
        
    # Create local dev client directory
    dev_client_dir = os.path.join(base_dir, ".flet_dev_client_v2")
    
    print(f"Copying Flet client from {cached_exe.parent.parent} to {dev_client_dir}...")
    if os.path.exists(dev_client_dir):
        shutil.rmtree(dev_client_dir)
        
    shutil.copytree(cached_exe.parent.parent, dev_client_dir)
    
    local_flet_exe = os.path.join(dev_client_dir, "flet", "flet.exe")
    if not os.path.exists(local_flet_exe):
        print(f"Error: Copied executable not found at {local_flet_exe}")
        return False
        
    print(f"\nPatching local dev Flet client: {local_flet_exe} ...")
    
    version_strings = {
        "ProductName": "SwiftSeed",
        "FileDescription": "SwiftSeed Torrent Client",
        "CompanyName": "Sayan Dey",
        "InternalName": "SwiftSeed",
        "OriginalFilename": "SwiftSeed.exe",
        "LegalCopyright": "Copyright (c) 2025 Sayan Dey",
    }
    
    success = True
    
    # 1. Set icon
    result = subprocess.run(
        [rcedit, local_flet_exe, "--set-icon", icon_path],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"  [OK] Icon set")
    else:
        print(f"  [WARN] Icon failed: {result.stderr.strip()}")
        success = False
    
    # 2. Set file and product version
    for ver_flag, ver_val in [
        ("--set-file-version", "2.5.0.0"),
        ("--set-product-version", "2.5.0.0"),
    ]:
        result = subprocess.run(
            [rcedit, local_flet_exe, ver_flag, ver_val],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"  [OK] {ver_flag.replace('--set-', '')}: {ver_val}")
        else:
            print(f"  [WARN] {ver_flag} failed: {result.stderr.strip()}")
    
    # 3. Set all version-info string fields
    for key, val in version_strings.items():
        result = subprocess.run(
            [rcedit, local_flet_exe, "--set-version-string", key, val],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"  [OK] {key}: {val}")
        else:
            print(f"  [WARN] {key} failed: {result.stderr.strip()}")
            success = False
    
    if success:
        print(f"\n[OK] Local dev Flet client branded as 'SwiftSeed'!")
        print("When you run `python src/main.py`, it will now use this branded client.")
        print("Note: Add .flet_dev_client_v2/ to your .gitignore")
    return success

if __name__ == "__main__":
    brand_flet_exe()
