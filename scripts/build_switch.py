#!/usr/bin/env python3
"""Add Shea's Nintendo Switch library to data/videogames.json.

Reads scripts/switch_catalog.json (titles transcribed from his Switch 2 photos).
Fetches official name, art, year, genres, and store URL from Nintendo.com when
a product page can be matched. Caches raw HTML/JSON in work/switch/pages/
(gitignored). Never invents store links.

Then merges those records with the existing PC (Steam) games in
data/videogames.json and regenerates js/videogames-data.js.

Usage:
  python3 scripts/build_switch.py
  python3 scripts/build_switch.py --refresh
"""
from __future__ import annotations

import argparse
import html as htmlmod
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from apply_created_art import apply_note, apply_to_records

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "scripts" / "switch_catalog.json"
CACHE_DIR = ROOT / "work" / "switch" / "pages"
OUT_JSON = ROOT / "data" / "videogames.json"
OUT_JS = ROOT / "js" / "videogames-data.js"
RECORDS_CACHE = ROOT / "work" / "switch" / "records.json"
ET = ZoneInfo("America/New_York")
UA = "Mozilla/5.0 (compatible; SheaGameShelf/1.0; +https://shea-nelson.github.io/game-library/)"
HEADERS = {"User-Agent": UA, "Accept": "text/html,application/json"}


def now_et_iso():
    return datetime.now(ET).strftime("%Y-%m-%dT%H:%M%z").replace("-0500", "-05:00").replace("-0400", "-04:00")


DLC_WORDS = {"dlc", "pack", "pass", "theme", "bundle", "demo", "trial", "expansion"}
STOP = {"the", "a", "an", "of", "and", "for", "to", "edition", "nintendo", "switch", "game", "games"}


