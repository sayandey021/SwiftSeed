import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from providers.additional import SkidrowRepackProvider
import bs4

provider = SkidrowRepackProvider()
html = provider._get("https://www.skidrowreloadedcrack.com/black-myth-wukong-empress/")
soup = bs4.BeautifulSoup(html, 'html.parser')

print("ALL A TAGS:")
for a in soup.find_all('a'):
    href = a.get('href', '')
    text = a.get_text(strip=True)
    if 'skidrowreloadedcrack' not in href and not href.startswith('/'):
        print(f"EXT: {text} -> {href}")
    elif '.torrent' in href.lower() or 'magnet:' in href.lower() or 'download' in href.lower() or 'file' in href.lower():
        print(f"INT MATCH: {text} -> {href}")
