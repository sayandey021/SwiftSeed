# Release Notes

## Version 2.5 - April 2026

### 🎯 Highlights
SwiftSeed v2.5 introduces a major cleanup of the project structure for better maintainability and a professional look. This release focuses on repository organization, enhanced ignoring of temporary files, and a more stable build process.

### ⚡ Major Features & Improvements

#### 📂 Repository Reorganization
The project structure has been cleaned up and reorganized to follow industry standards:
- **`docs/` Folder**: All documentation, guides, and release notes now reside in a dedicated folder.
- **`scripts/dev/` Folder**: Experimental and development-only scripts (like `apicheck.py`) are moved away from the root directory.
- **Root Cleanup**: The root directory is now focused and clean, containing only essential project files.

#### 🛡️ Enhanced .gitignore
Significant improvements to the Git exclusion rules:
- Added comprehensive patterns for logs, temporary files (`.tmp`, `.bak`), and system artifacts (`.DS_Store`, `Thumbs.db`).
- Improved handling of build artifacts to prevent repo bloat.

#### 🔧 Version Standardization
Unified the versioning across all components:
- Updated `version_info.txt`, `setup.py`, Inno Setup script, and MSIX Manifest to a consistent **2.5.0** release version.

### 📋 Quality of Life
- **Stability**: Refined the application shutdown process for better session saving.
- **Docs**: Updated building guides with the new folder paths.

---

## Version 1.9 - December 2025

### 🎯 Highlights
SwiftSeed v1.9 introduces a powerful **File Association System** that makes SwiftSeed your default torrent handler, along with critical bug fixes for magnet link handling. This release focuses on seamless Windows integration and improved reliability.

### ⚡ Major Features

#### 🔗 File Association System
Transform SwiftSeed into your default torrent handler with one click!

- **Windows Integration**: Native support for .torrent files and magnet: links
- **One-Click Setup**: "Set as Default for All" button in Settings
- **Smart First-Run Prompt**: Friendly dialog asks to set defaults on first launch
  - Shows only when running as .exe
  - Three options: "Yes, Set as Default", "Not Now", "Never Ask Again"
  - Respects user choice and never nags
- **Settings Tab**: New "File Associations" tab with:
  - Real-time status display (✓ Registered / ✗ Not registered)
  - Individual registration for .torrent files or magnet: links
  - Easy unregister options
  - Direct link to Windows Default Apps settings
  - Comprehensive help text with visual guides
- **Seamless Experience**:
  - Double-click any .torrent file → Opens in SwiftSeed
  - Click magnet: links in browser → Opens in SwiftSeed
  - Works alongside other torrent clients
  - No admin rights required (uses HKEY_CURRENT_USER)

#### 🐛 Critical Bug Fixes

**Magnet Link Cancel & Restart Issues**:
- **Fixed Duplicate Behavior**: Pasting a cancelled magnet link now correctly shows the file selection dialog again (instead of directly downloading)
- **Fixed Restart Persistence**: Cancelled downloads no longer reappear in paused state after app restart
- **Improved State Management**: 
  - Added `visible` parameter to download system
  - Downloads are now properly hidden until user confirms them
  - State is saved immediately with correct visibility flag
- **Better Duplicate Detection**: App now correctly identifies if a magnet was already added vs. was cancelled

### 🎨 UI/UX Improvements

- **Settings Organization**: New dedicated tab for file associations with clear status indicators
- **User Guidance**: Comprehensive help text with emoji icons for easy understanding
- **Error Handling**: Better error messages with recovery suggestions
- **Graceful Degradation**: Features disable cleanly when running from Python (not .exe)
- **Status Colors**: 
  - 🟢 Green: Successfully registered
  - 🟠 Orange: Partially configured or exe-only feature
  - ⚪ Grey: Not registered

### 🛠️ Technical Improvements

