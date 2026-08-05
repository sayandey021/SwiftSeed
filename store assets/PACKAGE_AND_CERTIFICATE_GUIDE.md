# Microsoft Store Package & Certificate Guide

## Understanding App Packages for Microsoft Store

### Package Types

1. **MSIX** (Recommended)
   - Modern packaging format
   - Supports Windows 10 1709+
   - Better installation experience
   - Easier updates
   - File extension: `.msix`

2. **APPX** (Legacy)
   - Older format
   - Supports Windows 8.1+
   - Being phased out
   - File extension: `.appx`

3. **MSIXBUNDLE / APPXBUNDLE**
   - Contains multiple packages for different architectures
   - File extension: `.msixbundle` or `.appxbundle`

## Creating MSIX Package for SwiftSeed

### Prerequisites

Install Windows SDK (includes required tools):
- Download: https://developer.microsoft.com/windows/downloads/windows-sdk/
- Required components: App Certification Kit, Windows App SDK

Required tools (included in Windows SDK):
- `MakeAppx.exe` - Creates MSIX packages
- `SignTool.exe` - Signs packages
- Windows App Certification Kit (WACK) - Tests packages

### Step 1: Create Package Manifest (AppxManifest.xml)

Create `AppxManifest.xml` in your package directory:

```xml
<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities">

  <Identity
    Name="SwiftSeed.TorrentSearchManager"
    Publisher="CN=YOUR_PUBLISHER_NAME"
    Version="2.0.0.0" />

  <Properties>
    <DisplayName>SwiftSeed - Torrent Search & Download Manager</DisplayName>
    <PublisherDisplayName>Sayan Dey</PublisherDisplayName>
    <Logo>Assets\StoreLogo.png</Logo>
    <Description>Fast, secure torrent search and download manager</Description>
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
        DisplayName="SwiftSeed"
        Description="Fast, secure torrent search and download manager"
        BackgroundColor="transparent"
        Square150x150Logo="Assets\Square150x150Logo.png"
        Square44x44Logo="Assets\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="Assets\Wide310x150Logo.png" />
        <uap:SplashScreen Image="Assets\SplashScreen.png" />
      </uap:VisualElements>
    </Application>
  </Applications>

  <Capabilities>
    <Capability Name="internetClient" />
    <Capability Name="internetClientServer" />
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>
</Package>
```

### Step 2: Prepare Package Directory Structure

```
PackageRoot/
├── AppxManifest.xml
├── SwiftSeed.exe
├── [All DLLs and dependencies]
├── Assets/
│   ├── StoreLogo.png (400x400)
│   ├── Square150x150Logo.png (150x150)
│   ├── Square44x44Logo.png (44x44)
│   ├── Wide310x150Logo.png (310x150)
│   └── SplashScreen.png (620x300)
└── [Other app files]
```

### Step 3: Create MSIX Package

Using MakeAppx.exe:

```powershell
# Navigate to Windows SDK bin folder
cd "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64"

# Create MSIX package
.\MakeAppx.exe pack /d "C:\Path\To\PackageRoot" /p "C:\Output\SwiftSeed.msix"
```

### Step 4: Sign the Package

#### Option A: For Microsoft Store Submission
**You DO NOT need to sign the package yourself!**
- Microsoft Store automatically re-signs packages with their certificate
- You can submit unsigned packages for Store-only distribution
- Skip to Step 5 if only submitting to Store

#### Option B: For Sideloading (Testing or Direct Distribution)
You need a code signing certificate.

##### B1: Create Self-Signed Certificate (Testing Only)

```powershell
# Create self-signed certificate
$cert = New-SelfSignedCertificate -Type Custom -Subject "CN=YOUR_NAME" `
    -KeyUsage DigitalSignature -FriendlyName "SwiftSeed Development" `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")

# Export certificate for distribution
$password = ConvertTo-SecureString -String "YourPassword" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath "SwiftSeed.pfx" -Password $password
```

