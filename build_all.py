"""
Complete build script for SwiftSeed
Builds both portable executable and installer
"""

import os
import sys
import shutil
import subprocess

def main():
    print("="*70)
    print("  SwiftSeed Build System")
    print("="*70)
    print()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist")
    
    # Step 1: Check PyInstaller
    print("[1/4] Checking PyInstaller...")
    try:
        import PyInstaller
        print("✓ PyInstaller found")
    except ImportError:
        print("✗ PyInstaller not found")
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller installed")
    
    # Step 2: Build executable
    print("\n[2/4] Building portable executable...")
    print("This may take several minutes...\n")
    
    try:
        subprocess.check_call([sys.executable, "build_exe.py"], cwd=base_dir)
        print("✓ Executable built successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Build failed: {e}")
        return False
    
    # Step 3: Check if exe exists
    exe_path = os.path.join(dist_dir, "SwiftSeed.exe")
    if not os.path.exists(exe_path):
        print(f"✗ Executable not found at {exe_path}")
        return False
    
    print(f"✓ Portable executable: {exe_path}")
    print(f"  Size: {os.path.getsize(exe_path) / (1024*1024):.2f} MB")
    
    # Step 4: Build installer with Inno Setup
    print("\n[3/4] Building installer...")
    
    # Check if Inno Setup is installed
    inno_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    
    iscc_path = None
    for path in inno_paths:
        if os.path.exists(path):
            iscc_path = path
            break
    
    if iscc_path:
        try:
            iss_script = os.path.join(base_dir, "installer_script.iss")
            subprocess.check_call([iscc_path, iss_script])
            print("✓ Installer built successfully")
            
            installer_dir = os.path.join(base_dir, "installer")
            if os.path.exists(installer_dir):
                installer_files = [f for f in os.listdir(installer_dir) if f.endswith('.exe')]
                if installer_files:
                    installer_path = os.path.join(installer_dir, installer_files[0])
                    print(f"✓ Installer: {installer_path}")
                    print(f"  Size: {os.path.getsize(installer_path) / (1024*1024):.2f} MB")
        except subprocess.CalledProcessError as e:
            print(f"✗ Installer build failed: {e}")
    else:
        print("⚠ Inno Setup not found. Skipping installer creation.")
        print("  To create installer:")
        print("  1. Download Inno Setup from: https://jrsoftware.org/isdl.php")
        print("  2. Install it")
        print("  3. Run this script again")
    
    # Step 5: Summary
    print("\n[4/4] Build Summary")
    print("="*70)
    print("✓ Portable executable ready for distribution")
    print(f"  Location: {exe_path}")
    
    if iscc_path and os.path.exists(os.path.join(base_dir, "installer")):
        print("✓ Installer ready for distribution")
        print(f"  Location: {os.path.join(base_dir, 'installer')}")
    
    print("\n" + "="*70)
    print("  Build Complete!")
    print("="*70)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
