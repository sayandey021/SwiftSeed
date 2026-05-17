# SwiftSeed MSIX Test Signing Script (PFX Method)
# Run this on your DEVELOPER PC after building the MSIX

$ErrorActionPreference = "Stop"

Write-Host "`n=== SwiftSeed MSIX Signing ===" -ForegroundColor Cyan

# 1. Clean up any old SwiftSeed test certs
Write-Host "`n[1/6] Cleaning up old test certificates..." -ForegroundColor Yellow
Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq "CN=37E2AF47-D2FC-489C-BDC1-02C989A7B989" } | Remove-Item -Force -ErrorAction SilentlyContinue

# 2. Create a fresh self-signed certificate
Write-Host "[2/6] Creating new self-signed certificate..." -ForegroundColor Yellow
$cert = New-SelfSignedCertificate `
    -Type Custom `
    -Subject "CN=37E2AF47-D2FC-489C-BDC1-02C989A7B989" `
    -KeyUsage DigitalSignature `
    -FriendlyName "SwiftSeed Test Signing" `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")

Write-Host "   Thumbprint: $($cert.Thumbprint)" -ForegroundColor Green

# 3. Export as PFX (with private key) - required for proper MSIX signing
Write-Host "[3/6] Exporting PFX (with private key)..." -ForegroundColor Yellow
$pfxPassword = ConvertTo-SecureString -String "SwiftSeedTest123" -Force -AsPlainText
$pfxPath = Join-Path $PSScriptRoot "SwiftSeedTest.pfx"
Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $pfxPassword -Force | Out-Null
Write-Host "   Saved: $pfxPath" -ForegroundColor Green

# 4. Export .cer (public key only) - this goes to the target PC
Write-Host "[4/6] Exporting public certificate (.cer)..." -ForegroundColor Yellow
$cerPath = Join-Path $PSScriptRoot "SwiftSeedTest.cer"
Export-Certificate -Cert $cert -FilePath $cerPath -Force | Out-Null
Write-Host "   Saved: $cerPath" -ForegroundColor Green

# 5. Find SignTool and sign the MSIX using the PFX
Write-Host "[5/6] Signing MSIX package with PFX..." -ForegroundColor Yellow
$SignTool = (Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin\10.0.*\x64\signtool.exe" -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1).FullName

if (-not $SignTool) {
    Write-Error "signtool.exe not found. Install Windows SDK first."
    exit 1
}
Write-Host "   Using: $SignTool" -ForegroundColor DarkGray

$msixPath = Join-Path $PSScriptRoot "installer\SwiftSeed.msix"
if (-not (Test-Path $msixPath)) {
    Write-Error "MSIX not found at: $msixPath. Run the build first!"
    exit 1
}

# Sign using PFX file (this is the correct method for MSIX packages)
& $SignTool sign /fd SHA256 /a /f $pfxPath /p "SwiftSeedTest123" $msixPath
if ($LASTEXITCODE -ne 0) {
    Write-Error "Signing failed!"
    exit 1
}
Write-Host "   Signing succeeded!" -ForegroundColor Green

# 6. Verify
Write-Host "[6/6] Verifying signature..." -ForegroundColor Yellow
$sig = Get-AuthenticodeSignature $msixPath
Write-Host "   MSIX signed with: $($sig.SignerCertificate.Thumbprint)" -ForegroundColor Green
Write-Host "   Certificate:      $($cert.Thumbprint)" -ForegroundColor Green

if ($sig.SignerCertificate.Thumbprint -eq $cert.Thumbprint) {
    Write-Host "   MATCH!" -ForegroundColor Green
} else {
    Write-Host "   MISMATCH! Something went wrong." -ForegroundColor Red
    exit 1
}

Write-Host "`n=== DONE ===" -ForegroundColor Cyan
Write-Host "Copy these 3 files to your new PC (put them in the SAME folder):" -ForegroundColor White
Write-Host "   1. $cerPath" -ForegroundColor Yellow
Write-Host "   2. $msixPath" -ForegroundColor Yellow
Write-Host "   3. $(Join-Path $PSScriptRoot 'install_msix.ps1')" -ForegroundColor Yellow
Write-Host "`nThen on the new PC: Right-click install_msix.ps1 > Run with PowerShell (as Admin)" -ForegroundColor White
Write-Host ""
