# Building MSIX Package for Microsoft Store

## Quick Start

The `build.bat` script now includes an option to build MSIX packages for Microsoft Store submission.

### Prerequisites

1. **Windows SDK** - Required for MSIX packaging tools
   - Download: https://developer.microsoft.com/windows/downloads/windows-sdk/
   - Required components:
     - App Certification Kit
     - Windows App SDK
   - The build script will automatically detect installed SDK versions

2. **Portable Build** - Must be built first
   - Run option 1 in `build.bat` to create portable version
   - Or ensure `dist/SwiftSeed/SwiftSeed.exe` exists

### How to Build MSIX

1. Open `build.bat`
2. Select option **[4] Build MSIX Package for Microsoft Store**
3. The script will:
   - Check for prerequisites
   - Create `msix_package` folder with proper structure
   - Copy application files from `dist/SwiftSeed`
   - Copy `AppxManifest.xml` from template
   - Copy logo assets from `store/assets` folder
   - Create `SwiftSeed.msix` package

### Output

- **Package Location**: `installer/SwiftSeed.msix`
- **Temp Folder**: `msix_package/` (used during build, can be deleted)

### Before Microsoft Store Submission

You **MUST** update the `AppxManifest.xml` in the `msix_package` folder before building:

1. **Publisher ID**: Get from Partner Center → App Identity
   ```xml
   Publisher="CN=YOUR_PUBLISHER_ID_FROM_PARTNER_CENTER"
   ```

2. **App Name**: Use your reserved name from Partner Center
   ```xml
   Name="12345YourName.SwiftSeed"
   ```

3. **Version Number**: Increment for each submission
   ```xml
   Version="2.0.0.0"
   ```

**Alternative**: Update `store/AppxManifest_TEMPLATE.xml` once, and it will be used for all future builds.

### Testing the MSIX Package

#### Method 1: Developer Mode (Recommended for Testing)

1. Enable Developer Mode:
   - Settings → Update & Security → For Developers → Developer Mode

2. Install the package:
   ```powershell
   Add-AppxPackage -Path "installer\SwiftSeed.msix"
   ```

3. Launch from Start Menu: Search for "SwiftSeed"

4. Uninstall when done testing:
   ```powershell
   Get-AppxPackage SwiftSeed* | Remove-AppxPackage
   ```

#### Method 2: Windows App Certification Kit (WACK)

Before submitting to the Store, validate your package:

```powershell
& "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\appcert.exe"
```

Or run from the Windows SDK:
1. Open "Windows App Cert Kit" from Start Menu
2. Select "Validate App Package"
3. Browse to `installer\SwiftSeed.msix`
4. Run all tests
5. Fix any issues reported

**The package MUST pass WACK validation before Store submission!**

### Submission to Microsoft Store

#### Important: No Signing Required!

- ✅ Submit the **UNSIGNED** `.msix` file
- ✅ Microsoft Store will sign it automatically
- ❌ Do NOT purchase a code signing certificate for Store submission
- ✅ Users won't need to install any certificates

#### Submission Steps

1. Go to [Partner Center](https://partner.microsoft.com/dashboard)
2. Create or select your app
3. Start a new submission
4. Upload `installer\SwiftSeed.msix` in the Packages section
5. Fill out Store listing details (can copy from `store/` folder)
6. Submit for review

### Troubleshooting

#### "Windows SDK not found"
- Install Windows SDK from the link above
- Ensure you install the x64 tools
- Default install path: `C:\Program Files (x86)\Windows Kits\10\`

#### "Portable build not found"
- Run build.bat option 1 first to create portable build
- Or build manually and ensure `dist/SwiftSeed/SwiftSeed.exe` exists

#### "Package signature is invalid" during testing
- Enable Developer Mode in Windows Settings
- This only affects testing; Store handles signing for distribution

#### "Restricted capabilities warning (runFullTrust)"
- **This is normal** for desktop applications (Win32) packaged as MSIX.
- During submission, you will be asked to provide a justification.
- **Justification to use:** "This is a full-trust Win32 desktop application packaged using the Desktop Bridge. It requires full system access to perform file operations and network communication for torrent downloading."

#### "WACK validation failed"
- Review the WACK report carefully
- Common issues:
  - Missing dependencies (DLLs)
  - Incorrect manifest values
  - App crashes on launch
- Fix issues and rebuild the package

#### "App won't launch after install"
- Check Event Viewer → Windows Logs → Application
- Ensure all DLLs are included in `dist/SwiftSeed`
- Test portable version first to verify it works

### Assets Required

The build script now **automatically creates properly sized MSIX assets** from `src/assets/icon.ico` using a PowerShell script.

The following assets are automatically generated with correct dimensions:

- `StoreLogo.png` (50x50)
- `Square150x150Logo.png` (150x150)
- `Square44x44Logo.png` (44x44)
- `Wide310x150Logo.png` (310x150)
- `SplashScreen.png` (620x300)

**How it works:**
1. The build process runs `create_msix_assets.ps1`
2. The script extracts the icon from `icon.ico`
3. It resizes the icon to each required dimension using high-quality interpolation
4. Saves properly sized PNG files to the MSIX package Assets folder

You do NOT need to manually prepare these files. The script handles everything automatically, ensuring the icons display correctly in the Windows Store and after installation.

### Build Process Details

The FUNC_BUILD_MSIX function:

1. ✅ Validates prerequisites (portable build, Windows SDK)
2. ✅ Creates clean `msix_package` directory structure
3. ✅ Copies all app files from `dist/SwiftSeed`
4. ✅ Copies and prepares `AppxManifest.xml`
5. ✅ Copies and organizes logo assets into `Assets/` folder
6. ✅ Runs `MakeAppx.exe pack` to create MSIX package
7. ✅ Reports success with package size and next steps
8. ✅ Provides detailed guidance for testing and submission

### Additional Resources

- **MSIX Documentation**: https://docs.microsoft.com/windows/msix/
- **Partner Center**: https://partner.microsoft.com/dashboard
- **Package Guide**: See `store/PACKAGE_AND_CERTIFICATE_GUIDE.md`
- **Submission Checklist**: See `store/SUBMISSION_CHECKLIST.md`
- **Store Listing**: See `store/STORE_LISTING_EN.md`

---

## Quick Reference

```batch
# Full build workflow:
1. build.bat → [1] Build Portable Version
2. build.bat → [4] Build MSIX Package
3. Update AppxManifest.xml with Partner Center details
4. Test with Add-AppxPackage
5. Validate with WACK
6. Submit to Partner Center
```

**No code signing certificate needed for Microsoft Store!** 🎉
