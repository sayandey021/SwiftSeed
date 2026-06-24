import os
from PIL import Image

def check_icon():
    img_path = 'src/assets/icon.png'
    img = Image.open(img_path)
    img = img.convert("RGBA")
    bbox = img.getbbox()
    print(f"Original size: {img.size}")
    print(f"Bounding box: {bbox}")

if __name__ == '__main__':
    check_icon()
