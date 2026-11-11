#!/usr/bin/env python3
"""Build data/videogames.json from Shea's Steam library.

Reads the Steam GetOwnedGames dump from STEAM_OWNED, or from
raw/steam/owned_games.json under the repo root if that is unset (does not
modify the file unless --refresh-owned is passed). Optionally re-pulls owned
games with --refresh-owned if STEAM_API_KEY is set in the environment. The
key is never printed, written, or copied into the site.

Store genres and release years come from the public Steam appdetails API
(no key). Results are cached in work/steam/appdetails/ (gitignored).
Be polite: one request at a time, with a delay and 429 backoff.

Usage:
  python3 scripts/build_videogames.py
  python3 scripts/build_videogames.py --refresh-store
  python3 scripts/build_videogames.py --refresh-owned
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OWNED = Path(os.environ.get("STEAM_OWNED", ROOT / "raw" / "steam" / "owned_games.json"))
CACHE_DIR = ROOT / "work" / "steam" / "appdetails"
OUT_JSON = ROOT / "data" / "videogames.json"
OUT_JS = ROOT / "js" / "videogames-data.js"
STEAM_ID = "76561197970277783"
ET = ZoneInfo("America/New_York")

UA = "Mozilla/5.0 (compatible; SheaGameShelf/1.0; +https://shea-nelson.github.io/game-library/)"
STORE_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json",
    "Cookie": "birthtime=0; mature_content=1; wants_mature_content=1; lastagecheckage=1-0-1980",
}


def now_et_iso():
    return datetime.now(ET).strftime("%Y-%m-%dT%H:%M%z").replace("-0500", "-05:00").replace("-0400", "-04:00")


def strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def parse_year(date_str: str):
    if not date_str:
        return None
    m = re.search(r"(19|20)\d{2}", date_str)
    return int(m.group(0)) if m else None


def load_owned(path: Path):
    data = json.loads(path.read_text())
    games = data["response"]["games"]
    return games


def refresh_owned(path: Path):
    key = os.environ.get("STEAM_API_KEY")
    if not key:
        sys.exit("STEAM_API_KEY is not set; cannot refresh owned games.")
    # Do not log the URL (it would contain the key).
    qs = urllib.parse.urlencode(
        {
            "key": key,
            "steamid": STEAM_ID,
            "include_appinfo": 1,
            "include_played_free_games": 1,
            "format": "json",
        }
    )
    url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/?" + qs
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.loads(r.read().decode())
    finally:
        # Drop key from locals as soon as the request is done.
        del key, qs, url, req
    games = payload.get("response", {}).get("games")
    if not games:
        sys.exit("Steam GetOwnedGames returned no games.")
    # Write next to the default source only if the caller pointed at it;
    # never write into the site folder.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    print(f"refreshed owned games: {len(games)}", file=sys.stderr)
    return games


def fetch_store(appid: int, delay: float, retries: int = 5):
    cache = CACHE_DIR / f"{appid}.json"
    if cache.exists():
        return json.loads(cache.read_text()), False
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}&l=english"
    wait = delay
    for attempt in range(retries):
        time.sleep(wait)
        req = urllib.request.Request(url, headers=STORE_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                payload = json.loads(r.read().decode())
            cache.write_text(json.dumps(payload))
            return payload, True
        except urllib.error.HTTPError as e:
            if e.code in (429, 403, 503) and attempt < retries - 1:
                wait = max(delay, 8) * (attempt + 2)
                print(f"  appid {appid}: HTTP {e.code}, backing off {wait:.0f}s", file=sys.stderr)
                continue
            print(f"  appid {appid}: HTTP {e.code}, skipping store details", file=sys.stderr)
            return None, True
        except Exception as e:
            if attempt < retries - 1:
                wait = delay * (attempt + 2)
                print(f"  appid {appid}: {e}, retrying", file=sys.stderr)
                continue
            print(f"  appid {appid}: {e}, skipping store details", file=sys.stderr)
            return None, True
    return None, True


def store_fields(appid: int, payload):
    out = {
        "type": None,
        "year": None,
        "genres": [],
        "shortDescription": "",
        "developers": [],
        "publishers": [],
        "comingSoon": False,
    }
    if not payload:
        return out
    entry = payload.get(str(appid)) or {}
    if not entry.get("success"):
        return out
    d = entry.get("data") or {}
    out["type"] = d.get("type") or None
    rd = d.get("release_date") or {}
    out["comingSoon"] = bool(rd.get("coming_soon"))
    out["year"] = parse_year(rd.get("date") or "")
    genres = []
    for g in d.get("genres") or []:
        name = (g.get("description") or "").strip()
        if name and name not in genres:
            genres.append(name)
    out["genres"] = genres
    out["shortDescription"] = strip_html(d.get("short_description") or "")
    out["developers"] = [x for x in (d.get("developers") or []) if x]
    out["publishers"] = [x for x in (d.get("publishers") or []) if x]
    return out


def build_record(g, details):
    minutes = int(g.get("playtime_forever") or 0)
    last = int(g.get("rtime_last_played") or 0)
    appid = int(g["appid"])
    name = g.get("name") or f"Steam app {appid}"
    rec = {
        "id": f"steam-{appid}",
        "platform": "pc",
        "store": "steam",
        "appid": appid,
        "name": name,
        "minutesPlayed": minutes,
        "hoursPlayed": round(minutes / 60, 1),
        "lastPlayed": last if last > 0 else None,
        "neverPlayed": minutes == 0,
        "year": details.get("year"),
        "comingSoon": details.get("comingSoon") or False,
        "genres": details.get("genres") or [],
        "type": details.get("type") or "game",
        "shortDescription": details.get("shortDescription") or "",
        "developers": details.get("developers") or [],
        "publishers": details.get("publishers") or [],
        "image": {
            "portrait": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_600x900.jpg",
            "header": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg",
            "capsule": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/capsule_616x353.jpg",
        },
        "storeUrl": f"https://store.steampowered.com/app/{appid}/",
    }
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owned", type=Path, default=DEFAULT_OWNED, help="Path to GetOwnedGames JSON")
    ap.add_argument("--refresh-owned", action="store_true", help="Re-pull owned games (needs STEAM_API_KEY)")
    ap.add_argument("--refresh-store", action="store_true", help="Ignore store-details cache and re-fetch")
    ap.add_argument("--delay", type=float, default=1.25, help="Seconds between store API calls")
    ap.add_argument("--skip-store", action="store_true", help="Do not call the store API")
    args = ap.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if args.refresh_store:
        for p in CACHE_DIR.glob("*.json"):
            p.unlink()

    if args.refresh_owned:
        games = refresh_owned(args.owned)
    else:
        if not args.owned.exists():
            sys.exit(f"Owned-games file not found: {args.owned}")
        games = load_owned(args.owned)

    games = sorted(games, key=lambda g: (g.get("name") or "").lower())
    fetched = 0
    records = []
    with_genres = 0
    with_year = 0
    for i, g in enumerate(games, 1):
        appid = int(g["appid"])
        details = {
            "type": None,
            "year": None,
            "genres": [],
            "shortDescription": "",
            "developers": [],
            "publishers": [],
            "comingSoon": False,
        }
        if not args.skip_store:
            payload, did_fetch = fetch_store(appid, args.delay)
            if did_fetch:
                fetched += 1
                print(f"[{i}/{len(games)}] fetched store details for {appid} {g.get('name')}", file=sys.stderr)
            details = store_fields(appid, payload)
        rec = build_record(g, details)
        if rec["genres"]:
            with_genres += 1
        if rec["year"]:
            with_year += 1
        records.append(rec)

    # Keep previously built Switch records so a Steam rebuild does not wipe them.
    switch_records = []
    switch_cache = ROOT / "work" / "switch" / "records.json"
    if switch_cache.exists():
        try:
            switch_records = json.loads(switch_cache.read_text())
        except Exception:
            switch_records = []
    records = [r for r in records if r.get("platform") != "switch2"] + switch_records

    generated = now_et_iso()
    with_genres = sum(1 for r in records if r.get("genres"))
    with_year = sum(1 for r in records if r.get("year"))
    payload = {
        "generated": generated,
        "source": "Steam GetOwnedGames for profile LordScorpy (SteamID 76561197970277783)"
        + ("; Nintendo Switch library from scripts/switch_catalog.json" if switch_records else ""),
        "note": "PC box art is hotlinked from Steam's public CDN, with header and capsule fallbacks. Switch box art is hotlinked from Nintendo's official store CDN when a matching product page was found. Genres and release years for PC games come from the public Steam store appdetails API. Switch store links are included only when verified.",
        "stats": {
            "generated": generated,
            "total": len(records),
            "pc": sum(1 for r in records if r["platform"] == "pc"),
            "switch2": sum(1 for r in records if r["platform"] == "switch2"),
            "played": sum(1 for r in records if r.get("neverPlayed") is False),
            "neverPlayed": sum(1 for r in records if r.get("neverPlayed") is True),
            "withGenres": with_genres,
            "withYear": with_year,
            "totalMinutes": sum(r.get("minutesPlayed") or 0 for r in records),
        },
        "games": records,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    OUT_JS.parent.mkdir(parents=True, exist_ok=True)
    OUT_JS.write_text(
        "/* Fallback copy of data/videogames.json for file:// viewing. Regenerate when data changes. */\n"
        "window.VIDEOGAMES_DATA="
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    s = payload["stats"]
    print(
        f"wrote {len(records)} video games "
        f"({s['played']} played, {s['neverPlayed']} never, "
        f"{s['withGenres']} genres, {s['withYear']} years) "
        f"fetched={fetched}"
    )


if __name__ == "__main__":
    main()
