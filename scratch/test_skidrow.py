import sys
import os

# Add src to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from providers.additional import SkidrowRepackProvider
from models.torrent import Torrent
from models.category import Category
import bs4

provider = SkidrowRepackProvider()

# Let's mock a torrent object
t = Torrent(
    name="Black Myth: Wukong EMPRESS",
    size="Unknown",
    seeders=-1,
    peers=-1,
    provider_id=provider.info.id,
    provider_name=provider.info.name,
    upload_date="Unknown",
    description_url="https://www.skidrowreloadedcrack.com/black-myth-wukong-empress/",
    magnet_uri="https://www.skidrowreloadedcrack.com/black-myth-wukong-empress/",
    category=Category.GAMES
)

html = provider._get(t.description_url)
soup = bs4.BeautifulSoup(html, 'html.parser')

print("=== magnets ===")
magnets = soup.find_all('a', href=lambda h: h and h.startswith('magnet:'))
for m in magnets:
    print(m.get('href'), "|", m.get_text(strip=True))

print("\n=== torrent links ===")
torrent_links = soup.find_all('a', href=lambda h: h and ('.torrent' in h.lower() or 'torrent' in h.lower() or 'do=download' in h.lower()))
for t_link in torrent_links:
    print(t_link.get('href'), "|", t_link.get_text(strip=True))

print("\n=== test _fetch_details ===")
results = provider._fetch_details([t])
for r in results:
    print(f"Name: {r.name}, URI: {r.magnet_uri}, Size: {r.size}")

