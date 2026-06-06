import requests
import bs4

r = requests.get('https://pirateiro.io/torrent/21096', headers={'User-Agent': 'Mozilla/5.0'})
soup = bs4.BeautifulSoup(r.text, 'html.parser')

print("Using select_one:")
magnet_elem = soup.select_one('a[href^="magnet:"]')
if magnet_elem:
    print(magnet_elem.get('href'))
else:
    print("None")

print("Using find_all:")
magnets = [a.get('href') for a in soup.find_all('a') if a.get('href') and 'magnet' in a.get('href')]
print(magnets)
