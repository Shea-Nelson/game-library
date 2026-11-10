"""Apply scripts/edition_overrides.json to data/games.json (idempotent) and regenerate js/games-data.js."""
import json
from pathlib import Path
B=str(Path(__file__).resolve().parent.parent)
ov=json.load(open(B+"/scripts/edition_overrides.json"))
g=json.load(open(B+"/data/games.json"))
def walk(items):
    for x in items:
        o=ov.get(str(x['bggId']))
        if o:
            x.update({k:v for k,v in o.items() if not k.startswith('_')})
        walk(x.get('expansions') or [])
walk(g)
json.dump(g,open(B+"/data/games.json","w"),indent=1,ensure_ascii=False)
m=json.load(open(B+"/data/coverage.json"))
open(B+"/js/games-data.js","w").write("/* Fallback copy of data/games.json for file:// viewing. Regenerate when data changes. */\nwindow.GAMES_DATA="+json.dumps(g,ensure_ascii=False,separators=(',',':'))+";\nwindow.GAMES_META="+json.dumps({'stats':{'generated':m['stats']['generated']}})+";\n")
print("applied",len(ov),"overrides")
