"""
MSIX Asset Generator for SwiftSeed
Generates properly sized PNG assets from source images for MSIX packaging.

Key design decisions:
- Uses resize() instead of thumbnail() so icons always FILL the target canvas
  (thumbnail only downscales, which causes tiny icons if the source is small)
- For file association icons, _altform-unplated variants fill edge-to-edge
  so Windows doesn't add a plaque/background behind them
- Prefers .png sources over .ico for higher quality extraction
"""

import os
import sys
from PIL import Image


def load_best_image(source_path):
    """Load the best quality image from a file.
    
    For .ico files, tries to find and load the largest available frame.
    For .png/.jpg, loads directly.
    """
    img = Image.open(source_path)
    
    if img.format == 'ICO':
        # ICO files contain multiple sizes. Pillow loads the largest by default,
        # but let's be explicit and ensure we get the biggest one.
        sizes = img.info.get('sizes', set())
        if sizes:
            # Pick the largest frame by area
            best_size = max(sizes, key=lambda s: s[0] * s[1])
            # Reopen at that specific size
            img = Image.open(source_path)
            img.size = best_size
    
    # Convert to RGBA for consistent handling
    img = img.convert('RGBA')
    return img


def generate_icon(source_img, width, height, output_path, edge_to_edge=False):
    """Generate a single icon at the specified dimensions.
    
    Args:
        source_img: PIL Image source
        width: Target width in pixels
        height: Target height in pixels
        output_path: Where to save the PNG
        edge_to_edge: If True, icon fills entire canvas (for unplated variants).
                      If False, adds ~12.5% padding on each side (for plated variants).
    """
    if edge_to_edge:
        # Icon fills the entire canvas — no padding
        resized = source_img.resize((width, height), Image.Resampling.LANCZOS)
        resized.save(output_path, "PNG")
    else:
        # Add padding so the plated background looks good
        # Standard MSIX guidance: ~75% of tile is icon, rest is padding
        padding_fraction = 0.125  # 12.5% padding on each side = 75% icon
        icon_w = int(width * (1 - 2 * padding_fraction))
        icon_h = int(height * (1 - 2 * padding_fraction))
        
        # Maintain aspect ratio within the padded area
        src_aspect = source_img.width / source_img.height
        target_aspect = icon_w / icon_h
        
        if src_aspect > target_aspect:
            draw_w = icon_w
            draw_h = int(icon_w / src_aspect)
        else:
            draw_h = icon_h
            draw_w = int(icon_h * src_aspect)
        
        resized = source_img.resize((draw_w, draw_h), Image.Resampling.LANCZOS)
        
        # Create transparent canvas and paste centered
        canvas = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        offset_x = (width - draw_w) // 2
        offset_y = (height - draw_h) // 2
        canvas.paste(resized, (offset_x, offset_y))
        canvas.save(output_path, "PNG")


def generate_app_assets(source_path, output_dir):
    """Generate app tile/logo assets."""
    img = load_best_image(source_path)
    print(f"  App icon source: {img.width}x{img.height} from {os.path.basename(source_path)}")
    
    app_assets = [
        (50, 50, "StoreLogo.png", False),
        (150, 150, "Square150x150Logo.png", False),
        (44, 44, "Square44x44Logo.png", False),
        (310, 150, "Wide310x150Logo.png", False),
        (620, 300, "SplashScreen.png", False),
    ]
    
    for width, height, name, edge_to_edge in app_assets:
        out = os.path.join(output_dir, name)
        print(f"  Creating {name} ({width}x{height})...")
        generate_icon(img, width, height, out, edge_to_edge)


def generate_file_assets(source_path, output_dir):
    """Generate file type association assets.
    
    The _altform-unplated variants are edge-to-edge so Windows
    displays the raw icon without adding a background plaque.
    Regular variants have padding for the plated display.
    """
    img = load_best_image(source_path)
    print(f"  File icon source: {img.width}x{img.height} from {os.path.basename(source_path)}")
    
    # (size, name, edge_to_edge)
    file_assets = [
        # Base icon (plated) - set to True so it doesn't double-pad the document shape
        (44, "FileLogo.png", True),
        # Target size variants - plated (with padding for plaque) - set to True to prevent tiny document icons
        (16, "FileLogo.targetsize-16.png", True),
        (32, "FileLogo.targetsize-32.png", True),
        (44, "FileLogo.targetsize-44.png", True),
        (48, "FileLogo.targetsize-48.png", True),
        (64, "FileLogo.targetsize-64.png", True),
        (96, "FileLogo.targetsize-96.png", True),
        (256, "FileLogo.targetsize-256.png", True),
        # Unplated variants — EDGE TO EDGE, no padding
        # These are what Windows uses when it can display without a plaque
        (16, "FileLogo.targetsize-16_altform-unplated.png", True),
        (32, "FileLogo.targetsize-32_altform-unplated.png", True),
        (44, "FileLogo.targetsize-44_altform-unplated.png", True),
        (48, "FileLogo.targetsize-48_altform-unplated.png", True),
        (64, "FileLogo.targetsize-64_altform-unplated.png", True),
        (96, "FileLogo.targetsize-96_altform-unplated.png", True),
        (256, "FileLogo.targetsize-256_altform-unplated.png", True),
    ]
    
    for size, name, edge_to_edge in file_assets:
        out = os.path.join(output_dir, name)
        print(f"  Creating {name} ({size}x{size}, {'unplated' if edge_to_edge else 'plated'})...")
        generate_icon(img, size, size, out, edge_to_edge)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate MSIX assets from source icons")
    parser.add_argument("--icon", required=True, help="Path to app icon (.ico or .png)")
    parser.add_argument("--file-icon", required=False, default="", help="Path to file type icon (.ico or .png)")
    parser.add_argument("--outdir", required=True, help="Output directory for assets")
    args = parser.parse_args()
    
    os.makedirs(args.outdir, exist_ok=True)
    
    print("Generating app assets...")
    generate_app_assets(args.icon, args.outdir)
    
    file_icon_source = args.file_icon if args.file_icon else args.icon
    print(f"\nGenerating file association assets...")
    generate_file_assets(file_icon_source, args.outdir)
    
    print("\nDone! All MSIX assets generated.")


if __name__ == "__main__":
    main()
