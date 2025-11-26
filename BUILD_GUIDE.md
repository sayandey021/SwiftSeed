# SwiftSeed Build Guide

This guide will help you create portable and installer versions of SwiftSeed for distribution.

## Prerequisites

1. **Python 3.8+** with all dependencies installed
2. **PyInstaller** (auto-installed by build script)
3. **Inno Setup 6** (optional, for installer creation)
   - Download from: https://jrsoftware.org/isdl.php

## Quick Build (Recommended)

The easiest way to build everything:

```bash
python build_all.py
```

This will:
1. Check and install PyInstaller if needed
2. Build the portable executable (`dist/SwiftSeed.exe`)
3. Create the installer if Inno Setup is installed (`installer/SwiftSeed_Setup_v1.5.exe`)

## Manual Build Steps

### 1. Build Portable Executable Only

```bash
python build_exe.py
```

Output: `dist/SwiftSeed.exe`

### 2. Build Installer (After building exe)

**Prerequisites**: Install Inno Setup first

**Option A: Using Inno Setup GUI**
1. Open `installer_script.iss` in Inno Setup Compiler
2. Click "Build" → "Compile"
3. Installer will be in `installer/` folder

**Option B: Using Command Line**
```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer_script.iss
```

## Output Files

After building, you'll have:

### Portable Version
- **File**: `dist/SwiftSeed.exe`
- **Size**: ~50-70 MB (depends on compression)
- **Usage**: Single executable, no installation needed
- **User data**: Stored in `%APPDATA%/SwiftSeed`

### Installer Version
- **File**: `installer/SwiftSeed_Setup_v1.5.exe`
- **Size**: ~50-70 MB
- **Features**:
  - No admin rights required
  - Desktop shortcut (optional)
  - Start menu entry
  - Clean uninstaller
  - Removes user data on uninstall

## Distribution

### For General Users
Provide **both** options:

1. **Portable** (`SwiftSeed.exe`)
   - For users who want no installation
   - Can run from USB drive
   - No system changes

2. **Installer** (`SwiftSeed_Setup_v1.5.exe`)
   - Recommended for most users
   - Better Windows integration
   - Easy updates and uninstall

### File Naming Convention
- Portable: `SwiftSeed_v1.5_Portable.exe`
- Installer: `SwiftSeed_Setup_v1.5.exe`

## Troubleshooting

### Build Fails
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (should be 3.8+)
- Try deleting `build/` and `dist/` folders and rebuild

### Icon Not Showing
- Ensure `src/assets/icon.ico` exists
- Windows caches icons - may need to restart after install

### Large File Size
- Normal for bundled Python apps (includes Python runtime)
- UPX compression is enabled for smaller size
- Can't reduce much more without breaking dependencies

### Inno Setup Not Found
- Download and install from: https://jrsoftware.org/isdl.php
- Use default installation path
- Restart command prompt after installation

## Build Configuration

### Icon
- Location: `src/assets/icon.ico`
- Format: ICO with multiple sizes (16, 32, 48, 64, 128, 256px)
- Used for: Taskbar, title bar, shortcuts, installer

### Version
- Update in: `installer_script.iss` (line 5: `MyAppVersion`)
- Update in: `src/main.py` (line 281: Version text)

### App Metadata
- Publisher: Line 6 of `installer_script.iss`
- URL: Line 7 of `installer_script.iss`

## Testing Before Distribution

1. **Test Portable**:
   ```
   dist/SwiftSeed.exe
   ```
   - Check all features work
   - Verify icon displays correctly
   - Test downloads

2. **Test Installer**:
   - Install to test location
   - Verify shortcuts created
   - Test app functionality
   - Uninstall and verify cleanup

3. **Test on Clean System**:
   - Use VM or separate PC
   - No Python installed
   - Verify everything works standalone

## License & Distribution

- SwiftSeed is distributed under [Your License]
- Ensure all third-party licenses are included
- Consider adding LICENSE.txt to installer

## Updates

To create updated version:
1. Update version number in code
2. Update `installer_script.iss` version
3. Test thoroughly
4. Rebuild with `python build_all.py`
5. Distribute new files

---

**Need Help?**
- GitHub: https://github.com/sayandey021
- Issues: [Create an issue](https://github.com/sayandey021/SwiftSeed/issues)
