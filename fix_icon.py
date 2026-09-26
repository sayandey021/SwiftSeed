import os
import shutil
from PIL import Image

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    source_png = os.path.join(base_dir, 'icon', 'icon.png')
    if not os.path.exists(source_png):
        source_png = os.path.join(base_dir, 'src', 'assets', 'icon.png')
    
    target_png = os.path.join(base_dir, 'src', 'assets', 'icon.png')
    target_ico_assets = os.path.join(base_dir, 'src', 'assets', 'icon.ico')
    target_ico_icon = os.path.join(base_dir, 'icon', 'icon.ico')
    
    try:
        print(f"Reading source: {source_png}")
        img = Image.open(source_png).convert('RGBA')
        
        # Ensure image is square
        w, h = img.size
        if w != h:
            max_dim = max(w, h)
            square = Image.new('RGBA', (max_dim, max_dim), (0, 0, 0, 0))
            square.paste(img, ((max_dim - w) // 2, (max_dim - h) // 2))
            img = square
        
        # Copy source PNG to src/assets/icon.png
        if os.path.abspath(source_png) != os.path.abspath(target_png):
            shutil.copy2(source_png, target_png)
            print(f"Copied PNG to {target_png}")
            
        icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        
        for ico_out in [target_ico_assets, target_ico_icon]:
            os.makedirs(os.path.dirname(ico_out), exist_ok=True)
            img.save(ico_out, format='ICO', sizes=icon_sizes)
            print(f"Saved: {ico_out} ({os.path.getsize(ico_out):,} bytes)")
            
        print("Successfully generated high-quality icon.ico with multiple sizes.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
