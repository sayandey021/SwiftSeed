import os
from PIL import Image

# Path to the 256px icon the user mentioned
source_path = r"c:\Users\sayan\Documents\GitHub\SwiftSeed Desktop\icon\256p.png"
output_ico = r"c:\Users\sayan\Documents\GitHub\SwiftSeed Desktop\icon\file.ico"
output_png = r"c:\Users\sayan\Documents\GitHub\SwiftSeed Desktop\icon\file.png"

# Standard Windows ICO sizes
ico_sizes = [16, 24, 32, 48, 64, 128, 256]

def main():
    if not os.path.exists(source_path):
        print(f"Error: Could not find {source_path}")
        return

    # Open the image
    img = Image.open(source_path)
    
    # Ensure it's RGBA
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
        
    print(f"Loaded {source_path} (size: {img.size})")

    # Generate resized images
    icons = []
    for size in ico_sizes:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        icons.append(resized)
        print(f"Generated {size}x{size} size.")
        
    # Save as ICO (bundles all sizes)
    icons[0].save(
        output_ico,
        format='ICO',
        sizes=[(s, s) for s in ico_sizes],
        append_images=icons[1:]
    )
    print(f"\nSaved multi-resolution ICO to {output_ico}")
    
    # Save as standard PNG (just the 256px version for fallback)
    img.save(output_png, format="PNG")
    print(f"Saved PNG to {output_png}")

if __name__ == "__main__":
    main()
