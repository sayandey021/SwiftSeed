# SwiftSeed MSIX Asset Generator
# Generates properly sized PNG assets from a source .ico file

param(
    [Parameter(Mandatory=$true)]
    [string]$IconPath,
    
    [Parameter(Mandatory=$true)]
    [string]$OutputDir
)

# Load System.Drawing for image manipulation
Add-Type -AssemblyName System.Drawing

if (-not (Test-Path $IconPath)) {
    Write-Error "Icon file not found at: $IconPath"
    exit 1
}

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

Write-Host "Generating MSIX assets from $IconPath to $OutputDir..." -ForegroundColor Cyan

# Define sizes required for MSIX
$sizes = @(
    @{ Size = 50;  Name = "StoreLogo.png" }
    @{ Size = 150; Name = "Square150x150Logo.png" }
    @{ Size = 44;  Name = "Square44x44Logo.png" }
    @{ Size = 310; Height = 150; Name = "Wide310x150Logo.png" }
    @{ Size = 620; Height = 300; Name = "SplashScreen.png" }
    # Added File Type logos
    @{ Size = 44;  Name = "FileLogo.png" }
    @{ Size = 16;  Name = "FileLogo.targetsize-16.png" }
    @{ Size = 32;  Name = "FileLogo.targetsize-32.png" }
    @{ Size = 44;  Name = "FileLogo.targetsize-44.png" }
    @{ Size = 256; Name = "FileLogo.targetsize-256.png" }
)

# Load the icon
$icon = New-Object System.Drawing.Icon($IconPath)
# Note: Icon.ToBitmap() usually returns the 32x32 version. 
# For better quality, we should use the largest available version from the .ico.
# In .NET, we can get specific versions or just use the whole icon if it works.
$sourceImage = $icon.ToBitmap()

foreach ($s in $sizes) {
    $width = $s.Size
    $height = if ($s.Height) { $s.Height } else { $s.Size }
    $name = $s.Name
    $targetPath = Join-Path $OutputDir $name
    
    Write-Host "  Creating $name ($width x $height)..." -ForegroundColor Yellow
    
    $bmp = New-Object System.Drawing.Bitmap($width, $height)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    
    # Calculate aspect ratio preserving fit
    $aspect = $sourceImage.Width / $sourceImage.Height
    $targetAspect = $width / $height
    
    if ($aspect -gt $targetAspect) {
        $drawW = $width
        $drawH = $width / $aspect
    } else {
        $drawH = $height
        $drawW = $height * $aspect
    }
    
    $x = ($width - $drawW) / 2
    $y = ($height - $drawH) / 2
    
    $g.Clear([System.Drawing.Color]::Transparent)
    $g.DrawImage($sourceImage, $x, $y, $drawW, $drawH)
    
    $bmp.Save($targetPath, [System.Drawing.Imaging.ImageFormat]::Png)
    
    $g.Dispose()
    $bmp.Dispose()
}

$sourceImage.Dispose()
$icon.Dispose()

Write-Host "Done! Assets generated successfully." -ForegroundColor Green
