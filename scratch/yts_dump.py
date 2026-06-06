import json, re

with open('yts_search.html', encoding='utf-8') as f:
    html = f.read()

m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html)
if m:
    data = json.loads(m.group(1))
    movies = data['props']['pageProps']['movies']
    print(json.dumps(movies[0], indent=2))
