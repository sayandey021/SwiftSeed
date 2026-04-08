
import sys
import os

# Add src to python path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from providers.additional import ApacheTorrentProvider
from models.category import Category

def test_apache():
    provider = ApacheTorrentProvider()
    print(f"Testing {provider.info.name}...")
    
    # Search for a movie
    query = "batman"
    print(f"Searching for '{query}'...")
    results = provider.search(query, Category.MOVIES)
    
    print(f"Found {len(results)} results.")
    
    for i, torrent in enumerate(results[:3]):
        print(f"\n--- Result {i+1} ---")
        print(f"Name: {torrent.name}")
        print(f"Size: {torrent.size}")
        print(f"Magnet: {torrent.magnet_uri}")
        print(f"Date: {torrent.upload_date}")
        print(f"Desc URL: {torrent.description_url}")

if __name__ == "__main__":
    test_apache()
