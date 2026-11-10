import json,os,subprocess,time
from pathlib import Path
B=str(Path(__file__).resolve().parent.parent)
ids=[l.strip() for l in open(os.environ.get("BGG_IDS", B+"/ids.txt"))]
out={}
for i in ids:
    it=json.load(open(f"{B}/raw/{i}.item.json"))['item']
    url=it.get('imageurl') or (it.get('images') or {}).get('thumb')
    p=f"{B}/img/{i}.jpg"
    if url and not (os.path.exists(p) and os.path.getsize(p)>1000):
        subprocess.run(["curl","-sL","-m","30","-A","Mozilla/5.0","-o",p,url]); time.sleep(0.3)
    ok=os.path.exists(p) and os.path.getsize(p)>1000
    out[i]={"local":f"img/{i}.jpg" if ok else None,"remote":url}
json.dump(out,open(B+"/work/images.json","w"),indent=1)
print(sum(1 for v in out.values() if v['local']),"of",len(out))