def tokens(s: str) -> set[str]:
    s = (s or "").lower()
    s = s.replace("&", " and ").replace("+", " plus ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    out = set()
    for t in s.split():
        if not t:
            continue
        if t.isdigit():
            out.add(t)
            continue
        if t in STOP or len(t) <= 1:
            continue
        out.add(t)
    return out


def names_match(catalog_name: str, official: str) -> bool:
    if not official:
        return False
    a, b = tokens(catalog_name), tokens(official)
    if not a or not b:
        return False
    # "Heave Ho 2" must not match "Heave Ho"; keep numerals meaningful.
    nums_a = {t for t in a if t.isdigit()}
    nums_b = {t for t in b if t.isdigit()}
    if nums_a and not nums_a.issubset(nums_b):
        return False
    if nums_b and not nums_a and nums_b - {"1"}:
        # Official is a numbered sequel or DLC the catalog name didn't ask for
        return False
    if (b & DLC_WORDS) and not (a & DLC_WORDS):
        return False
    # Catalog tokens should be present on the official page title. Extra words are
    # allowed only when they are generic edition filler, not a DLC or expansion subtitle.
    allow_extra = {"console", "standard", "digital", "hd", "collection", "remaster", "remastered", "definitive", "complete", "royal", "bonus"}
    if a <= b:
        extra = b - a - DLC_WORDS
        return extra <= allow_extra
    if b <= a:
        # Official is shorter; only OK when dropped words are generic edition filler
        # (e.g. "Bonus Edition"). Do not match "Prototype Missions" to the full game.
        extra = a - b - allow_extra
        return not extra
    return False


def fetch_url(url: str, dest: Path, delay: float, retries: int = 4):
    if dest.exists():
        return dest.read_text(errors="replace"), dest.suffix, False
    wait = delay
    last = None
    for attempt in range(retries):
        time.sleep(wait)
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                raw = r.read()
            # prefer text
            text = raw.decode("utf-8", "replace")
            dest.write_text(text)
            return text, ".html", True
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 404:
                dest.write_text("HTTP 404")
                return None, "404", True
            if e.code in (429, 403, 503) and attempt < retries - 1:
                wait = max(delay, 6) * (attempt + 2)
                print(f"  HTTP {e.code} for {url}, backing off {wait:.0f}s", file=sys.stderr)
                continue
            print(f"  HTTP {e.code} for {url}", file=sys.stderr)
            return None, "err", True
        except Exception as e:
            last = e
            if attempt < retries - 1:
                wait = delay * (attempt + 2)
                continue
            print(f"  {type(e).__name__} for {url}: {e}", file=sys.stderr)
            return None, "err", True
    return None, "err", True


def extract_product(html: str, expected_name: str):
    if not html or html.startswith("HTTP 404"):
        return None
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    page = (data.get("props") or {}).get("pageProps", {}) or {}
    apollo = page.get("initialApolloState") or {}
    # Prefer the page's primary product (the one this URL is actually for).
    primary_sku = ((page.get("analytics") or {}).get("product") or {}).get("sku")
    primary = apollo.get(f'Product:{{"sku":"{primary_sku}"}}') if primary_sku else None
    candidates = []
    if isinstance(primary, dict) and primary.get("__typename") == "Product":
        candidates.append(primary)
    for key, val in apollo.items():
        if not isinstance(val, dict) or val.get("__typename") != "Product":
            continue
        if val is primary:
            continue
        candidates.append(val)
    def primary_ok(catalog_name, official):
        """Accept the page's own product when the official title contains the
        catalog tokens, even if Nintendo uses a longer original name."""
        if not official:
            return False
        a, b = tokens(catalog_name), tokens(official)
        if not a or not b:
            return False
        nums_a = {t for t in a if t.isdigit()}
        nums_b = {t for t in b if t.isdigit()}
        if nums_a and not nums_a.issubset(nums_b):
            return False
        if nums_b and not nums_a and nums_b - {"1"}:
            return False
        if (b & DLC_WORDS) and not (a & DLC_WORDS):
            return False
        return a <= b or names_match(catalog_name, official)

    best = None
    for i, val in enumerate(candidates):
        name = val.get("name") or ""
        ok = primary_ok(expected_name, name) if (i == 0 and primary is val) else names_match(expected_name, name)
        if not ok:
            continue
        if i == 0 and primary is val:
            best = val
            break
        if best is None:
            best = val
    if not best:
        return None
    tags = best.get("tags") or {}
    genres = []
    for g in (tags.get("genres") or []):
        label = (g.get("label") or "").strip()
        if label and label not in genres:
            genres.append(label)
    img = None
    pi = best.get("productImage") or {}
    if isinstance(pi, dict) and pi.get("url"):
        img = pi["url"]
    square = best.get('productImage({"shape":"square"})') or {}
    square_url = square.get("url") if isinstance(square, dict) else None
    year = None
    rd = best.get("releaseDate") or ""
    ym = re.search(r"(19|20)\d{2}", rd)
    if ym:
        year = int(ym.group(0))
    platforms = []
    for p in best.get("platforms") or []:
        lab = (p.get("label") or "").strip()
        if lab:
            platforms.append(lab)
    rel = best.get("url({\"relative\":true})") or ""
    store = ("https://www.nintendo.com" + rel) if rel.startswith("/") else None
    dev = best.get("softwareDeveloper") or None
    if isinstance(dev, str) and dev.startswith("http"):
        dev = None
    pub = best.get("softwarePublisher") or None
    desc = best.get("headline") or ""
    # longer description if present
    longd = best.get('description({"html":true})') or ""
    if isinstance(longd, str):
        longd = re.sub(r"<br\s*/?>", "\n", longd, flags=re.I)
        longd = re.sub(r"<[^>]+>", "", longd)
        longd = htmlmod.unescape(longd).strip()
    short = (desc or longd or "").strip()
    if len(short) > 600:
        short = short[:597].rsplit(" ", 1)[0] + "…"
    return {
        "officialName": best.get("name"),
        "year": year,
        "genres": genres,
        "developers": [dev] if dev else [],
        "publishers": [pub] if pub else [],
        "shortDescription": short,
        "imageHeader": img,
        "imageSquare": square_url,
        "storeUrl": store,
        "platforms": platforms,
        "urlKey": best.get("urlKey"),
    }


def lookup(entry, delay, refresh):
    slugs = list(entry.get("storeSlugs") or [])
    if entry.get("storeUrl"):
        m = re.search(r"/products/([^/]+)/?", entry["storeUrl"])
        if m and m.group(1) not in slugs:
            slugs.insert(0, m.group(1))
    fetched = 0
    for slug in slugs:
        cache = CACHE_DIR / f"{slug}.html"
        if refresh and cache.exists():
            cache.unlink()
        url = f"https://www.nintendo.com/us/store/products/{slug}/"
        html, status, did = fetch_url(url, cache, delay)
        if did:
            fetched += 1
        if status == "404" or not html:
            continue
        meta = extract_product(html, entry["name"])
        if meta and (meta.get("officialName") or meta.get("storeUrl")):
            return meta, fetched
    return None, fetched


def clean_name(s: str) -> str:
    s = (s or "").replace("™", "").replace("®", "").replace("©", "")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+([:!?])", r"\1", s)
    return s.strip()


def build_record(entry, meta):
    name = clean_name(entry["name"])
    store_url = None
    official = None
    year = None
    genres = []
    devs, pubs = [], []
    desc = ""
    header = None
    portrait = None
    if meta:
        official = clean_name(meta.get("officialName") or "")
        # Prefer the official Nintendo title, but keep a more specific catalog
        # subtitle when the official name is a shorter generic form.
        if official:
            ot, ct = tokens(official), tokens(name)
            if not (ot and ct and ot < ct):
                name = official
        store_url = meta.get("storeUrl") or None
        year = meta.get("year")
        genres = meta.get("genres") or []
        devs = meta.get("developers") or []
        pubs = meta.get("publishers") or []
        desc = meta.get("shortDescription") or ""
        header = meta.get("imageHeader")
        portrait = meta.get("imageSquare") or header
    else:
        # No verified page — do not keep a guessed store URL
        store_url = None
    rec = {
        "id": entry["id"],
        "platform": "switch2",
        "store": "nintendo",
        "appid": entry["id"],
        "name": name,
        "minutesPlayed": None,
        "hoursPlayed": None,
        "lastPlayed": None,
        "neverPlayed": None,
        "year": year,
        "comingSoon": False,
        "genres": genres,
        "type": entry.get("type") or "game",
        "shortDescription": desc,
        "developers": devs,
        "publishers": pubs,
        "image": {
            "portrait": portrait,
            "header": header,
            "capsule": None,
        },
        "storeUrl": store_url,
        "format": entry["format"],
        "switchFamily": entry.get("switchFamily"),
    }
    return rec


def merge_and_write(switch_records):
    if not OUT_JSON.exists():
        sys.exit(f"Missing {OUT_JSON}; run scripts/build_videogames.py first.")
    data = json.loads(OUT_JSON.read_text())
    pc = [g for g in data.get("games") or [] if g.get("platform") == "pc"]
    games = pc + switch_records
    apply_to_records(games)
    generated = now_et_iso()
    with_genres = sum(1 for g in games if g.get("genres"))
    with_year = sum(1 for g in games if g.get("year"))
    played = sum(1 for g in games if g.get("neverPlayed") is False)
    never = sum(1 for g in games if g.get("neverPlayed") is True)
    minutes = sum(g.get("minutesPlayed") or 0 for g in games)
    sw = [g for g in switch_records]
    payload = {
        "generated": generated,
        "source": (
            "Steam GetOwnedGames for profile LordScorpy (SteamID 76561197970277783); "
            "Nintendo Switch library transcribed from Shea's Switch 2 Virtual Game Cards "
            "and physical cartridge photos, with official titles, art, years, and store "
            "pages from Nintendo.com when a matching product page was found."
        ),
        "note": apply_note(
            "PC box art is hotlinked from Steam's public CDN, with header and capsule fallbacks. "
            "Switch box art is hotlinked from Nintendo's official store CDN (assets.nintendo.com) "
            "when a matching product page was found; otherwise the card uses a monogram. "
            "Store links are included only when the Nintendo.com page was verified. "
            "switchFamily is set only when the platform can be verified: "
            "switch2 (Switch 2 exclusive), switch2-edition, or switch1 (a Switch 1 game playing on Switch 2). "
            "The Legend of Zelda: Ocarina of Time was added at Shea's request; it is not on the VGC screens."
        ),
        "stats": {
            "generated": generated,
            "total": len(games),
            "pc": len(pc),
            "switch2": len(sw),
            "switchDigital": sum(1 for g in sw if g.get("format") == "Digital"),
            "switchPhysical": sum(1 for g in sw if g.get("format") == "Physical"),
            "switchBoth": sum(1 for g in sw if g.get("format") == "Both"),
            "switchFamilySwitch2": sum(1 for g in sw if g.get("switchFamily") in ("switch2", "switch2-edition")),
            "played": played,
            "neverPlayed": never,
            "withGenres": with_genres,
            "withYear": with_year,
            "totalMinutes": minutes,
        },
        "games": games,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    OUT_JS.write_text(
        "/* Fallback copy of data/videogames.json for file:// viewing. Regenerate when data changes. */\n"
        "window.VIDEOGAMES_DATA="
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    return payload["stats"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="Ignore the Nintendo page cache and re-fetch")
    ap.add_argument("--delay", type=float, default=1.15, help="Seconds between Nintendo.com requests")
    ap.add_argument("--skip-fetch", action="store_true", help="Rebuild from cached pages only")
    args = ap.parse_args()

    catalog = json.loads(CATALOG.read_text())
    entries = catalog["games"]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    fetched = 0
    with_page = 0
    with_art = 0
    with_year = 0
    with_genres = 0
    for i, entry in enumerate(entries, 1):
        meta = None
        if not args.skip_fetch:
            meta, n = lookup(entry, args.delay, args.refresh)
            fetched += n
        else:
            # still try cache
            meta, n = lookup(entry, 0, False)
        rec = build_record(entry, meta)
        if meta:
            with_page += 1
        if rec["image"]["header"] or rec["image"]["portrait"]:
            with_art += 1
        if rec["year"]:
            with_year += 1
        if rec["genres"]:
            with_genres += 1
        flag = "ok" if meta else "no-page"
        print(f"[{i}/{len(entries)}] {flag}  {rec['name']}", file=sys.stderr)
        records.append(rec)

    RECORDS_CACHE.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")
    stats = merge_and_write(records)
    print(
        f"wrote {stats['total']} video games "
        f"({stats['pc']} PC, {stats['switch2']} Switch; "
        f"{stats['switchDigital']} digital, {stats['switchPhysical']} physical, {stats['switchBoth']} both; "
        f"{with_page} Nintendo pages, {with_art} art, {with_genres} genres, {with_year} years; "
        f"fetched={fetched})"
    )


if __name__ == "__main__":
    main()