- **File Association Manager**: New `FileAssociationManager` class for Windows registry operations
- **Registry Safety**: All operations use HKEY_CURRENT_USER (no elevation required)
- **Recursive Cleanup**: Proper registry key deletion for complete uninstallation
- **State Persistence**: New settings keys for prompt display and user preferences
- **Error Recovery**: Robust try-catch blocks prevent crashes from registry errors
- **Platform Detection**: Smart detection of executable vs. Python environment

### 📋 Quality of Life

- **No More Phantom Downloads**: Cancelled magnets won't haunt your download list
- **Consistent Behavior**: Same magnet link always behaves the same way
- **User Control**: Complete control over file associations from Settings
- **Documentation**: Comprehensive implementation guide in `V1.9_IMPLEMENTATION_GUIDE.md`

### 🔧 For Developers

- **New Manager**: `src/managers/file_association_manager.py` (245 lines)
- **Modified Files**:
  - `src/ui/settings_view.py` - File Associations tab
  - `src/main.py` - First-run prompt integration
  - `src/managers/torrent_manager.py` - Visibility parameter
  - `src/ui/downloads_view.py` - Fixed cancel behavior
- **Documentation**:
  - `V1.9_IMPLEMENTATION_GUIDE.md` - Complete technical guide
  - `MAGNET_CANCEL_FIX.md` - Bug fix details
  - `FILE_ASSOCIATION_PROMPT.md` - Prompt documentation

---

## Version 1.8 - December 2025

### 🎯 Highlights
SwiftSeed v1.8 brings System Tray integration for background downloading, along with improved dialog interactions and easier update access.

### 🎨 UI/UX Enhancements
- **System Tray Integration**:
  - Application minimizes to system tray when closed
  - Right-click tray icon to Exit or Show application
  - Keeps downloads running in the background
- **Dialog Improvements**:
  - File selection dialog now closes automatically after saving .torrent file
  - Default save location for .torrent files set to Downloads folder
- **Update Check**: Direct link to GitHub Releases page for easier updates
- **Support Link**: Updated donation link to Ko-fi

---

## Version 1.7 - December 2025

### 🎯 Highlights
SwiftSeed v1.7 brings major improvements to download persistence, application stability, performance optimization, and visual design. This release focuses on providing a robust, portable, and visually stunning torrent client experience.

### 🔒 Download Persistence & State Management
- **Advanced Download Recovery**: Downloads now correctly persist across application restarts, even if original files are deleted from the directory
- **Smart File State Detection**: Application accurately reflects the status of deleted or missing files in the download list
- **Enhanced Selection Persistence**: File selection information is now properly saved and restored
- **Immediate State Saving**: Download state is saved immediately after critical actions (add, remove, pause, resume) to prevent data loss
- **Intelligent Resume**: Downloads automatically resume from the exact point where they left off

### 📦 Portable Distribution & DLL Management
- **Fully Portable Build**: Fixed critical `ImportError: DLL load failed while importing libtorrent` issues
- **Complete DLL Bundling**: All necessary libtorrent DLLs and dependencies are correctly bundled with the executable
- **Zero Dependencies**: Application now runs on fresh machines without requiring pre-installed Python or libraries
- **Clean ZIP Distribution**: Streamlined portable package for easy deployment
- **Consolidated Build Process**: Single `build_complete.py` script and unified `build.bat` for simplified building

### ⚡ Performance Optimization
- **Maximum Download Speed**: Significantly optimized libtorrent configuration for peak performance
- **Enhanced Connection Management**: Improved connection limits, timeouts, and choking algorithms
- **Optimized Disk I/O**: Better disk cache and read/write settings for faster transfers
- **Network Tuning**: Fine-tuned network-related settings to match or exceed other torrent clients
- **Performance Documentation**: Added comprehensive performance comparison and troubleshooting guide

### 🎨 UI/UX Enhancements
- **Glass Theme (Premium)**: New stunning glassmorphism theme with modern aesthetics
  - Vibrant gradients and smooth animations
  - Premium dark mode with sophisticated blur effects
  - Elevated visual design that wows at first glance
