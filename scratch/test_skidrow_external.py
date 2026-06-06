import sys
import os

# Add src to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from providers.additional import SkidrowRepackProvider
from models.torrent import Torrent
from models.category import Category
import bs4
import json

provider = SkidrowRepackProvider()

html = provider._get("https://www.skidrowreloadedcrack.com/black-myth-wukong-empress/")
soup = bs4.BeautifulSoup(html, 'html.parser')

all_links = soup.find_all('a')
links = []
for a in all_links:
    href = a.get('href', '')
    text = a.get_text(strip=True)
    if 'skidrowreloadedcrack.com' not in href and not href.startswith('/'):
        links.append({'text': text, 'href': href})
        
print("External links:")
for link in links:
    print(f"[{link['text']}] {link['href']}")
