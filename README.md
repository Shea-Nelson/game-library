# Shea's Game Shelf

A static, filterable library of the Nelson family's board games: box art, player counts, play time, weight, rulebooks, errata, guides, house rules, and how-to-play videos.

Live site: GitHub Pages repo `Shea-Nelson/game-library`.

The earlier Board Game Collection & Davenport Picks page now lives at [`davenport/`](davenport/).

## How it works
- `index.html`, `css/style.css`, `js/app.js`: plain HTML/CSS/JS. No build step, no dependencies, no secrets. Every path is relative.
- `data/games.json`: one object per base game, with its expansions nested inside. The page loads this file with `fetch`. If that fails (for example, opening the file straight from disk), it falls back to `js/games-data.js`, a copy of the same data.
- `data/coverage.json` / `data/COVERAGE.md`: data snapshot date and coverage stats.
- `img/<bggid>.jpg`: box art downloaded from BoardGameGeek.
- Detail views use shareable hash links, for example `#game/171131-captain-sonar`.
- Theme: light by default. A toggle switches to dark mode and remembers the choice in `localStorage`. Respects `prefers-reduced-motion`.
- Videos load only on click, through `youtube-nocookie.com`.
- Links that could not be confirmed automatically carry `verified: false` and show a "Not verified" badge.

## Updating the data
The data scripts in `scripts/` (fetch from BGG, YouTube search, video picks, images, build, coverage) write `data/games.json`. Their caches (`raw/`, `work/`) are git-ignored. The scripts resolve paths from the repo root. Optional environment variables:

- `BGG_COLLECTION` — path to the owned-games JSON (defaults to `raw/Scorpy311_owned_games.json`)
- `BGG_IDS` — path to the id list used by `scripts/images.py` (defaults to `ids.txt`)
- `YT_DLP` — `yt-dlp` executable (defaults to `yt-dlp` on `PATH`)
- `CANVAS_VARIANTS_SRC` — Canvas source file for `scripts/canvas_variants.py` (defaults to `work/source.canvas.tsx`) After rebuilding, regenerate the fallback:

```sh
python3 -c "import json;g=json.load(open('data/games.json'));m=json.load(open('data/coverage.json'));open('js/games-data.js','w').write('window.GAMES_DATA='+json.dumps(g,ensure_ascii=False,separators=(',',':'))+';\nwindow.GAMES_META='+json.dumps({'stats':{'generated':m['stats']['generated']}})+';\n')"
```

To preview locally, run `python3 -m http.server` in this folder.

## Credits
Game data, box art, player polls, weights, files, and forums: [BoardGameGeek](https://boardgamegeek.com) (collection: Scorpy311). Rulebooks link to publishers where we found them. Videos are hosted on YouTube by their creators. BGG file downloads need a free BGG login. Stark keeps this page up to date.
