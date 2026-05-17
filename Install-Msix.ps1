param (
    [Parameter(Mandatory=$true)]
    [string]$MsixPath
)

# Ensure running as Admin
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "Please run this script as Administrator to install the certificate."
    Exit
}

$MsixFullPath = Resolve-Path $MsixPath -ErrorAction Stop

Write-Host "Installing MSIX: $MsixFullPath" -ForegroundColor Cyan

Write-Host "Extracting certificate from MSIX signature..." -ForegroundColor Yellow
$cert = (Get-AuthenticodeSignature -FilePath $MsixFullPath).SignerCertificate

if ($cert -ne $null) {
    Write-Host "Found certificate. Thumbprint: $($cert.Thumbprint)"
    # Import the certificate into the TrustedPeople store
    $store = New-Object System.Security.Cryptography.X509Certificates.X509Store "TrustedPeople", "LocalMachine"
    $store.Open("ReadWrite")
    $store.Add($cert)
    $store.Close()
    Write-Host "Certificate installed to Trusted People store." -ForegroundColor Green
} else {
    Write-Warning "Could not find a valid signature on the MSIX package. The package must be signed with a self-signed certificate first."
    Exit
}

# Finally, install the MSIX package
Write-Host "Installing application package..."
Add-AppxPackage -Path $MsixFullPath
Write-Host "Installation complete!" -ForegroundColor Green
