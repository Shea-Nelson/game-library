import json,re,os,time,urllib.request,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
B=str(ROOT); RAW=B+"/raw"
_collection=Path(os.environ.get("BGG_COLLECTION", ROOT/"raw"/"Scorpy311_owned_games.json"))
items=json.load(open(_collection))['items']
OUT=B+"/work/videos.json"; OE=B+"/work/oembed_cache.json"
res=json.load(open(OUT)) if os.path.exists(OUT) else {}
OVR=json.load(open(B+"/work/video_overrides.json")); NULLR={}
oe=json.load(open(OE)) if os.path.exists(OE) else {}
STOP=set("the a an of and game board card edition english deluxe second 2nd third 3rd retail standard multilingual includes expansions extra salt pepper".split())
PREF={"watch it played":60,"rodney smith":60,"meeple university":50,"the dice tower":45,"dice tower":45}
HOW=re.compile(r"how to play|how-to-play|how 2 play|learn to play|rules|teach|tutorial|in \d+ min|explained|instructions",re.I)
BAD=re.compile(r"review|unboxing|top \d+|vs\.? |live stream|stream|reaction|playthrough only",re.I)
def norm(s): return re.sub(r"[^a-z0-9 ]"," ",s.lower().replace("&"," and ").replace("'","").replace("’",""))
def toks(s): return [w for w in norm(s).split() if w not in STOP]
def oembed(vid):
    if vid in oe: return oe[vid]
    u="https://www.youtube.com/oembed?format=json&url="+urllib.parse.quote(f"https://www.youtube.com/watch?v={vid}")
    try:
        d=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=20))
        oe[vid]={"title":d.get("title"),"channel":d.get("author_name"),"channelUrl":d.get("author_url")}
    except Exception as e: oe[vid]={"error":str(e)}
    time.sleep(0.3); return oe[vid]
def clean(t): return re.sub(r'\s*\((?:[^()]|\([^()]*\))*\)\s*$','',t).strip()
for it in items:
    i=it['id']
    if i in res and not os.environ.get("FORCE"): continue
    if not os.path.exists(f"{RAW}/{i}.item.json") or not os.path.exists(f"{RAW}/yt/{i}.json"): continue
    item=json.load(open(f"{RAW}/{i}.item.json"))['item']
    pubs=[x['name'] for x in item['links'].get('boardgamepublisher',[])]
    names={clean(it['title']),item['name']}
    isexp='boardgameexpansion' in item.get('subtypes',[])
    for n in (list(names) if not isexp else []):
        if ':' in n:
            pre=n.split(':')[0]
            if len(toks(pre))>=1 and len(pre)>=6: names.add(pre)
    tokset=[t for t in (toks(n) for n in names) if t]
    def matches(title):
        tt=' '+' '.join(w for w in norm(title).split() if w not in STOP)+' '
        return any(' '+' '.join(ts)+' ' in tt for ts in tokset)
    fullname=norm(it['title'])
    NEG=re.compile(r"drinking|guitar|riff|minecraft|roblox|this war of mine|video game|fortnite battle royale|español|italiano|deutsch|en français|tutorial \d+|regole|\ble jeu\b|règles",re.I)
    def edition_ok(t):
        m=re.search(r"(\w+) edition",t,re.I)
        return not m or m.group(1).lower() in fullname.split() or m.group(1).lower() in norm(item['name']).split()
    cands={}
    bv=(json.load(open(f"{RAW}/{i}.videos.json")) if os.path.exists(f"{RAW}/{i}.videos.json") else {}).get('videos',[])
    bv=[v for v in bv if v.get('videohost')=='youtube' and v.get('language')=='English']
    bv.sort(key=lambda v:-int(v.get('numrecommend') or 0))
    for v in bv[:6]:
        o=oembed(v['extvideoid'])
        if 'error' in o: continue
        cands[v['extvideoid']]={"id":v['extvideoid'],"title":o['title'],"channel":o['channel'],"channelUrl":o.get('channelUrl'),"bgg":True,"bggRec":int(v.get('numrecommend') or 0),"duration":None,"views":0}
    yt=json.load(open(f"{RAW}/yt/{i}.json"))['results']
    for q,lst in yt.items():
        if not isinstance(lst,list): continue
        for v in lst:
            if not v.get('id') or not v.get('title'): continue
            c=cands.setdefault(v['id'],{"id":v['id'],"title":v['title'],"channel":v.get('channel'),"bgg":False,"bggRec":0})
            c['duration']=v.get('duration') or c.get('duration'); c['views']=v.get('view_count') or c.get('views') or 0
            c['channel']=c.get('channel') or v.get('channel')
    scored=[]
    for c in cands.values():
        t=c['title'] or ''
        if not matches(t): continue
        if NEG.search(t) or not edition_ok(t): continue
        if not HOW.search(t): continue
        if BAD.search(t) and not re.search(r"how to play",t,re.I): continue
        if c.get('duration') and c['duration']<90: continue
        ch=(c.get('channel') or '').lower(); s=0; pref=None
        for k,v in PREF.items():
            if k in ch: s+=v; pref="preferred"; break
        pubhit=any(len(p)>3 and (norm(p).split()[0] in norm(ch).split()) for p in pubs if norm(p).split()) and ch
        if pubhit and not pref: s+=45; pref="publisher"
        if c['bgg']: s+=15+min(c['bggRec'],30)/3
        if re.search(r"how to play",t,re.I): s+=15
        if matches(t): s+=10
        s+=min((c.get('views') or 0)/100000,10)
        scored.append((s,pref,c))
    scored.sort(key=lambda x:-x[0])
    ov=OVR.get(i,{})
    if 'id' in ov:
        if ov['id'] is None:
            res[i]=None; NULLR[i]=ov.get('reason'); print(i,'-> override null'); json.dump(res,open(OUT,"w"),indent=1); continue
        c=cands.get(ov['id'],{"id":ov['id'],"bgg":False,"duration":None})
        scored=[(999,None,c)]
    pick=None
    for s,pref,c in scored[:3]:
        o=oembed(c['id'])
        if 'error' in o: continue
        pick={"youtubeId":c['id'],"url":f"https://www.youtube.com/watch?v={c['id']}","title":o['title'],"channel":o['channel'],"channelUrl":o.get('channelUrl'),
              "durationSec":c.get('duration'),"channelType":pref or "other","listedOnBGG":c['bgg'],"verified":True,
              "titleMatchesGame":matches(o['title']),"kind":ov.get('kind','how-to-play')}
        if ov.get('note'): pick['note']=ov['note']
        if 'id' in ov: pick['manuallyReviewed']=True
        ch=(o['channel'] or '').lower()
        for k in PREF:
            if k in ch: pick['channelType']='preferred'
        if any(norm(p).split() and norm(p).split()[0] in norm(ch).split() for p in pubs): pick['channelType']=pick['channelType'] if pick['channelType']=='preferred' else 'publisher'
        break
    res[i]=pick
    print(i,clean(it['title']),'->',(pick or {}).get('channel'),'|',(pick or {}).get('title'),flush=True)
    json.dump(res,open(OUT,"w"),indent=1); json.dump(oe,open(OE,"w"))
json.dump(NULLR,open(B+"/work/video_null_reasons.json","w"),indent=1)
