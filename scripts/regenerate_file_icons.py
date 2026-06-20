"""
Regenerate file.ico from file.png with all required sizes for proper
Windows Explorer scaling. The .ico MUST contain a 256x256 PNG-compressed
frame for large/extra-large icon views to work properly.

Usage:
    python scripts/regenerate_file_icons.py

This reads icon/file.png (high-res source) and outputs:
    - icon/file.ico        (multi-frame ICO with 256px frame)
    - src/assets/file.ico  (copy)
    - src/assets/file.png  (copy of source)
"""

import os
import sys
import shutil
from PIL import Image

# All sizes Windows Explorer needs for proper scaling
# 256 is critical — without it, large icons show a tiny image
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Find the high-res source PNG
    source_candidates = [
        os.path.join(base_dir, "icon", "512p.png"),
        os.path.join(base_dir, "icon", "file.png"),
        os.path.join(base_dir, "src", "assets", "file.png"),
    ]
    
    source_path = None
    for candidate in source_candidates:
        if os.path.exists(candidate):
            source_path = candidate
            break
    
    if not source_path:
        print("ERROR: No source file.png found in icon/ or src/assets/")
        print("Place a high-resolution PNG of your file icon at icon/file.png")
        sys.exit(1)
    
    print(f"Source: {source_path}")
    
    # Load the source image
    img = Image.open(source_path)
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    print(f"Source size: {img.width}x{img.height}")
    
    if img.width < 256 or img.height < 256:
        print(f"WARNING: Source image is only {img.width}x{img.height}. "
              f"For best results, use a 512x512 or larger source.")
    
    # Generate each size frame
    frames = []
    for size in ICO_SIZES:
        frame = img.resize((size, size), Image.Resampling.LANCZOS)
        frames.append(frame)
        print(f"  Generated {size}x{size} frame")
    
    # Save as ICO with all frames
    # The 256x256 frame will be PNG-compressed inside the ICO (standard for modern .ico)
    output_paths = [
        os.path.join(base_dir, "icon", "file.ico"),
        os.path.join(base_dir, "src", "assets", "file.ico"),
    ]
    
    for output_path in output_paths:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        frames[0].save(
            output_path,
            format='ICO',
            sizes=[(s, s) for s in ICO_SIZES],
            append_images=frames[1:]
        )
        file_size = os.path.getsize(output_path)
        print(f"  Saved: {output_path} ({file_size:,} bytes)")
    
    # Also copy the source PNG to src/assets if it's not already there
    assets_png = os.path.join(base_dir, "src", "assets", "file.png")
    if source_path != assets_png:
        shutil.copy2(source_path, assets_png)
        print(f"  Copied source PNG to: {assets_png}")
    
    print(f"\nDone! ICO contains frames: {ICO_SIZES}")
    print(f"ICO file size should be >50KB if 256x256 frame is included properly.")
    
    # Verify
    for output_path in output_paths:
        size = os.path.getsize(output_path)
        if size < 50000:
            print(f"  WARNING: {output_path} is only {size:,} bytes — 256px frame may be missing!")
        else:
            print(f"  OK: {output_path} = {size:,} bytes")


if __name__ == "__main__":
    main()
