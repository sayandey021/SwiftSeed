import requests
from bs4 import BeautifulSoup
import re

url = "https://www.skidrowreloadedcrack.com/metal-gear-solid-delta-snake-eater-v1-1-2-p2p/"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
r = requests.get(url, headers=headers)
if r.status_code == 200:
    content = r.text
    
    # Try different size regexes
    free_disk_match = re.search(r'Free\s*Disk\s*Space[:\s]*(\d+(?:[.,]\d+)?\s*(?:GB|MB|TB))', content, re.I)
    hdd_match = re.search(r'(?:Hard\s*disk|HDD|Disk\s*space)[:\s]*(\d+(?:[.,]\d+)?\s*(?:GB|MB|TB))', content, re.I)
    storage_match = re.search(r'(?:Storage|Space\s*required|Available\s*space)[:\s]*(\d+(?:[.,]\d+)?\s*(?:GB|MB|TB))', content, re.I)
    repack_match = re.search(r'(?:Repack|Download|Game|File|Install|Installed)\s*(?:size)?[:\s~]+(\d+(?:[.,]\d+)?\s*(?:GB|MB|TB))', content, re.I)
    
    print("Free Disk:", free_disk_match.group(1) if free_disk_match else "None")
    print("HDD:", hdd_match.group(1) if hdd_match else "None")
    print("Storage:", storage_match.group(1) if storage_match else "None")
    print("Repack:", repack_match.group(1) if repack_match else "None")
    
    # Let's extract raw text and look at it
    soup = BeautifulSoup(content, 'html.parser')
    print("---")
    print(soup.get_text()[:500])
