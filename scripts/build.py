import json,re,os,html,glob
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
B=str(ROOT); RAW=B+"/raw"
_collection=Path(os.environ.get("BGG_COLLECTION", ROOT/"raw"/"Scorpy311_owned_games.json"))
items=json.load(open(_collection))['items']
title_by_id={i['id']:i['title'] for i in items}
def J(i,k):
    p=f"{RAW}/{i}.{k}.json"
    try: return json.load(open(p))
    except Exception: return None
def clean_title(t):
    m=re.match(r'^(.*?)\s*\(((?:[^()]|\([^()]*\))*)\)\s*$',t)
    return (m.group(1).strip(),m.group(2).strip()) if m else (t.strip(),None)
def slug(href): return href
def strip_html(s): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s or ''))).strip()

pubman=json.load(open(B+"/work/publisher_manuals.json"))
pmchk=json.load(open(B+"/work/pm_check.json"))
canvaschk=json.load(open(B+"/work/canvas_urls_check.json"))
videos=json.load(open(B+"/work/videos.json")) if os.path.exists(B+"/work/videos.json") else {}
imgs=json.load(open(B+"/work/images.json")) if os.path.exists(B+"/work/images.json") else {}
canvas=json.load(open(B+"/work/canvas_variants.json"))
nullr=json.load(open(B+"/work/video_null_reasons.json")) if os.path.exists(B+"/work/video_null_reasons.json") else {}
extras=json.load(open(B+"/work/curated_extras.json")); cechk=json.load(open(B+"/work/ce_check.json"))

RULE_RX=re.compile(r'\b(rule ?book|rules|manual|instructions|how to play booklet)\b',re.I)
NOT_RULE_RX=re.compile(r'summary|reference|aid|cheat|sheet|handout|variant|house|solo|fan|custom|print|insert|organizer|score|tracker|card list|translation|faq|errata|clarif|quick|teach|guide|overview|one ?page|1sheet|script|player board|tile|jacket|reformat|redesign|simplif|unofficial|homebrew|v\d+ ?-? ?redone|russian|german|french|spanish|italian|polish|portuguese only|dutch|czech|hungarian|automa|estonian|finnish|swedish|norwegian|danish|greek|turkish|romanian|japanese|korean|chinese|hebrew|expansion|solitaire|flowchart|interpreted|preview|appendix|reminder|pocketmod|\bks v',re.I)
ERRATA_RX=re.compile(r'\b(errata|faq|f\.a\.q|clarifications?|rules? questions|corrections?)\b',re.I)
GUIDE_RX=re.compile(r'\b(rules? summary|summary|reference|player aid|teaching|teach|quick ?start|guide|cheat ?sheet|overview|how to play|walkthrough|tutorial)\b',re.I)
def ftxt(f): return f"{f.get('title','')} {f.get('filename','')}"
def filepage(f): return "https://boardgamegeek.com"+f['href']

def pick_files(i,name):
    fs=[f for f in (J(i,'files') or {}).get('files',[]) if f.get('language')=='English']
    rules=[f for f in fs if RULE_RX.search(ftxt(f)) and not NOT_RULE_RX.search(ftxt(f))]
    errata=[f for f in fs if ERRATA_RX.search(ftxt(f))]
    guides=[f for f in fs if GUIDE_RX.search(ftxt(f)) and f not in errata]
    key=lambda f:-int(f.get('numpositive') or 0)
    return sorted(rules,key=key),sorted(errata,key=key),sorted(guides,key=key)

def link(url,title,source,verified,note=None,**kw):
    d={"url":url,"title":title,"source":source,"verified":verified}
    if note: d["note"]=note
    d.update(kw); return d

def best_players(dyn):
    try:
        pl=dyn['item']['polls']['userplayers']
        def rng(lst):
            out=[]
            for r in lst:
                a,b=r['min'],r['max']; out.append(str(a) if a==b else f"{a}-{b}")
            return ", ".join(out) or None
        return rng(pl.get('best',[])),rng(pl.get('recommended',[])),int(pl.get('totalvotes') or 0)
    except Exception: return None,None,0

