# SwiftSeed

A modern, fast, and lightweight torrent search and download client built with Python and Flet.

## Features

- 🔍 **Unified Search**: Search torrents from multiple providers (ThePirateBay, Nyaa, 1337x, TorrentsCSV) simultaneously.
- 🚀 **Integrated Downloader**: Download torrents directly within the application using Libtorrent.
- 🎨 **Modern UI**: Sleek, dark-themed interface built with Flet.
- 📂 **Smart Organization**: Filter by categories (Movies, TV, Games, Anime, etc.).
- ⭐ **Bookmarks**: Save your favorite torrents for later.
- 📜 **History**: Keep track of your search history.
- ⚙️ **Customizable**: Enable/disable providers, manage settings, and add custom Torznab providers.

## Installation

### Running from Source

1. **Prerequisites**: Ensure you have Python 3.7+ installed.
2. **Clone the repository**:
   ```bash
   git clone https://github.com/sayandey021/SwiftSeed.git
   cd SwiftSeed
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the application**:
   ```bash
   python src/main.py
   ```

### Building the Executable

To create a standalone Windows executable:

```bash
python build_exe.py
```

The executable will be created in the `dist/` folder.

## Usage

1. **Search**: Enter a query in the search bar and select a category.
2. **Download**: Click the "Download" button on a result to start downloading.
3. **Manage**: Monitor downloads in the "Downloads" tab.
4. **Settings**: Configure providers and application preferences in the "Settings" tab.

## Data Storage

- **Settings & Data**: stored in `~/.swiftseed/`

## Disclaimer

This application is a search engine and download client. It does not host any content. The developer is not responsible for the content accessed or downloaded using this application. Please ensure you comply with your local laws and regulations regarding copyright and torrenting.

## License

[MIT License](LICENSE)
