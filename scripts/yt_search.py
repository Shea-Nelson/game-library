import json,re,subprocess,time,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
OUT=str(ROOT/"raw"/"yt")
os.makedirs(OUT,exist_ok=True)
_collection=Path(os.environ.get("BGG_COLLECTION", ROOT/"raw"/"Scorpy311_owned_games.json"))
items=json.load(open(_collection))['items']
def clean(t):
    t=re.sub(r'\s*\((?:[^()]|\([^()]*\))*\)\s*$','',t).strip()
    return t
for it in items:
    p=f"{OUT}/{it['id']}.json"
    if os.path.exists(p): continue
    n=clean(it['title'])
    res={}
    for q in [f"how to play {n} board game", f"Watch It Played {n}"]:
        try:
            o=subprocess.run([os.environ.get("YT_DLP","yt-dlp"),"--flat-playlist","-j",f"ytsearch12:{q}"],capture_output=True,text=True,timeout=90).stdout
            res[q]=[{k:d.get(k) for k in("id","title","channel","duration","view_count")} for d in map(json.loads,o.splitlines()) ]
        except Exception as e: res[q]=str(e)
        time.sleep(2)
    json.dump({"name":n,"results":res},open(p,"w"))
    print("done",it['id'],n,flush=True)
