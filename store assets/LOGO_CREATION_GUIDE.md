# Microsoft Store Logo Creation Guide

## Required Logo Sizes

Microsoft Store requires app icons in multiple sizes. Below are the specifications and how to create them.

### Required Sizes

1. **Store Logo** (1240 x 1240 pixels)
   - Purpose: Primary store listing image
   - Format: PNG with transparency
   - Use: Large store page display
   - ✅ Created: `store_logo_1240.png`

2. **App List Icon** (400 x 400 pixels)
   - Purpose: App list and search results
   - Format: PNG with transparency
   - Use: Medium-sized app display

3. **Tile Icon** (150 x 150 pixels)
   - Purpose: Windows tile and icon
   - Format: PNG with transparency
   - Use: App tile, task manager

4. **Small Tile** (44 x 44 pixels)
   - Purpose: Small icon display
   - Format: PNG with transparency
   - Use: Notifications, system icons

5. **Badge Logo** (88 x 88 pixels) - Optional
   - Purpose: Lock screen badge
   - Format: PNG with transparency
   - Use: Lock screen notifications

## How to Create Smaller Sizes

### Option 1: Using PowerShell (Automated)
Create a PowerShell script to resize the 1240x1240 logo:

```powershell
# save as resize_logos.ps1
Add-Type -AssemblyName System.Drawing

$sourcePath = "store_logo_1240.png"
$sizes = @(400, 150, 88, 44)

foreach ($size in $sizes) {
    $outputPath = "store_logo_$size.png"
    
    $source = [System.Drawing.Image]::FromFile((Resolve-Path $sourcePath))
    $dest = New-Object System.Drawing.Bitmap($size, $size)
    $graphics = [System.Drawing.Graphics]::FromImage($dest)
    
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $graphics.DrawImage($source, 0, 0, $size, $size)
    
    $dest.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)
    
    $graphics.Dispose()
    $dest.Dispose()
    $source.Dispose()
    
    Write-Host "Created $outputPath"
}
```

Run: `powershell -ExecutionPolicy Bypass -File resize_logos.ps1`

### Option 2: Using Paint 3D (Manual)
1. Open `store_logo_1240.png` in Paint 3D
2. Click "Canvas"
3. Uncheck "Lock aspect ratio"
4. Set width and height to desired size (e.g., 400 x 400)
5. Click "Resize"
6. Save as PNG with new name

### Option 3: Using Online Tools
1. Go to: https://www.iloveimg.com/resize-image
2. Upload `store_logo_1240.png`
3. Set dimensions (maintain aspect ratio)
4. Download resized image
5. Repeat for each required size

### Option 4: Using GIMP (Free Software)
1. Open image in GIMP
2. Image → Scale Image
3. Set Width & Height to desired size
4. Set "Interpolation" to "Cubic" for best quality
5. Click "Scale"
6. Export as PNG

## Logo Design Guidelines

### Do's ✅
- Use transparent background
- Maintain consistent design across all sizes
- Ensure logo is recognizable at 44x44 pixels
- Use vibrant, distinguishable colors
- Keep design simple and clean
- Center the main icon element
- Test visibility in both light and dark themes

### Don'ts ❌
- Don't include text (too small at smaller sizes)
- Don't use overly complex details
- Don't use very thin lines (invisible at small sizes)
- Don't make background opaque
- Don't violate Microsoft's branding guidelines
- Don't use copyrighted elements

## File Naming Convention

Save your logos with these names:
- `store_logo_1240.png` - 1240x1240
- `store_logo_400.png` - 400x400
- `store_logo_150.png` - 150x150
- `store_logo_88.png` - 88x88
- `store_logo_44.png` - 44x44

## Quality Checklist

Before submitting, verify each logo:
- [ ] Correct dimensions
- [ ] PNG format with transparency
- [ ] File size under 2MB
- [ ] No artifacts or pixelation
- [ ] Visible and recognizable at actual size
- [ ] Consistent design across all sizes
- [ ] Tested on both light and dark backgrounds

## Current Assets

✅ **Created:**
- `store_logo_1240.png` - Primary store logo (1240x1240)
- `store_hero_image.png` - Hero banner for store page (1920x1080)

📋 **To Create:**
- `store_logo_400.png` - 400x400
- `store_logo_150.png` - 150x150
- `store_logo_88.png` - 88x88
- `store_logo_44.png` - 44x44

## Additional Store Assets

### Hero Image (Created)
- **File**: `store_hero_image.png`
- **Size**: 1920 x 1080 pixels
- **Purpose**: Store page header/featured image
- **Status**: ✅ Created

### Promotional Image (Optional)
- **Size**: 2400 x 1200 pixels
- **Purpose**: Marketing campaigns and featured placements
- **Status**: ⏳ Optional - create if needed for promotions

### Screenshot Images
- **Size**: 1920 x 1080 pixels (or actual app resolution)
- **Quantity**: 4-10 screenshots recommended
- **Purpose**: Show app features and interface
- **Status**: ⏳ Need to capture from running app
- **See**: `SCREENSHOT_REQUIREMENTS.md` for details

## Testing Your Logos

### Visibility Test
1. View each logo at actual size (100% zoom)
2. Check clarity and recognizability
3. Test on different backgrounds:
   - White background
   - Black background
   - Blue background (Microsoft blue)
   - Colored backgrounds

### Contrast Test
Ensure your logo:
- Has good contrast
- Is clearly visible on all backgrounds
- Maintains brand identity

### Size Test
The 44x44 logo should:
- Still be recognizable
- Maintain key design elements
- Have clear, visible shapes
- Not look cluttered or messy

## Microsoft Store Logo Guidelines

Follow Microsoft's guidelines:
- **Transparency**: Use transparent PNG backgrounds
- **Padding**: Include some padding around main icon (about 10% of canvas)
- **Quality**: Use high-quality, crisp images
- **Consistency**: All sizes should look cohesive
- **Scaling**: Design should scale well from 44x44 to 1240x1240

## Quick Command Reference

```powershell
# Create all sizes at once (save this script)
$sizes = @(1240, 400, 150, 88, 44)
foreach ($size in $sizes) {
    Write-Host "Create store_logo_$size.png at ${size}x${size} pixels"
}
```

---

**Next Steps:**
1. Review `store_logo_1240.png` and `store_hero_image.png`
2. Create smaller logo sizes using method above
3. Test all logos at actual size
4. Verify quality and visibility
5. Save all files in `/store/assets/` folder
6. Proceed to screenshot creation
