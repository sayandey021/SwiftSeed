import os
import shutil

assets_dir = r"c:\Users\sayan\Documents\GitHub\SwiftSeed Desktop\msix_package\Assets"
source_png = r"c:\Users\sayan\Documents\GitHub\SwiftSeed Desktop\icon\file.png"

def main():
    if not os.path.exists(assets_dir):
        print(f"Assets directory not found at {assets_dir}")
        return
        
    if not os.path.exists(source_png):
        print(f"Source PNG not found at {source_png}")
        return

    # Delete all existing FileLogo files
    count = 0
    for file in os.listdir(assets_dir):
        if file.startswith("FileLogo"):
            os.remove(os.path.join(assets_dir, file))
            count += 1
    print(f"Deleted {count} old FileLogo files.")

    # Copy the new file as FileLogo.png and the unplated variants
    shutil.copy(source_png, os.path.join(assets_dir, "FileLogo.png"))
    shutil.copy(source_png, os.path.join(assets_dir, "FileLogo.targetsize-256_altform-unplated.png"))
    shutil.copy(source_png, os.path.join(assets_dir, "FileLogo.targetsize-48_altform-unplated.png"))
    
    print("Successfully copied file.png to msix_package/Assets! Your MSIX will now use the unplated icon.")

if __name__ == "__main__":
    main()
