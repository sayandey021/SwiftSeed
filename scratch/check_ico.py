import sys
from PIL import Image, ImageSequence

def check_ico(path):
    img = Image.open(path)
    print(f"File: {path}")
    for i, frame in enumerate(ImageSequence.Iterator(img)):
        frame_rgba = frame.convert("RGBA")
        bbox = frame_rgba.getbbox()
        print(f"Frame {i}: size {frame.size}, bbox {bbox}")

if __name__ == '__main__':
    check_ico('src/assets/icon.ico')
