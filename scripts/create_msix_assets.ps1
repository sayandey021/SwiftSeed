# SwiftSeed MSIX Asset Generator
# Generates properly sized PNG assets from a source .ico file

param(
    [Parameter(Mandatory=$true)]
    [string]$IconPath,
    
    [Parameter(Mandatory=$true)]
    [string]$OutputDir,
    
    [Parameter(Mandatory=$false)]
    [string]$FileIconPath = ""
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
$appSizes = @(
    @{ Size = 50;  Name = "StoreLogo.png" }
    @{ Size = 150; Name = "Square150x150Logo.png" }
    @{ Size = 44;  Name = "Square44x44Logo.png" }
    @{ Size = 310; Height = 150; Name = "Wide310x150Logo.png" }
    @{ Size = 620; Height = 300; Name = "SplashScreen.png" }
)

$fileSizes = @(
    @{ Size = 44;  Name = "FileLogo.png" }
    @{ Size = 16;  Name = "FileLogo.targetsize-16.png" }
    @{ Size = 16;  Name = "FileLogo.targetsize-16_altform-unplated.png" }
    @{ Size = 32;  Name = "FileLogo.targetsize-32.png" }
    @{ Size = 32;  Name = "FileLogo.targetsize-32_altform-unplated.png" }
    @{ Size = 44;  Name = "FileLogo.targetsize-44.png" }
    @{ Size = 44;  Name = "FileLogo.targetsize-44_altform-unplated.png" }
    @{ Size = 48;  Name = "FileLogo.targetsize-48.png" }
    @{ Size = 48;  Name = "FileLogo.targetsize-48_altform-unplated.png" }
    @{ Size = 64;  Name = "FileLogo.targetsize-64.png" }
    @{ Size = 64;  Name = "FileLogo.targetsize-64_altform-unplated.png" }
    @{ Size = 96;  Name = "FileLogo.targetsize-96.png" }
    @{ Size = 96;  Name = "FileLogo.targetsize-96_altform-unplated.png" }
    @{ Size = 256; Name = "FileLogo.targetsize-256.png" }
    @{ Size = 256; Name = "FileLogo.targetsize-256_altform-unplated.png" }
)

function Generate-Assets {
    param($SourcePath, $SizesArray)
    
    if (-not $SourcePath -or -not (Test-Path $SourcePath)) {
        return
    }
    
    # Detect file type and load accordingly
    $ext = [System.IO.Path]::GetExtension($SourcePath).ToLower()
    $icon = $null
    
    if ($ext -eq ".ico") {
        # For .ico files, try to extract the largest frame for best quality
        $icon = New-Object System.Drawing.Icon($SourcePath, 256, 256)
        $sourceImage = $icon.ToBitmap()
    } else {
        # For .png and other image formats, load directly as Bitmap
        $sourceImage = New-Object System.Drawing.Bitmap($SourcePath)
    }
    
    Write-Host "  Source image: $($sourceImage.Width) x $($sourceImage.Height) pixels" -ForegroundColor Gray
    
    foreach ($s in $SizesArray) {
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
    if ($icon) { $icon.Dispose() }
}

# Generate App Icons
Generate-Assets -SourcePath $IconPath -SizesArray $appSizes

# Generate File Icons
if ($FileIconPath) {
    Generate-Assets -SourcePath $FileIconPath -SizesArray $fileSizes
} else {
    # Fallback to main app icon for file associations if no specific file icon is provided
    Generate-Assets -SourcePath $IconPath -SizesArray $fileSizes
}

Write-Host "Done! Assets generated successfully." -ForegroundColor Green
