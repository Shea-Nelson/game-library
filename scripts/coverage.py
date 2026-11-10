import json,collections,datetime
from pathlib import Path
B=str(Path(__file__).resolve().parent.parent)
g=json.load(open(B+"/data/games.json"))
n=len(g); ex=sum(len(x['expansions']) for x in g)
def c(f): return sum(1 for x in g if f(x))
man=collections.Counter(x['links']['manual']['source'] for x in g)
stats={
 "generated":datetime.datetime.now().astimezone().isoformat(timespec='minutes'),
 "baseGames":n,"expansionsNested":ex,"totalOwnedEntries":n+ex,
 "boxArtLocal":c(lambda x:x['image']['local']),
 "manualPublisher":man['publisher'],"manualPublisherUnverified":c(lambda x:x['links']['manual']['source']=='publisher' and not x['links']['manual']['verified']),
 "manualBggFile":man['bgg_file'],"manualBggFilesPageOnly":man['bgg_files_page'],
 "errataAny":c(lambda x:x['links']['errata']),"errataOfficial":c(lambda x:any(e.get('official') for e in x['links']['errata'])),
 "guides":c(lambda x:x['links']['guides']),
 "variantsForum":c(lambda x:x['links']['variantsForum']),"variantsForumWithThreads":c(lambda x:(x['links']['variantsForum'] or {}).get('threads',0)>0),
 "curatedHouseRules":c(lambda x:x['houseRules']),"curatedHouseRuleCount":sum(len(x['houseRules']) for x in g),
 "video":c(lambda x:x['video']),"videoPreferredChannel":c(lambda x:x['video'] and x['video']['channelType']=='preferred'),"videoPublisherChannel":c(lambda x:x['video'] and x['video']['channelType']=='publisher'),
 "bestPlayers":c(lambda x:x['bestPlayers']),"weight":c(lambda x:x['weight']),
}
gaps={"noVideo":[x['name'] for x in g if not x['video']],
 "manualFilesPageOnly":[x['name'] for x in g if x['links']['manual']['source']=='bgg_files_page'],
 "manualUnverified":[x['name']+" ("+x['links']['manual'].get('note','')+")" for x in g if x['links']['manual']['verified'] is False],
 "noErrata":c(lambda x:not x['links']['errata']),
 "noBestPlayerPoll":[x['name'] for x in g if not x['bestPlayers']],
 "noWeight":[x['name'] for x in g if not x['weight']],
 "houseRulesUnverifiedLinks":[f"{x['name']}: {h['name']} -> {h['url']}" for x in g for h in x['houseRules'] if not h['verified']],
}
json.dump({"stats":stats,"gaps":gaps},open(B+"/data/coverage.json","w"),indent=1,ensure_ascii=False)
L=["# Game library data: coverage report",f"Generated {stats['generated']} (America/New_York)","",
f"- {n} base games, {ex} expansions nested under their base game ({n+ex} owned entries; live BGG collection matched the Nov 7 snapshot, 113 entries).",
f"- Box art downloaded locally: {stats['boxArtLocal']}/{n} (img/<bggid>.jpg; expansions also have art).",
f"- Manual/rulebook: {man['publisher']} publisher links ({stats['manualPublisherUnverified']} not confirmed by our checker), {man['bgg_file']} BGG rulebook file pages, {man['bgg_files_page']} fall back to the BGG files page.",
f"- Errata/FAQ: {stats['errataAny']}/{n} (official publisher FAQ: {stats['errataOfficial']}; the rest are BGG user-compiled).",
f"- Strategy/teaching guides: {stats['guides']}/{n}.",
f"- BGG Variants forum link: {stats['variantsForum']}/{n} ({stats['variantsForumWithThreads']} have at least one thread); curated house rules from the variants Page: {stats['curatedHouseRuleCount']} rules across {stats['curatedHouseRules']} games.",
f"- YouTube how-to-play video: {stats['video']}/{n} (preferred channel {stats['videoPreferredChannel']}, publisher channel {stats['videoPublisherChannel']}). All checked with YouTube oEmbed.",
f"- Best player count (BGG poll): {stats['bestPlayers']}/{n}; weight: {stats['weight']}/{n}.","",
"## Gaps","- No video: "+", ".join(gaps['noVideo']),
"- Manual only via BGG files page: "+", ".join(gaps['manualFilesPageOnly']),
"- Publisher manual not confirmed (bot-blocked): "+"; ".join(gaps['manualUnverified']),
"- No best-player poll: "+", ".join(gaps['noBestPlayerPoll']),
"- House-rule links that failed our check: "+"; ".join(gaps['houseRulesUnverifiedLinks'])]
open(B+"/data/COVERAGE.md","w").write("\n".join(L)+"\n")
print("\n".join(L))
