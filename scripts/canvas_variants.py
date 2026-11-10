import re,json,os
from pathlib import Path
_src=Path(os.environ.get("CANVAS_VARIANTS_SRC", Path(__file__).resolve().parent.parent/"work"/"source.canvas.tsx"))
src=_src.read_text()
chk=json.load(open('work/canvas_urls_check.json'))
TAG={"F":"Family night","D":"Dawn & Lily day","B":"Davenport","T":"2-player"}
MAP={"Catan":["13"],"Ticket to Ride":["9209"],"Carcassonne":["822"],"Lost Ruins of Arnak":["312484"],"Quacks (All-In)":["441706"],"Quacks":["441706"],
"Cosmic Encounter":["39463"],"Avalon":["128882"],"Feed the Kraken":["271601"],"Captain Sonar":["171131"],"King of Tokyo":["336755"],"Western Legends":["232405"],
"Kingdomino":["204583"],"Patchwork":["163412"],"Castle Panic":["43443"],"Camel Up":["260605"],"Skull King":["150145"],"The Crew":["284083"],"Codenames":["178900"],
"Just One":["254640"],"Decrypto":["225694"],"Dixit (+ Odyssey)":["39856"],"One Night Ultimate Werewolf (+ Daybreak, Super Villains)":["147949"],
"Deception (+ Undercover Allies)":["156129"],"The Quest for El Dorado":["217372"],"Sea Salt & Paper":["468272"],"Flip 7 (+ With A Vengeance)":["420087"],
"Wandering Towers":["355483"],"Star Wars: The Deckbuilding Game":["374173"],"Thunder Road: Vendetta":["342070"],"Unstable Unicorns":["234190"],"Here to Slay":["299252"],
"Poetry for Neanderthals":["312786"],"Scrabble":["320"],"Skyjo":["204135"],"Skull":["92415"],"No Thanks!":["12942"],"Beat the Heat / Take 5":["432"],"Telestrations":["46213"],
"Monikers":["156546"],"Azul: Stained Glass of Sintra":["256226"],"Kites":["348096"],"Tapple":["129556"],"Catapult Feud":["310789"],"Rhino Hero: Super Battle":["218333"],"Munchkin Deluxe":["1927"]}
out={}
def ver(u):
    c=chk.get(u,{}); code=c.get('code','')
    return code.startswith('20') and code!='202'
vre=re.compile(r'\{ game: "(.*?)", name: "(.*?)", kind: "(.*?)", what: "(.*?)", tags: \[(.*?)\], src: "(.*?)" \}')
for g,n,k,w,t,s in vre.findall(src):
    tags=[TAG[x.strip()] for x in t.split(',') if x.strip()]
    for i in MAP[g]:
        out.setdefault(i,{"variants":[],"mistakes":[]})["variants"].append({"name":n,"kind":k,"description":w,"tags":tags,"url":s,"verified":ver(s)})
mre=re.compile(r'\["(.*?)", "(.*?)", "(.*?)"\]')
for g,m,s in mre.findall(src.split('const MISTAKES')[1].split('];')[0]):
    for i in MAP[g]:
        out.setdefault(i,{"variants":[],"mistakes":[]})["mistakes"].append({"text":m,"url":s,"verified":ver(s)})
json.dump(out,open('work/canvas_variants.json','w'),indent=1)
print(len(out),sum(len(v['variants']) for v in out.values()),sum(len(v['mistakes']) for v in out.values()))
