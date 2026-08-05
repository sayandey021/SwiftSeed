# SwiftSeed Logo Resizer
# This script creates all required Microsoft Store logo sizes from the 1240x1240 source logo

param(
    [string]$SourceLogo = "assets\store_logo_1240.png",
    [string]$OutputFolder = "assets"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SwiftSeed Logo Resizer for MS Store" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if source logo exists
if (-not (Test-Path $SourceLogo)) {
    Write-Host "Error: Source logo not found at: $SourceLogo" -ForegroundColor Red
    Write-Host "Please ensure store_logo_1240.png exists in the assets folder." -ForegroundColor Yellow
    exit 1
}

Write-Host "Found source logo: $SourceLogo" -ForegroundColor Green
Write-Host ""

# Load System.Drawing assembly for image manipulation
Add-Type -AssemblyName System.Drawing

# Define sizes to create
$sizes = @(
    @{Size = 400; Name = "store_logo_400.png"; Description = "App List Icon" }
    @{Size = 150; Name = "store_logo_150.png"; Description = "Tile Icon" }
    @{Size = 88; Name = "store_logo_88.png"; Description = "Badge Logo" }
    @{Size = 44; Name = "store_logo_44.png"; Description = "Small Tile Icon" }
)

Write-Host "Creating logo sizes..." -ForegroundColor Cyan
Write-Host ""

# Track success
$successCount = 0
$totalCount = $sizes.Count

# Create output folder if it doesn't exist
if (-not (Test-Path $OutputFolder)) {
    New-Item -ItemType Directory -Path $OutputFolder -Force | Out-Null
}

# Load source image
try {
    $sourceImage = [System.Drawing.Image]::FromFile((Resolve-Path $SourceLogo))
    
    foreach ($sizeInfo in $sizes) {
        $size = $sizeInfo.Size
        $outputName = $sizeInfo.Name
        $description = $sizeInfo.Description
        $outputPath = Join-Path $OutputFolder $outputName
        
        Write-Host "Creating $outputName - $size x $size - $description..." -ForegroundColor Yellow
        
        try {
            # Create new bitmap
            $newImage = New-Object System.Drawing.Bitmap($size, $size)
            
            # Create graphics object for high-quality resizing
            $graphics = [System.Drawing.Graphics]::FromImage($newImage)
            $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
            $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
            $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
            
            # Draw resized image
            $graphics.DrawImage($sourceImage, 0, 0, $size, $size)
            
            # Save as PNG
            $newImage.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)
            
            # Cleanup
            $graphics.Dispose()
            $newImage.Dispose()
            
            # Verify file was created
            if (Test-Path $outputPath) {
                $fileInfo = Get-Item $outputPath
                $fileSizeKB = [math]::Round($fileInfo.Length / 1024, 2)
                Write-Host "  Created successfully! Size: $fileSizeKB KB" -ForegroundColor Green
                $successCount++
            }
            else {
                Write-Host "  Failed to create file" -ForegroundColor Red
            }
        }
        catch {
            Write-Host "  Error: $_" -ForegroundColor Red
        }
        
        Write-Host ""
    }
    
    # Cleanup source image
    $sourceImage.Dispose()
}
catch {
    Write-Host "Error loading source image: $_" -ForegroundColor Red
    exit 1
}

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($successCount -eq $totalCount) {
    Write-Host "Successfully created: $successCount / $totalCount logos" -ForegroundColor Green
    Write-Host ""
    Write-Host "All logos created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Review all logos in the assets folder" -ForegroundColor White
    Write-Host "2. Test logos at actual size to ensure clarity" -ForegroundColor White
    Write-Host "3. Copy to MSIX package Assets folder when building" -ForegroundColor White
}
else {
    Write-Host "Successfully created: $successCount / $totalCount logos" -ForegroundColor Yellow
    Write-Host "Some logos failed to create. Please check errors above." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
