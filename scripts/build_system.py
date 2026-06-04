import os
import sys
import subprocess
import argparse

def build_portable():
    print("\n--- Building Portable Application ---")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build_script = os.path.join(base_dir, "scripts", "build_exe.py")
    result = subprocess.run([sys.executable, build_script], cwd=base_dir)
    if result.returncode != 0:
        print("Error: Portable build failed.")
        sys.exit(1)
    print("Portable build successful.")

def build_installer():
    print("\n--- Building Windows Installer ---")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exe_path = os.path.join(base_dir, "dist", "SwiftSeed", "SwiftSeed.exe")
    if not os.path.exists(exe_path):
        print(f"Error: Portable build not found at {exe_path}. Build portable first.")
        sys.exit(1)
        
    iscc_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe"
    ]
    
    iscc = next((p for p in iscc_paths if os.path.exists(p)), None)
    if not iscc:
        print("Error: Inno Setup (ISCC.exe) not found. Install from https://jrsoftware.org/isdl.php")
        sys.exit(1)
        
    script = os.path.join(base_dir, "installer_script.iss")
    result = subprocess.run([iscc, script], cwd=base_dir)
    if result.returncode != 0:
        print("Error: Installer build failed.")
        sys.exit(1)
    print("Installer build successful.")

def build_msix():
    print("\n--- Building MSIX Package ---")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exe_path = os.path.join(base_dir, "dist", "SwiftSeed", "SwiftSeed.exe")
    if not os.path.exists(exe_path):
        print(f"Error: Portable build not found at {exe_path}. Build portable first.")
        sys.exit(1)
        
    # Run MakeAppx and powershell script logic...
    sdk_base = r"C:\Program Files (x86)\Windows Kits\10\bin"
    makeappx = None
    if os.path.exists(sdk_base):
        for folder in os.listdir(sdk_base):
            if folder.startswith("10.0."):
                candidate = os.path.join(sdk_base, folder, "x64", "MakeAppx.exe")
                if os.path.exists(candidate):
                    makeappx = candidate
                    break
                    
    if not makeappx:
        print("Error: Windows SDK MakeAppx.exe not found.")
        sys.exit(1)
        
    pkg_root = os.path.join(base_dir, "msix_package")
    pkg_assets = os.path.join(pkg_root, "Assets")
    
    if os.path.exists(pkg_root):
        import shutil
        shutil.rmtree(pkg_root)
    os.makedirs(pkg_assets)
    
    print("Copying application files...")
    subprocess.run(["xcopy", "/E", "/I", "/Y", "/Q", os.path.join(base_dir, "dist", "SwiftSeed", "*"), os.path.join(pkg_root, "")])
    
    manifest_src = os.path.join(base_dir, "..", "store", "AppxManifest_TEMPLATE.xml")
    if os.path.exists(manifest_src):
        import shutil
        shutil.copy2(manifest_src, os.path.join(pkg_root, "AppxManifest.xml"))
        
    print("Preparing assets...")
    ps_script = os.path.join(base_dir, "scripts", "create_msix_assets.ps1")
    icon_path = os.path.join(base_dir, "src", "assets", "icon.ico")
    file_icon_path = os.path.join(base_dir, "src", "assets", "file_256_preview.png")
    
    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_script, 
                   "-IconPath", icon_path, "-FileIconPath", file_icon_path, "-OutputDir", pkg_assets])
    
    # Patch flet.exe copies with SwiftSeed branding before packing
    print("Patching Flet executables in MSIX package...")
    patch_msix_flet_exes(pkg_root)
    
    out_dir = os.path.join(base_dir, "installer")
    os.makedirs(out_dir, exist_ok=True)
    out_msix = os.path.join(out_dir, "SwiftSeed.msix")
    
    print("Packing MSIX...")
    result = subprocess.run([makeappx, "pack", "/d", pkg_root, "/p", out_msix, "/l", "/o"])
    if result.returncode != 0:
        print("Error: MSIX package creation failed.")
        sys.exit(1)
    print(f"MSIX created at {out_msix}")


def patch_msix_flet_exes(pkg_root):
    """Patch all flet.exe copies inside the MSIX package root with SwiftSeed branding."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rcedit_path = os.path.join(base_dir, "scripts", "rcedit.exe")
    icon_path = os.path.join(base_dir, "src", "assets", "icon.ico")

    if not os.path.exists(rcedit_path):
        print("Warning: rcedit.exe not found, skipping MSIX branding patch.")
        return
    if not os.path.exists(icon_path):
        print("Warning: icon.ico not found, skipping MSIX branding patch.")
        return

    # Find all flet.exe / fletd.exe in the package root
    flet_exes = []
    for root, dirs, files in os.walk(pkg_root):
        for f in files:
            if f.lower() in ("flet.exe", "fletd.exe"):
                flet_exes.append(os.path.join(root, f))

    if not flet_exes:
        print("No Flet executables found in MSIX package, skipping patch.")
        return

    print(f"\nPatching {len(flet_exes)} Flet executable(s) in MSIX package...")

    version_strings = {
        "ProductName": "SwiftSeed",
        "FileDescription": "SwiftSeed Torrent Client",
        "CompanyName": "Sayan Dey",
        "InternalName": "SwiftSeed",
        "OriginalFilename": "SwiftSeed.exe",
        "LegalCopyright": "Copyright (c) 2025 Sayan Dey",
    }

    for flet_exe in flet_exes:
        print(f"  Patching {flet_exe}")
        # Icon
        subprocess.run([rcedit_path, flet_exe, "--set-icon", icon_path],
                       capture_output=True, text=True)
        # Versions
        subprocess.run([rcedit_path, flet_exe, "--set-file-version", "2.5.0.0"],
                       capture_output=True, text=True)
        subprocess.run([rcedit_path, flet_exe, "--set-product-version", "2.5.0.0"],
                       capture_output=True, text=True)
        # String fields
        for key, val in version_strings.items():
            subprocess.run([rcedit_path, flet_exe, "--set-version-string", key, val],
                           capture_output=True, text=True)
        print(f"  [OK] {os.path.basename(flet_exe)} patched")

def interactive_menu():
    while True:
        print("\n" + "="*60)
        print("                    SwiftSeed Build System")
        print("="*60)
        print("\nSelect build operation:\n")
        print("  [1] Build Portable Version Only")
        print("  [2] Build Windows Installer Only")
        print("  [3] Build EVERYTHING (Portable + Installer)")
        print("  [4] Build MSIX Package")
        print("  [5] Bump Version")
        print("  [6] Exit\n")
        
        choice = input("Enter your choice (1-6): ").strip()
        if choice == '1':
            build_portable()
        elif choice == '2':
            build_installer()
        elif choice == '3':
            build_portable()
            build_installer()
        elif choice == '4':
            build_msix()
        elif choice == '5':
            new_ver = input("Enter new version (e.g. 2.0.8): ").strip()
            if new_ver:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                bump_script = os.path.join(base_dir, "scripts", "bump_version.py")
                subprocess.run([sys.executable, bump_script, new_ver])
        elif choice == '6':
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SwiftSeed Build System")
    parser.add_argument("--portable", action="store_true", help="Build portable version")
    parser.add_argument("--installer", action="store_true", help="Build installer")
    parser.add_argument("--all", action="store_true", help="Build everything")
    parser.add_argument("--msix", action="store_true", help="Build MSIX package")
    
    args = parser.parse_args()
    
    if args.portable:
        build_portable()
    elif args.installer:
        build_installer()
    elif args.all:
        build_portable()
        build_installer()
    elif args.msix:
        build_msix()
    else:
        interactive_menu()