##### B2: Get Commercial Certificate (Production)

For commercial distribution outside the Store, purchase a code signing certificate from:
- **DigiCert**: https://www.digicert.com/signing/code-signing-certificates
- **Sectigo**: https://sectigo.com/ssl-certificates-tls/code-signing
- **GlobalSign**: https://www.globalsign.com/en/code-signing-certificate

**Cost**: $200-400 per year
**Validation**: Requires identity verification

##### B3: Sign Package with Certificate

```powershell
# Using SignTool from Windows SDK
cd "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64"

# Sign with PFX file
.\SignTool.exe sign /fd SHA256 /a /f "C:\Path\To\SwiftSeed.pfx" `
    /p "YourPassword" "C:\Output\SwiftSeed.msix"

# Verify signature
.\SignTool.exe verify /pa "C:\Output\SwiftSeed.msix"
```

## Certificate Guide for Microsoft Store

### For Microsoft Store Submission

**DO:**
✅ Submit unsigned MSIX package
✅ Microsoft will sign with their certificate automatically
✅ Users won't need to install any certificates
✅ Automatic trust through Windows Store

**DON'T:**
❌ Don't purchase expensive certificate just for Store
❌ Don't worry about signing for Store submission
❌ Don't include your own certificate

### For Sideloading (Outside Store)

**Required:**
- Valid code signing certificate
- Users must trust the certificate (install it)
- Certificate must not be expired

**Process:**
1. Purchase code signing certificate
2. Sign MSIX package
3. Distribute signed MSIX
4. Users must install certificate first (or enable Developer Mode)

## Package Validation (WACK)

Before submission, test your package:

```powershell
# Run Windows App Certification Kit
& "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\appcert.exe" `
    -appxpackagepath "C:\Output\SwiftSeed.msix" `
    -reportoutputpath "C:\Output\WACKReport.xml"
```

This tests:
- Package integrity
- Manifest correctness
- App stability
- Security requirements
- Performance
- Windows compatibility

**Must pass WACK before Store submission!**

## Testing Your MSIX Package

### Method 1: Install and Test

```powershell
# Install package (requires signature or Developer Mode)
Add-AppxPackage -Path "C:\Output\SwiftSeed.msix"

# Test the app
# Launch from Start Menu

# Uninstall
Get-AppxPackage SwiftSeed* | Remove-AppxPackage
```

### Method 2: Developer Mode (Bypass Signature)

1. Open Settings
2. Go to "Update & Security" > "For developers"
3. Enable "Developer mode"
4. Now you can install unsigned MSIX packages for testing

## Creating Build Script

Create `build_msix.ps1`:

```powershell
# SwiftSeed MSIX Build Script

$ErrorActionPreference = "Stop"

# Configuration
$projectRoot = "C:\Path\To\SwiftSeed"
$buildOutput = "$projectRoot\dist\SwiftSeed"
$packageRoot = "$projectRoot\msix_package"
$outputPath = "$projectRoot\SwiftSeed.msix"
$sdkPath = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64"

# Step 1: Clean and prepare
Write-Host "Preparing package directory..."
Remove-Item -Path $packageRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $packageRoot -Force
New-Item -ItemType Directory -Path "$packageRoot\Assets" -Force

# Step 2: Copy app files
Write-Host "Copying application files..."
Copy-Item -Path "$buildOutput\*" -Destination $packageRoot -Recurse -Force

# Step 3: Copy assets
Write-Host "Copying logo assets..."
Copy-Item -Path "$projectRoot\store\assets\store_logo_400.png" `
    -Destination "$packageRoot\Assets\StoreLogo.png"
Copy-Item -Path "$projectRoot\store\assets\store_logo_150.png" `
    -Destination "$packageRoot\Assets\Square150x150Logo.png"