def build(i):
    it=(J(i,'item') or {}).get('item')
    if not it: return None
    dyn=J(i,'dyn') or {}
    disp,edition=clean_title(title_by_id.get(i,it['name']))
    href=it['href']; bggurl="https://boardgamegeek.com"+href
    L=it.get('links',{})
    cats=[x['name'] for x in L.get('boardgamecategory',[])]
    mechs=[x['name'] for x in L.get('boardgamemechanic',[])]
    pubs=[x['name'] for x in L.get('boardgamepublisher',[])]
    desigs=[x['name'] for x in L.get('boardgamedesigner',[])]
    best,rec,votes=best_players(dyn)
    st=(dyn.get('item') or {}).get('stats',{})
    polls=(dyn.get('item') or {}).get('polls',{})
    try: weight=round(float(st.get('avgweight')),2) if float(st.get('avgweight') or 0)>0 else None
    except Exception: weight=None
    rank=None
    for r in (dyn.get('item') or {}).get('rankinfo',[]):
        if r.get('veryshortprettyname')=='Overall' and r.get('rank') and r['rank'].isdigit(): rank=int(r['rank'])
    def num(x):
        try: n=int(x); return n if n>0 else None
        except Exception: return None
    rules,errata,guides=pick_files(i,it['name'])
    files_page=bggurl+"/files"
    # manual
    manual=None
    if i in pubman:
        pm=pubman[i]; c=pmchk.get(pm['url'],{})
        ok=c.get('code','').startswith('20') and c.get('code')!='202' and ('pdf' in c.get('ctype','') or (pm.get('page') and 'html' in c.get('ctype','')))
        if ok or pm.get('keep_unverified'):
            manual=link(pm['url'],pm['title'],"publisher",ok,pm.get('note'))
        elif c.get('code') in ('403','503'):
            manual=link(pm['url'],pm['title'],"publisher",False,(pm.get('note','')+" Publisher site blocked our automated check (HTTP %s); link not confirmed."%c.get('code')).strip())
    if not manual and rules:
        f=rules[0]; manual=link(filepage(f),f['title'],"bgg_file",True,"User-uploaded rulebook on BGG (free BGG login needed to download).")
    if not manual:
        manual=link(files_page,"BGG files page","bgg_files_page",True,"No publisher PDF found; check BGG files.")
    errs=[]
    for f in errata[:2]:
        errs.append(link(filepage(f),f['title'],"bgg_file",True,"Uploaded by a BGG user; not an official publisher document.",official=False))
    for c in extras['errata'].get(i,[])[::-1]:
        errs.insert(0,link(c['url'],c['title'],"publisher" if c.get('official') else "web",cechk.get(c['url'],{}).get('code','').startswith('20'),official=c.get('official',False)))
    gl=[link(c['url'],c['title'],"web",cechk.get(c['url'],{}).get('code','').startswith('20')) for c in extras['guides'].get(i,[])]
    for f in guides[:2]: gl.append(link(filepage(f),f['title'],"bgg_file",True))
    forums={f['title']:f for f in (J(i,'forums') or {}).get('forums',[])}
    def forum(t):
        f=forums.get(t); 
        return link(f"{bggurl}/forums/{f['forumid']}",f"BGG {t} forum ({f['numthreads']} threads)","bgg_forum",True,threads=f['numthreads']) if f else None
    sf=forum("Strategy"); vf=forum("Variants"); rf=forum("Rules")
    if sf and sf.get('threads',0)>0: gl.append(sf)
    img=imgs.get(i,{})
    return {
      "bggId":int(i),"bggUrl":bggurl,"name":disp,"bggName":it['name'],"edition":edition,
      "year":num(it.get('yearpublished')),
      "image":{"local":img.get('local'),"remote":it.get('imageurl'),"thumb":(it.get('images') or {}).get('thumb')},
      "minPlayers":num(it.get('minplayers')),"maxPlayers":num(it.get('maxplayers')),
      "bestPlayers":best,"recommendedPlayers":rec,"playerPollVotes":votes,
      "minPlayTime":num(it.get('minplaytime')),"maxPlayTime":num(it.get('maxplaytime')),
      "minAge":num(it.get('minage')),"communityAge":polls.get('playerage') or None,
      "weight":weight,"weightVotes":num(st.get('numweights')),"bggRating":round(float(st['average']),2) if st.get('average') and float(st['average'])>0 else None,"bggRank":rank,
      "categories":cats,"mechanics":mechs,"designers":desigs[:3],"publisher":pubs[0] if pubs else None,
      "shortDescription":strip_html(it.get('short_description')) or None,
      "publisherSite":link(it['website']['url'],it['website'].get('title') or 'Publisher page',"bgg_listed",None,"Listed on BGG; not checked.") if (it.get('website') or {}).get('url') else None,
      "links":{"manual":manual,"filesPage":files_page,"errata":errs,"guides":gl,"rulesForum":rf,"variantsForum":vf},
      "houseRules":canvas.get(i,{}).get("variants",[]),"rulesMistakes":canvas.get(i,{}).get("mistakes",[]),
      "video":videos.get(i),"videoMissingReason":(nullr.get(i) or "No how-to-play video found for this game.") if not videos.get(i) else None,
      "isExpansion":'boardgameexpansion' in it.get('subtypes',[]),
      "expandsIds":[x['objectid'] for x in L.get('expandsboardgame',[])],
      "expansions":[],
    }

