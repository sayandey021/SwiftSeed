import sys
import subprocess
sys.path.append('c:\\Users\\sayan\\Documents\\GitHub\\SwiftSeed Desktop\\src')
from providers.additional import LeetxProvider

# get html via curl
result = subprocess.run(["curl.exe", "-s", "https://www.1377x.to/search/?q=ubuntu"], capture_output=True)
# Decode ignoring errors
html = result.stdout.decode('utf-8', errors='ignore')

provider = LeetxProvider()
# monkey patch _get
provider._get = lambda url: html

torrents = provider.search('ubuntu', None)
print(f'Found {len(torrents)} torrents')
for t in torrents[:5]:
    print(f'Name: {repr(t.name)}')
    print(f'Size: {t.size}')
