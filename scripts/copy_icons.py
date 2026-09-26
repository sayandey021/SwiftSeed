import os
import shutil

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
icon_dir = os.path.join(base_dir, "icon")
assets_dir = os.path.join(base_dir, "src", "assets")
os.makedirs(assets_dir, exist_ok=True)

for fname in ["icon.png", "icon.ico", "file.png", "file.ico"]:
    src = os.path.join(icon_dir, fname)
    dst = os.path.join(assets_dir, fname)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"Copied {src} -> {dst}")
    else:
        print(f"Notice: {src} not found in icon/")
