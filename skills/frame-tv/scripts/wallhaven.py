"""wallhaven.py OUTDIR TYPE "query1" ["query2"...] [--n 24] [--cats 110]
Keyless Wallhaven search: SFW, >=3840x2160, 16:9 only, toplist all-time. Saves large thumbs + pool.json."""
import sys, os, json, time, urllib.request, urllib.parse, concurrent.futures as cf
args=[a for a in sys.argv[1:]]
n=int(args[args.index('--n')+1]) if '--n' in args else 24
cats=args[args.index('--cats')+1] if '--cats' in args else '110'
args=[a for i,a in enumerate(args) if a not in('--n','--cats') and (i==0 or args[i-1] not in('--n','--cats'))]
out,t,qs=args[0],args[1],args[2:]
os.makedirs(f'{out}/{t}',exist_ok=True)
UA={'User-Agent':'frame-tv-skill/0.1 (personal home use)'}
pool={}
for q in qs:
    for page in (1,2):
        u='https://wallhaven.cc/api/v1/search?'+urllib.parse.urlencode({'q':q,'categories':cats,'purity':'100','atleast':'3840x2160','ratios':'16x9','sorting':'favorites','page':page})
        u=u.replace('&topRange=','')
        try: d=json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30))
        except Exception as e: print('ERR',q,e); time.sleep(3); continue
        for w in d['data']: pool.setdefault(w['id'],{'id':w['id'],'q':q,'fav':w['favorites'],'res':w['resolution'],'path':w['path'],'thumb':w['thumbs']['large'],'url':w['url']})
        time.sleep(1.5)
        if d['meta']['last_page']<=page: break
top=sorted(pool.values(),key=lambda w:-w['fav'])[:n]
json.dump(top,open(f'{out}/{t}/pool.json','w'),indent=1)
def dl(w):
    fn=f"{out}/{t}/{w['id']}.jpg"
    if not os.path.exists(fn): open(fn,'wb').write(urllib.request.urlopen(urllib.request.Request(w['thumb'],headers=UA),timeout=30).read())
with cf.ThreadPoolExecutor(6) as ex: list(ex.map(dl,top))
print(t,len(pool),'found,',len(top),'kept')
