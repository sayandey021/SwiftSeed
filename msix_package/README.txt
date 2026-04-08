# SwiftSeed Portable - Setup Instructions

## Quick Start

1. Extract the ZIP file to any folder
2. Run `SwiftSeed.exe`
3. **If you see an error about missing DLLs**, install the Microsoft Visual C++ Redistributable (see below)

## System Requirements

- **Windows 10/11** (64-bit)
- **Microsoft Visual C++ Redistributable** (usually pre-installed)

## Troubleshooting

### "DLL load failed while importing libtorrent"

This error means you need to install the Microsoft Visual C++ Redistributable:

1. Download: https://aka.ms/vs/17/release/vc_redist.x64.exe
2. Run the installer
3. Restart SwiftSeed

**Why?** SwiftSeed uses the libtorrent library which requires Visual C++ runtime components. These are usually already installed on Windows, but fresh Windows installations might need them.

### First Run is Slow

The first time you run SwiftSeed, it may take a few seconds to start. This is normal as it initializes the torrent engine.

### Antivirus Warnings

Some antivirus software may flag torrent applications. SwiftSeed is safe - you can add it to your antivirus exceptions if needed.

## Portable Mode

SwiftSeed is fully portable:
- All settings are saved in the application folder
- `.resume` folder: Downloaded torrent resume data
- `.torrent_state` folder: Download state and settings
- No registry modifications
- Can run from USB drives

## Features

- Search torrents from multiple sources
- Download with selective file picking
- Resume support
- Speed limiting
- Built-in torrent client (no external apps needed)

## Support

For issues and updates, visit: https://github.com/YourUsername/SwiftSeed

## Legal Notice

SwiftSeed is a torrent client. Please use it responsibly and only download content you have the legal right to access.
