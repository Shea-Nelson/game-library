import json,os,sys,time,urllib.request,urllib.error
from pathlib import Path
UA="Mozilla/5.0 (X11; Linux x86_64) SheaGameLibrary/1.0 (personal collection page)"
RAW=str(Path(__file__).resolve().parent.parent/"raw")
def get(url,tries=6):
    d=2
    for t in range(tries):
        try:
            r=urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":UA}),timeout=30)
            if r.status==202: raise urllib.error.HTTPError(url,202,"",None,None)
            return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (202,429,500,502,503,504): time.sleep(d); d*=2; continue
            raise
        except Exception: time.sleep(d); d*=2
    raise RuntimeError("failed "+url)
EP={
 "item":"https://api.geekdo.com/api/geekitems?objectid={id}&objecttype=thing",
 "dyn":"https://api.geekdo.com/api/dynamicinfo?objectid={id}&objecttype=thing",
 "files":"https://api.geekdo.com/api/files?objectid={id}&objecttype=thing&showcount=100&pageid=1&sort=hot",
 "videos":"https://api.geekdo.com/api/videos?objectid={id}&objecttype=thing&gallery=instructional&sort=hot&showcount=50&pageid=1",
 "forums":"https://api.geekdo.com/api/forums?objectid={id}&objecttype=thing",
}
ids=sys.argv[1:] or [l.strip() for l in open(RAW+"/../ids.txt")]
for i in ids:
    for k,u in EP.items():
        p=f"{RAW}/{i}.{k}.json"
        if os.path.exists(p): continue
        try:
            b=get(u.format(id=i)); open(p,"wb").write(b)
        except Exception as e: print("ERR",i,k,e,flush=True)
        time.sleep(1.0)
    print("done",i,flush=True)
