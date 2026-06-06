import requests
proxies=['yts.mx', 'yts.torrentbay.st', 'yts.rs', 'yts.lt', 'yts.am', 'yts.ae', 'yts.ag', 'ytss.to', 'yts.pm', 'yts.do', 'yts.cool', 'yify.fi', 'yts.movie', 'yify.is']
res=[]
for p in proxies:
    try:
        if requests.get(f'https://{p}/api/v2/list_movies.json?limit=1', timeout=4, verify=False).status_code == 200:
            res.append(p)
    except:
        pass
print('Working:', res)
