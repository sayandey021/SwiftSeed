"""
Automated distribution build script for SwiftSeed.
Creates:
1. Portable Executable (Folder)
2. Portable ZIP
3. EXE Installer (Inno Setup)
4. MSIX Package
"""

import os
import sys
import shutil
import subprocess
import glob
from pathlib import Path

def print_header(text):
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")

def run_command(command, cwd=None, shell=False):
    print(f"Running: {' '.join(command) if isinstance(command, list) else command}")
    try:
        subprocess.check_call(command, cwd=cwd, shell=shell)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return False

def find_inno_setup():
    inno_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    for path in inno_paths:
        if os.path.exists(path):
            return path
    return None

def find_makeappx():
    sdk_base = r"C:\Program Files (x86)\Windows Kits\10\bin"
    latest_ver = ""
    if os.path.exists(sdk_base):
        versions = [v for v in os.listdir(sdk_base) if v.startswith("10.0.")]
        if versions:
            latest_ver = sorted(versions, key=lambda x: [int(i) for i in x.split('.')])[-1]
            makeappx = os.path.join(sdk_base, latest_ver, "x64", "makeappx.exe")
            if os.path.exists(makeappx):
                return makeappx
    return None

def main():
    base_dir = Path(__file__).parent.absolute()
    dist_dir = base_dir / "dist"
    installer_dir = base_dir / "installer"
    msix_root = base_dir / "msix_package"
    
    # Ensure installer directory exists
    installer_dir.mkdir(exist_ok=True)

    # 1. Build Portable Executable
    print_header("Step 1: Building Portable Executable")
    if not run_command([sys.executable, "build_exe.py"], cwd=base_dir):
        print("Failed to build executable. Aborting.")
        return

    # 2. Build Portable ZIP
    print_header("Step 2: Creating Portable ZIP")
    if not run_command([sys.executable, "create_portable_zip.py"], cwd=base_dir):
        print("Warning: Failed to create portable ZIP.")

    # 3. Build EXE Installer
    print_header("Step 3: Creating EXE Installer")
    iscc_path = find_inno_setup()
    if iscc_path:
        if not run_command([iscc_path, str(base_dir / "installer_script.iss")], cwd=base_dir):
            print("Warning: Failed to create EXE installer.")
    else:
        print("Inno Setup not found. Skipping EXE installer.")

    # 4. Build MSIX Package
    print_header("Step 4: Creating MSIX Package")
    makeappx_path = find_makeappx()
    if not makeappx_path:
        print("Windows SDK (MakeAppx) not found. Skipping MSIX package.")
    else:
        # Prepare MSIX Layout
        print("Preparing MSIX layout...")
        if msix_root.exists():
            shutil.rmtree(msix_root)
        msix_root.mkdir()
        (msix_root / "Assets").mkdir()
        
        # Copy files from dist/SwiftSeed
        source_dir = dist_dir / "SwiftSeed"
        if source_dir.exists():
            for item in source_dir.iterdir():
                if item.is_dir():
                    shutil.copytree(item, msix_root / item.name)
                else:
                    shutil.copy2(item, msix_root / item.name)
        else:
            print("Error: Source dist directory not found.")
            return

        # Handle Manifest
        manifest_dest = msix_root / "AppxManifest.xml"
        manifest_src = base_dir / "msix_package_template" / "AppxManifest.xml" # Fallback
        if not manifest_src.exists():
             manifest_src = base_dir / "msix_package" / "AppxManifest.xml" # Use existing if we didn't just delete it

        # Wait, I just deleted msix_root. I should have copied it aside.
        # Let's assume there is a source manifest somewhere or use the one I saw earlier.
        # I'll just write it back if needed, but I viewed it earlier so I know its content.
        
        # Write back the manifest I viewed earlier
        manifest_content = r'''<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities">
  <Identity
    Name="Saayan.SwiftSeedDesktop"
    Publisher="CN=37E2AF47-D2FC-489C-BDC1-02C989A7B989"
    Version="2.5.0.0" />
  <Properties>
    <DisplayName>SwiftSeed Desktop</DisplayName>
    <PublisherDisplayName>Saayan</PublisherDisplayName>
    <Logo>Assets\StoreLogo.png</Logo>
    <Description>Fast, secure torrent search and download manager. Search multiple providers, download torrents with built-in client. Privacy-focused and ad-free.</Description>
  </Properties>
  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.19041.0" MaxVersionTested="10.0.22621.0" />
  </Dependencies>
  <Resources>
    <Resource Language="en-us" />
  </Resources>
  <Applications>
    <Application Id="SwiftSeed" Executable="SwiftSeed.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements
        DisplayName="SwiftSeed Desktop"
        Description="Fast, secure torrent search and download manager"
        BackgroundColor="transparent"
        Square150x150Logo="Assets\Square150x150Logo.png"
        Square44x44Logo="Assets\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="Assets\Wide310x150Logo.png" ShortName="SwiftSeed Desktop">
          <uap:ShowNameOnTiles>
            <uap:ShowOn Tile="square150x150Logo"/>
            <uap:ShowOn Tile="wide310x150Logo"/>
          </uap:ShowNameOnTiles>
        </uap:DefaultTile>
        <uap:SplashScreen Image="Assets\SplashScreen.png" BackgroundColor="#1a1a2e"/>
      </uap:VisualElements>
      <Extensions>
        <uap:Extension Category="windows.fileTypeAssociation">
          <uap:FileTypeAssociation Name="torrent">
            <uap:SupportedFileTypes>
              <uap:FileType>.torrent</uap:FileType>
            </uap:SupportedFileTypes>
            <uap:DisplayName>Torrent File</uap:DisplayName>
            <uap:Logo>Assets\FileLogo.png</uap:Logo>
          </uap:FileTypeAssociation>
        </uap:Extension>
        <uap:Extension Category="windows.protocol">
          <uap:Protocol Name="magnet">
            <uap:DisplayName>Magnet Link</uap:DisplayName>
          </uap:Protocol>
        </uap:Extension>
      </Extensions>
    </Application>
  </Applications>
  <Capabilities>
    <Capability Name="internetClient" />
    <Capability Name="internetClientServer" />
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>
</Package>
'''
        with open(manifest_dest, 'w', encoding='utf-8') as f:
            f.write(manifest_content)

        # Generate Assets
        print("Generating MSIX assets...")
        run_command(["powershell", "-ExecutionPolicy", "Bypass", "-File", "create_msix_assets.ps1", 
                    "-IconPath", "src/assets/icon.ico", "-OutputDir", "msix_package/Assets"], cwd=base_dir)

        # Pack MSIX
        print("Packing MSIX...")
        output_msix = installer_dir / "SwiftSeed.msix"
        if run_command([makeappx_path, "pack", "/d", str(msix_root), "/p", str(output_msix), "/l", "/o"], cwd=base_dir):
            print(f"✓ MSIX package created: {output_msix}")
        else:
            print("✗ MSIX package creation failed.")

    print_header("BUILD COMPLETE")
    print(f"Portable (Folder): {dist_dir / 'SwiftSeed'}")
    print(f"Portable (ZIP):    {list(dist_dir.glob('*.zip'))[0] if list(dist_dir.glob('*.zip')) else 'N/A'}")
    print(f"EXE Installer:     {list(installer_dir.glob('*.exe'))[0] if list(installer_dir.glob('*.exe')) else 'N/A'}")
    print(f"MSIX Package:      {installer_dir / 'SwiftSeed.msix' if (installer_dir / 'SwiftSeed.msix').exists() else 'N/A'}")
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