ids=[l.strip() for l in open(B+"/ids.txt")]
games={i:build(i) for i in ids}
owned=set(ids)
# related owned (integrations/implementations/reimplementations)
for i,g in games.items():
    it=J(i,'item')['item']; L=it['links']
    rel=set()
    for k in ('boardgameintegration','boardgameimplementation','reimplementation','reimplements'):
        for x in L.get(k,[]):
            if x['objectid'] in owned and x['objectid']!=i: rel.add(x['objectid'])
    g['relatedOwnedIds']=sorted(int(r) for r in rel)
for i,g in games.items():
    for r in g['relatedOwnedIds']:
        if int(i) not in games[str(r)]['relatedOwnedIds']: games[str(r)]['relatedOwnedIds'].append(int(i))
out=[]
for i,g in games.items():
    if g['isExpansion'] and any(b in owned for b in g['expandsIds']):
        continue
    out.append(g)
for i,g in games.items():
    if g['isExpansion']:
        base=[b for b in g['expandsIds'] if b in owned]
        if base:
            e={k:g[k] for k in ("bggId","bggUrl","name","bggName","edition","year","image","minPlayers","maxPlayers","minPlayTime","maxPlayTime","minAge","weight","shortDescription","links","video","houseRules")}
            games[base[0]]['expansions'].append(e)
for g in out:
    g.pop('expandsIds',None); g['expansionCount']=len(g['expansions'])
    # base player range including expansions
    mx=[e['maxPlayers'] for e in g['expansions'] if e.get('maxPlayers')]
    g['maxPlayersWithExpansions']=max([g['maxPlayers'] or 0]+mx) or None
out.sort(key=lambda g:re.sub(r'^(the|a) ','',g['name'].lower()))
os.makedirs(B+"/data",exist_ok=True)
json.dump(out,open(B+"/data/games.json","w"),indent=1,ensure_ascii=False)
print(len(out),"base games;",sum(len(g['expansions']) for g in out),"expansions nested")

# Edition fixes (art/year for the edition Shea owns) + regenerate js/games-data.js
import runpy; runpy.run_path(B+"/scripts/apply_overrides.py")