Copy-Item -Path "$projectRoot\store\assets\store_logo_44.png" `
    -Destination "$packageRoot\Assets\Square44x44Logo.png"

# Step 4: Copy manifest
Write-Host "Copying manifest..."
Copy-Item -Path "$projectRoot\AppxManifest.xml" -Destination $packageRoot

# Step 5: Create MSIX
Write-Host "Creating MSIX package..."
& "$sdkPath\MakeAppx.exe" pack /d $packageRoot /p $outputPath /l

# Step 6: Sign (if certificate available)
if (Test-Path "$projectRoot\SwiftSeed.pfx") {
    Write-Host "Signing package..."
    & "$sdkPath\SignTool.exe" sign /fd SHA256 /a /f "$projectRoot\SwiftSeed.pfx" `
        /p "YourPassword" $outputPath
}

Write-Host "✅ MSIX package created: $outputPath"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Test package: Add-AppxPackage -Path '$outputPath'"
Write-Host "2. Run WACK validation"
Write-Host "3. Submit to Microsoft Store"
```

## Submission to Microsoft Store

### What to Upload

1. **MSIX Package**
   - Your unsigned `.msix` file
   - Microsoft will re-sign it

2. **Package Specific Info**
   - Architecture: x64 (or x86, ARM64)
   - Target device family: Desktop
   - Minimum OS version: Windows 10 19041+

### Publisher Certificate

For Microsoft Store:
- Your Partner Center account has a Publisher ID
- Example: `CN=1A234567-89BC-DEF0-1234-56789ABCDEF0`
- Use this in your AppxManifest.xml `Publisher` field
- Find it in Partner Center → App Identity section

### Update Manifest Before Submission

```xml
<Identity
    Name="12345SayanDey.SwiftSeed"  <!-- From Store reservation -->
    Publisher="CN=1A234567-89BC-DEF0-1234-56789ABCDEF0"  <!-- From Partner Center -->
    Version="2.0.0.0" />
```

## Common Issues & Solutions

### Issue: "Package signature is invalid"
**Solution**: Either sign with valid cert or enable Developer Mode for testing

### Issue: "Publisher doesn't match certificate"
**Solution**: Update `Publisher` field in AppxManifest.xml to match certificate

### Issue: "WACK validation failed"
**Solution**: Review WACK report, fix issues, rebuild package

### Issue: "Missing dependencies"
**Solution**: Include all DLLs and runtime files in package

### Issue: "App won't launch after install"
**Solution**: Check logs in Event Viewer → Windows Logs → Application

## Checklist Before Submission

- [ ] AppxManifest.xml has correct Publisher ID from Partner Center
- [ ] App name matches Store reservation
- [ ] Version number is correct and incremental
- [ ] All required logo assets included
- [ ] App runs correctly when installed from MSIX
- [ ] WACK validation passes
- [ ] Package size is reasonable (< 2GB)
- [ ] All files needed for app to run are included
- [ ] Tested on clean Windows installation

## Resources

- **Windows SDK**: https://developer.microsoft.com/windows/downloads/windows-sdk/
- **MSIX Toolkit**: https://github.com/microsoft/MSIX-Toolkit
- **MSIX Documentation**: https://docs.microsoft.com/windows/msix/
- **Partner Center**: https://partner.microsoft.com/dashboard
- **Package Signing**: https://docs.microsoft.com/windows/msix/package/sign-app-package-using-signtool

---

**Summary for SwiftSeed:**

1. ✅ Build your app with PyInstaller (you already have this)
2. ✅ Create AppxManifest.xml
3. ✅ Prepare logo assets in Assets folder
4. ✅ Use MakeAppx.exe to create MSIX
5. ❌ NO NEED to sign for Store submission
6. ✅ Test with WACK
7. ✅ Submit unsigned MSIX to Microsoft Store
8. ✅ Microsoft signs and publishes

**For Store:** No certificate purchase needed!
**For Sideload:** Purchase code signing certificate ($200-400/year)
