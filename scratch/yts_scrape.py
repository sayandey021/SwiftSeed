import re, json

with open('yts_search.html', encoding='utf-8') as f:
    html = f.read()

# Look for next data
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html)
if m:
    data = json.loads(m.group(1))
    print("Found NEXT_DATA")
    try:
        movies = data['props']['pageProps']['movies']
        print(f"Found {len(movies)} movies")
        for m in movies[:2]:
            print(m['title'])
    except Exception as e:
        print("Error parsing next data:", e)
else:
    print("No NEXT_DATA")
    
    # Let's search for any JSON in the page
    m2 = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', html)
    if m2:
        print("Found INITIAL_STATE")
    else:
        # maybe movies are just in the DOM?
        pass
