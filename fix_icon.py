from PIL import Image

def main():
    img_path = 'src/assets/icon.png'
    ico_path = 'src/assets/icon.ico'
    
    try:
        img = Image.open(img_path)
        # Create an icon with multiple sizes for best quality on Windows
        icon_sizes = [(16,16), (24, 24), (32, 32), (48, 48), (64,64), (128, 128), (256, 256)]
        
        # Save as ico
        img.save(ico_path, format='ICO', sizes=icon_sizes)
        print("Successfully generated high-quality icon.ico with multiple sizes.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
