# SwiftSeed MSIX Install Script - Run on the NEW PC as Administrator
# Usage: Right-click this file > "Run with PowerShell" (as Admin)

$ErrorActionPreference = "Stop"

Write-Host "`n=== SwiftSeed MSIX Installer ===" -ForegroundColor Cyan

# Find the files (look in same directory as this script, or C:\MSIX_Test)
$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = "." }

$cerFile = Join-Path $scriptDir "SwiftSeedTest.cer"
$msixFile = Join-Path $scriptDir "SwiftSeed.msix"

if (-not (Test-Path $cerFile)) {
    $cerFile = "C:\MSIX_Test\SwiftSeedTest.cer"
}
if (-not (Test-Path $msixFile)) {
    $msixFile = "C:\MSIX_Test\SwiftSeed.msix"
}

if (-not (Test-Path $cerFile)) {
    Write-Error "Cannot find SwiftSeedTest.cer! Place it next to this script or in C:\MSIX_Test\"
    pause; exit 1
}
if (-not (Test-Path $msixFile)) {
    Write-Error "Cannot find SwiftSeed.msix! Place it next to this script or in C:\MSIX_Test\"
    pause; exit 1
}

# Step 1: Clean up any old SwiftSeed certs
Write-Host "`n[1/3] Cleaning old certificates..." -ForegroundColor Yellow
Get-ChildItem Cert:\LocalMachine\Root | Where-Object { $_.Subject -eq "CN=37E2AF47-D2FC-489C-BDC1-02C989A7B989" } | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem Cert:\LocalMachine\TrustedPeople | Where-Object { $_.Subject -eq "CN=37E2AF47-D2FC-489C-BDC1-02C989A7B989" } | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "   Done." -ForegroundColor Green

# Step 2: Install certificate into TrustedPeople
Write-Host "[2/3] Installing certificate into TrustedPeople store..." -ForegroundColor Yellow
$imported = Import-Certificate -FilePath $cerFile -CertStoreLocation "Cert:\LocalMachine\TrustedPeople"
Write-Host "   Imported: $($imported.Thumbprint)" -ForegroundColor Green

# Verify the MSIX signature matches the cert we just imported
$msixSig = Get-AuthenticodeSignature $msixFile
Write-Host "   MSIX signed with: $($msixSig.SignerCertificate.Thumbprint)" -ForegroundColor DarkGray

if ($msixSig.SignerCertificate.Thumbprint -ne $imported.Thumbprint) {
    Write-Host "   WARNING: The MSIX file was signed with a DIFFERENT certificate!" -ForegroundColor Red
    Write-Host "   Make sure you copied the LATEST SwiftSeed.msix from your developer PC!" -ForegroundColor Red
    pause; exit 1
}
Write-Host "   Certificate and MSIX thumbprints match!" -ForegroundColor Green

# Step 3: Install the MSIX
Write-Host "[3/3] Installing SwiftSeed..." -ForegroundColor Yellow
try {
    Add-AppxPackage -Path $msixFile
    Write-Host "`n=== SUCCESS! ===" -ForegroundColor Green
    Write-Host "SwiftSeed has been installed! Check your Start Menu." -ForegroundColor Green
} catch {
    Write-Host "`n=== INSTALLATION FAILED ===" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "`nTrying alternative: Developer Mode sideload..." -ForegroundColor Yellow
    Write-Host 'Please enable Developer Mode in Settings > Privacy & Security > For Developers' -ForegroundColor Yellow
    Write-Host 'Then re-run this script.' -ForegroundColor Yellow
}

Write-Host ""
pause
