"""
Build MSIX package only (assumes dist/SwiftSeed already exists from PyInstaller build).
"""
import os
import shutil
import subprocess
from pathlib import Path

def find_makeappx():
    sdk_base = r"C:\Program Files (x86)\Windows Kits\10\bin"
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
    msix_root = base_dir / "msix_package"
    installer_dir = base_dir / "installer"
    installer_dir.mkdir(exist_ok=True)

    # Find MakeAppx
    makeappx_path = find_makeappx()
    if not makeappx_path:
        print("ERROR: Windows SDK (MakeAppx) not found!")
        return
    print(f"Found MakeAppx: {makeappx_path}")

    # Clean and recreate msix_package
    print("\n=== Preparing MSIX layout ===")
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
        print(f"Copied all items from dist/SwiftSeed")
    else:
        print("ERROR: dist/SwiftSeed not found! Run build_exe.py first.")
        return

    # Write manifest
    manifest_path = msix_root / "AppxManifest.xml"
    manifest_content = '''<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities">
  <Identity
    Name="Saayan.SwiftSeedDesktop"
    Publisher="CN=37E2AF47-D2FC-489C-BDC1-02C989A7B989"
    Version="2.0.5.0" />
  <Properties>
    <DisplayName>SwiftSeed Desktop</DisplayName>
    <PublisherDisplayName>Saayan</PublisherDisplayName>
    <Logo>Assets\\StoreLogo.png</Logo>
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
        Square150x150Logo="Assets\\Square150x150Logo.png"
        Square44x44Logo="Assets\\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="Assets\\Wide310x150Logo.png" ShortName="SwiftSeed Desktop">
          <uap:ShowNameOnTiles>
            <uap:ShowOn Tile="square150x150Logo"/>
            <uap:ShowOn Tile="wide310x150Logo"/>
          </uap:ShowNameOnTiles>
        </uap:DefaultTile>
        <uap:SplashScreen Image="Assets\\SplashScreen.png" BackgroundColor="#1a1a2e"/>
      </uap:VisualElements>
      <Extensions>
        <uap:Extension Category="windows.fileTypeAssociation">
          <uap:FileTypeAssociation Name="torrent">
            <uap:SupportedFileTypes>
              <uap:FileType>.torrent</uap:FileType>
            </uap:SupportedFileTypes>
            <uap:DisplayName>Torrent File</uap:DisplayName>
            <uap:Logo>Assets\\FileLogo.png</uap:Logo>
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
    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write(manifest_content)
    print("Manifest written (Version 2.0.5.0)")

    # Verify backgrounds are included
    bg_dir = msix_root / "_internal" / "assets" / "backgrounds"
    if bg_dir.exists():
        bgs = list(bg_dir.iterdir())
        print(f"\n=== Background images in MSIX: {len(bgs)} files ===")
        for b in bgs:
            print(f"  - {b.name} ({b.stat().st_size:,} bytes)")
    else:
        print("WARNING: No backgrounds directory found in MSIX layout!")

    # Generate MSIX tile assets
    print("\n=== Generating MSIX assets ===")
    subprocess.check_call([
        "powershell", "-ExecutionPolicy", "Bypass", "-File", "create_msix_assets.ps1",
        "-IconPath", "src/assets/icon.ico",
        "-FileIconPath", "src/assets/file_256_preview.png",
        "-OutputDir", "msix_package/Assets"
    ], cwd=base_dir)

    # Pack MSIX
    print("\n=== Packing MSIX ===")
    output_msix = installer_dir / "SwiftSeed.msix"
    try:
        subprocess.check_call([
            makeappx_path, "pack",
            "/d", str(msix_root),
            "/p", str(output_msix),
            "/l", "/o"
        ], cwd=base_dir)
        print(f"\n✓ MSIX package created: {output_msix}")
        print(f"  Size: {output_msix.stat().st_size / 1024 / 1024:.1f} MB")
    except subprocess.CalledProcessError:
        print("\n✗ MSIX package creation failed!")

if __name__ == "__main__":
    main()
