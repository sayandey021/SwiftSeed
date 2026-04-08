"""
Regenerate file.ico with a larger logo inside the document shape.
The logo should fill more of the icon space so it appears bigger at all sizes.
"""

from PIL import Image, ImageDraw
import os

# Load the original SwiftSeed logo
LOGO_PATH = "icon.png"

# Output
OUTPUT_ICO = "file.ico"

# ICO sizes to include (Windows uses these)
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]

def create_document_icon(logo_img, size, logo_scale=0.70):
    """
    Create a document-style icon with the logo inside.
    
    Args:
        logo_img: PIL Image of the logo
        size: Output icon size
        logo_scale: How much of the icon the logo should fill (0.7 = 70%)
    """
    # Create transparent canvas
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # Document shape dimensions
    margin = int(size * 0.05)  # 5% margin
    doc_width = size - (margin * 2)
    doc_height = size - (margin * 2)
    fold_size = int(size * 0.15)  # Corner fold size
    corner_radius = int(size * 0.08)  # Rounded corners
    
    # Document shape coordinates
    left = margin
    right = size - margin
    top = margin
    bottom = size - margin
    
    # Draw document background (white/light gray with rounded corners)
    # Using polygon for the document shape with folded corner
    doc_points = [
        (left + corner_radius, top),  # Top-left after curve
        (right - fold_size, top),     # Before fold
        (right, top + fold_size),     # After fold
        (right, bottom - corner_radius),  # Bottom-right before curve
        (right - corner_radius, bottom),  # Bottom-right after curve
        (left + corner_radius, bottom),   # Bottom-left before curve
        (left, bottom - corner_radius),   # Bottom-left after curve
        (left, top + corner_radius),      # Top-left before curve
    ]
    
    # Draw white background with slight shadow effect
    shadow_offset = max(1, int(size * 0.02))
    
    # Shadow
    shadow_color = (0, 0, 0, 40)
    for i in range(shadow_offset, 0, -1):
        alpha = int(40 * (shadow_offset - i + 1) / shadow_offset)
        draw.rounded_rectangle(
            [left + i, top + i, right + i, bottom + i],
            radius=corner_radius,
            fill=(0, 0, 0, alpha)
        )
    
    # Main document body
    draw.rounded_rectangle(
        [left, top, right, bottom],
        radius=corner_radius,
        fill=(255, 255, 255, 255),
        outline=(200, 200, 200, 255),
        width=max(1, int(size * 0.01))
    )
    
    # Folded corner effect
    fold_points = [
        (right - fold_size, top),
        (right, top + fold_size),
        (right - fold_size, top + fold_size),
    ]
    draw.polygon(fold_points, fill=(230, 230, 230, 255), outline=(200, 200, 200, 255))
    
    # Resize and place the logo
    logo_size = int(size * logo_scale)
    logo_resized = logo_img.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
    
    # Center the logo in the document
    logo_x = (size - logo_size) // 2
    logo_y = (size - logo_size) // 2 + int(size * 0.02)  # Slightly lower to account for fold
    
    # Paste logo with transparency
    canvas.paste(logo_resized, (logo_x, logo_y), logo_resized)
    
    return canvas


def create_simple_icon(logo_img, size, logo_scale=0.85):
    """
    Create a simpler icon with just the logo on document background.
    This makes the logo appear LARGER.
    """
    # Create transparent canvas
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # Margin and corner radius
    margin = int(size * 0.03)
    corner_radius = int(size * 0.12)
    fold_size = int(size * 0.18)
    
    # Document bounds
    left = margin
    right = size - margin
    top = margin
    bottom = size - margin
    
    # Draw shadow
    shadow_offset = max(1, int(size * 0.015))
    for i in range(shadow_offset + 2, 0, -1):
        alpha = int(30 * (shadow_offset + 2 - i + 1) / (shadow_offset + 2))
        draw.rounded_rectangle(
            [left + i, top + i, right + i, bottom + i],
            radius=corner_radius,
            fill=(0, 0, 0, alpha)
        )
    
    # Main document body - white
    draw.rounded_rectangle(
        [left, top, right, bottom],
        radius=corner_radius,
        fill=(255, 255, 255, 255),
        outline=(210, 210, 210, 255),
        width=max(1, int(size * 0.008))
    )
    
    # Folded corner
    fold_points = [
        (right - fold_size, top),
        (right, top),
        (right, top + fold_size),
    ]
    # Draw fold shadow first
    draw.polygon(
        [(right - fold_size + 1, top + 1), (right + 1, top + 1), (right + 1, top + fold_size + 1)],
        fill=(180, 180, 180, 100)
    )
    # Draw folded corner
    fold_inner = [
        (right - fold_size, top),
        (right, top + fold_size),
        (right - fold_size, top + fold_size),
    ]
    draw.polygon(fold_inner, fill=(240, 240, 240, 255), outline=(200, 200, 200, 255))
    
    # Calculate logo size - make it fill most of the document area
    available_width = right - left - margin * 2
    available_height = bottom - top - margin * 2 - int(fold_size * 0.3)  # Account for fold
    logo_size = int(min(available_width, available_height) * logo_scale)
    
    # Resize logo
    logo_resized = logo_img.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
    
    # Center logo (slightly lower to account for fold)
    logo_x = (size - logo_size) // 2
    logo_y = (size - logo_size) // 2 + int(fold_size * 0.15)
    
    # Paste logo
    canvas.paste(logo_resized, (logo_x, logo_y), logo_resized)
    
    return canvas


def main():
    # Load logo
    if not os.path.exists(LOGO_PATH):
        print(f"Error: Logo not found at {LOGO_PATH}")
        return
    
    logo = Image.open(LOGO_PATH)
    if logo.mode != 'RGBA':
        logo = logo.convert('RGBA')
    
    print(f"Loaded logo: {logo.size}")
    
    # Generate icons at each size
    icons = []
    for size in ICO_SIZES:
        # Use larger logo scale for bigger icons
        if size >= 64:
            scale = 0.72  # Larger logos for big icons
        elif size >= 32:
            scale = 0.65
        else:
            scale = 0.60  # Slightly smaller for tiny icons to maintain clarity
        
        icon = create_simple_icon(logo, size, logo_scale=scale)
        icons.append(icon)
        print(f"Created {size}x{size} icon (logo scale: {scale})")
    
    # Save as ICO with all sizes
    # PIL saves the first image and includes others as additional sizes
    icons[0].save(
        OUTPUT_ICO,
        format='ICO',
        sizes=[(s, s) for s in ICO_SIZES],
        append_images=icons[1:]
    )
    
    print(f"\n✓ Saved {OUTPUT_ICO} with sizes: {ICO_SIZES}")
    
    # Also save a preview of the 256x256 version
    icons[-1].save("file_new_preview.png", "PNG")
    print("✓ Saved file_new_preview.png for preview")


if __name__ == "__main__":
    main()
