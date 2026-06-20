import os
import shutil
from PIL import Image

workspace = r"c:\Users\sayan\Documents\GitHub\SwiftSeed Desktop"
document_image_path = os.path.join(workspace, "icon", "file1.png")
raw_logo_path = os.path.join(workspace, "src", "assets", "icon.png")

def make_square(img, pad_percentage=0.05):
    """Crops transparent/solid borders and pads an image into a square."""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
        
    # 1. Crop fully transparent borders (checking alpha channel only)
    alpha = img.split()[-1]
    bbox = alpha.getbbox()
    if bbox:
        img = img.crop(bbox)
        
    # 2. Check if the image has a solid white background (like a screenshot)
    bg_color = img.getpixel((0, 0))
    if bg_color[3] > 250 and bg_color[0] > 240 and bg_color[1] > 240 and bg_color[2] > 240:
        from PIL import ImageChops
        bg = Image.new(img.mode, img.size, bg_color)
        diff = ImageChops.difference(img, bg)
        diff_gray = diff.convert('L')
        bbox2 = diff_gray.getbbox()
        if bbox2:
            img = img.crop(bbox2)

    # 3. Create a square with padding
    x, y = img.size
    size = max(x, y)
    pad = max(int(size * pad_percentage), 1)
    new_size = size + pad * 2
    
    new_img = Image.new('RGBA', (new_size, new_size), (0, 0, 0, 0))
    new_img.paste(img, (pad + (size - x) // 2, pad + (size - y) // 2))
    return new_img

def main():
    if not os.path.exists(document_image_path):
        print(f"Document image not found: {document_image_path}")
        return
    if not os.path.exists(raw_logo_path):
        print(f"Raw logo image not found: {raw_logo_path}")
        return

    print("Processing document image for Win32/ICO...")
    doc_img = Image.open(document_image_path)
    squared_doc = make_square(doc_img, pad_percentage=0.02) # Very little padding for the document icon

    # 1. Update src/assets/file.png and icon/file.png with the squared document
    squared_doc.save(os.path.join(workspace, "src", "assets", "file.png"), "PNG")
    squared_doc.save(os.path.join(workspace, "icon", "file.png"), "PNG")
    print("Updated src/assets/file.png and icon/file.png")
    
    # 2. Update src/assets/file.ico
    ico_sizes = [16, 24, 32, 48, 64, 128, 256]
    ico_path = os.path.join(workspace, "src", "assets", "file.ico")
    squared_doc.save(ico_path, format='ICO', sizes=[(s, s) for s in ico_sizes])
    print(f"Updated {ico_path}")
    
    print("\nProcessing raw logo for MSIX assets...")
    raw_logo_img = Image.open(raw_logo_path)
    squared_logo = make_square(raw_logo_img, pad_percentage=0.08) # Slightly more padding so it fits well inside the MSIX plate
    
    # 3. Update all FileLogo*.png in msix_package/Assets using the RAW logo
    msix_assets = os.path.join(workspace, "msix_package", "Assets")
    if os.path.exists(msix_assets):
        for f in os.listdir(msix_assets):
            if f.startswith("FileLogo") and f.endswith(".png"):
                target_path = os.path.join(msix_assets, f)
                try:
                    with Image.open(target_path) as existing_img:
                        size = existing_img.size
                    
                    resized = squared_logo.resize(size, Image.Resampling.LANCZOS)
                    resized.save(target_path, format='PNG')
                    print(f"Updated MSIX asset {f} to size {size}")
                except Exception as e:
                    print(f"Failed to update {f}: {e}")
    else:
        print(f"MSIX assets directory not found: {msix_assets}")
        
    print("\nAll .torrent assets have been successfully rebuilt!")
    print("- Win32 uses the document shape (file1.png)")
    print("- MSIX uses the raw logo (icon.png) to be framed by Windows")

if __name__ == "__main__":
    main()
