import shutil
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
icon_dir = os.path.join(base_dir, "icon")
assets_dir = os.path.join(base_dir, "src", "assets")

file_ico_src = os.path.join(icon_dir, "file.ico")
file_png_src = os.path.join(icon_dir, "file.png")

if os.path.exists(file_ico_src):
    shutil.copy2(file_ico_src, os.path.join(assets_dir, "file.ico"))
    print(f"Copied {file_ico_src} to assets.")

if os.path.exists(file_png_src):
    shutil.copy2(file_png_src, os.path.join(assets_dir, "file.png"))
    print(f"Copied {file_png_src} to assets.")