- **Improved File Selection Dialog**:
  - Fixed folder checkbox logic for nested structures
  - Parent folder checkboxes now correctly update all descendants
  - Accurate checkbox state reflection for folders and files
  - Fixed "Select All" and "Deselect All" buttons functionality
- **Enhanced Download View**:
  - Improved display of file and folder structures
  - Fixed incorrect file extensions on folder names
  - Better visual representation with appropriate icons
- **Taskbar Branding**: Consistent "SwiftSeed Client" icon and text in Windows taskbar and jump list
### 🐛 Bug Fixes
- **Close Dialog**: Fixed issue where confirmation dialog wasn't appearing when closing the application
- **File Display**: Resolved inconsistent file structure display for magnet links and bookmarked torrents
- **Folder Recognition**: Fixed bug where folders appeared with file extensions in the UI
- **Download Tab Refresh**: Fixed issue where newly added downloads wouldn't appear
- **Pause/Resume**: Fixed independent pause/resume functionality for individual downloads
- **UI Glitches**: Resolved various visual inconsistencies on the download page
- **Nested Folder Support**: Proper expand/collapse functionality for folder hierarchies

### 🛠️ Technical Improvements
- **Cleaner Project Structure**: Removed unnecessary build artifacts and temporary files
- **Unified Build Scripts**: Consolidated multiple build scripts into a single, maintainable solution
- **Single Dist Folder**: Streamlined output directory structure
- **Single Inno Setup Script**: Simplified installer creation process
- **Updated Social Links**: Refreshed LinkedIn and support links in the About section
- **SEO Optimization**: Implemented best practices for better web visibility

### 📋 Quality of Life
- **Better Error Messages**: More informative error handling and user feedback
- **Improved Documentation**: Enhanced build guides and troubleshooting resources
- **Version Consistency**: Proper version information across all application components

---

## Version 1.6 - Previous Release

## 🚀 Major Updates

### 📦 Standalone Libtorrent Integration
We have completely transitioned to a standalone downloader using **Libtorrent**. This removes the dependency on external clients like Aria2 or qBittorrent, making SwiftSeed a fully self-contained torrent client.
- **Native Downloading**: High-performance downloading directly within the app.
- **Magnet Link Support**: Seamless handling of magnet links with metadata fetching.
- **Torrent File Support**: Open and download local `.torrent` files.

### 💾 Enhanced State Management
- **Robust Persistence**: Downloads now save their state immediately upon addition, removal, pause, or resume. Your download progress is safe even if the app closes unexpectedly.
- **Smart Resume**: The application intelligently resumes downloads from where they left off.

## ✨ UI/UX Improvements

- **File Selection Dialog**: 
  - Improved file parsing to correctly display folder structures and file names.
  - Fixed issues where folders were incorrectly identified as files.
  - You can now select/deselect specific files before starting a download.
- **Download Management**:
  - Added a **"Open Folder"** button to quickly access downloaded files.
  - Fixed "Pause", "Resume", "Stop", and "Delete" buttons for reliable control.
  - Real-time speed, peer, and ETA updates.
- **Social Links**: Updated "About" section with current social media and support links.

## 🐛 Bug Fixes

- **Magnet Links**: Fixed an issue where magnet links would not correctly fetch or display the file list.
- **File Extensions**: Resolved a bug where downloaded files sometimes lacked the correct extension.
- **UI Refresh**: Fixed an issue where newly added downloads wouldn't appear in the list immediately.
- **Stability**: Fixed a critical indentation error in the TorrentManager that caused crashes.
- **Temp Files**: Corrected the handling of temporary files during the download process.

## 🛠️ Technical Changes

- **Backend**: Switched core engine to `python-libtorrent`.
- **Cleanup**: Removed unused build artifacts and temporary files for a cleaner repository.

---

*Enjoy the new and improved SwiftSeed! Happy Downloading!* 
