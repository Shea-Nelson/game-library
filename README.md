# Shea's Game Shelf

A static, filterable library of the Nelson family's board games and video games: box art, player counts, play time, weight, rulebooks, errata, guides, house rules, and how-to-play videos on the board-game side; hours played, store pages, genres, and release years on the PC side; and Digital / Physical badges plus verified Switch 2 or Switch 1 (playing on Switch 2) tags on the Nintendo side.

Live site: GitHub Pages repo `Shea-Nelson/game-library`.

The earlier Board Game Collection & Davenport Picks page now lives at [`davenport/`](davenport/).

## How it works
- `index.html`, `css/style.css`, `js/app.js`: plain HTML/CSS/JS. No build step, no dependencies, no secrets. Every path is relative.
- A Board games / Video games segmented control at the top of the sticky toolbar switches shelves. The choice is stored in `localStorage` (`gs-shelf`) and in the URL hash (`#board`, `#video`) so it can be linked and remembered. Board game details stay at `#game/<bggId>-<slug>`. Video game details use `#video/<appid>-<slug>`.
- `data/games.json`: one object per base board game, with its expansions nested inside. The page loads this file with `fetch`. If that fails (for example, opening the file straight from disk), it falls back to `js/games-data.js`, a copy of the same data.
- `data/videogames.json`: one object per video game, with a `platform` field (`pc` or `switch2`). Same `fetch` plus `js/videogames-data.js` fallback. PC games come from Shea's Steam library (profile LordScorpy). Nintendo games use `platform: "switch2"` so they appear under the Nintendo Switch 2 filter (the shelf is the Switch 2 library, which also includes Switch 1 games playing on it). Each Switch record has a `format` of Digital, Physical, or Both, and a `switchFamily` of `switch2`, `switch2-edition`, or `switch1` only when that can be verified — otherwise the field is left empty. Played / Never played is hidden when only Nintendo is selected, because those games have no playtime data.
- `data/coverage.json` / `data/COVERAGE.md`: board-game data snapshot date and coverage stats. Video-game snapshot date and counts live in `data/videogames.json`.
- `img/<bggid>.jpg`: board-game box art downloaded from BoardGameGeek.
- Video game cover art is usually hotlinked, not downloaded into the repo. PC art comes from Steam's public CDN (`cdn.cloudflare.steamstatic.com`), preferring the portrait `library_600x900.jpg` capsule, then falling back to `header.jpg` and `capsule_616x353.jpg`, then a monogram if all three 404. Switch art is hotlinked from Nintendo's official store CDN (`assets.nintendo.com`) when a matching product page was found. When no official cover could be found, `img/created/<id>.webp` holds original 600×900 title art credited as Art by Scorpy (see `scripts/created_art.json`); those cards are not official box art.
- Theme: light by default. A toggle switches to dark mode and remembers the choice in `localStorage`. Respects `prefers-reduced-motion`.
- Board-game videos load only on click, through `youtube-nocookie.com`.
- Links that could not be confirmed automatically carry `verified: false` and show a "Not verified" badge. How-to-play videos are not invented for the video-game shelf.

## Updating the data

### Board games
The data scripts in `scripts/` (fetch from BGG, YouTube search, video picks, images, build, coverage) write `data/games.json`. Their caches (`raw/`, `work/`) are git-ignored. `build.py` finishes by running `scripts/apply_overrides.py`, which applies `scripts/edition_overrides.json` (box art, year, and edition fixes for the edition Shea actually owns, such as Beat the Heat and Accomplices) and regenerates the `js/games-data.js` fallback. After hand-editing `data/games.json`, run it yourself:

```sh
python3 scripts/apply_overrides.py
```

The board-game scripts resolve paths from the repo root. Optional environment variables:

- `BGG_COLLECTION` — path to the owned-games JSON (defaults to `raw/Scorpy311_owned_games.json`)
- `BGG_IDS` — path to the id list used by `scripts/images.py` (defaults to `ids.txt`)
- `YT_DLP` — `yt-dlp` executable (defaults to `yt-dlp` on `PATH`)
- `CANVAS_VARIANTS_SRC` — Canvas source file for `scripts/canvas_variants.py` (defaults to `work/source.canvas.tsx`)

### Video games
`scripts/build_videogames.py` reads a Steam GetOwnedGames dump and writes `data/videogames.json` plus `js/videogames-data.js`. It also pulls genres, release year, description, and developers from the public Steam store `appdetails` API, one request at a time, and caches the raw responses in `work/steam/appdetails/` (git-ignored). The dump path comes from `STEAM_OWNED`, or from `raw/steam/owned_games.json` under the repo root if that is unset. The script does not modify that file unless `--refresh-owned` is passed. If Switch records have already been built, they are merged back in so a Steam rebuild does not wipe them.

```sh
python3 scripts/build_videogames.py
```

`scripts/build_switch.py` reads `scripts/switch_catalog.json` (titles transcribed from Shea's Switch 2 Virtual Game Cards and cartridge-shelf photos) and fetches official names, cover art, years, genres, and store URLs from Nintendo.com, one request at a time, caching pages in `work/switch/pages/` (git-ignored). Store links and art are stored only when a matching product page is found. It then merges those records into `data/videogames.json` and regenerates the JS fallback.

`scripts/apply_created_art.py` (also called from both video-game build scripts) points games listed in `scripts/created_art.json` at the original title-art files in `img/created/` and sets `image.credit` to `Art by Scorpy`. After adding or changing created art, run:

```sh
python3 scripts/apply_created_art.py
```

```sh
python3 scripts/build_switch.py
```

To re-pull the Steam library itself, set `STEAM_API_KEY` in the environment and pass `--refresh-owned`. The key is never printed, written, or copied into the site. Do not put the key in a file in this folder.

Optional environment variables:

- `STEAM_OWNED` — path to the GetOwnedGames JSON (defaults to `raw/steam/owned_games.json`)
- `STEAM_API_KEY` — used only with `--refresh-owned`; never committed

To preview locally, run `python3 -m http.server` in this folder.

## Credits
Board game data, box art, player polls, weights, files, and forums: [BoardGameGeek](https://boardgamegeek.com) (collection: Scorpy311). Rulebooks link to publishers where we found them. Videos are hosted on YouTube by their creators. BGG file downloads need a free BGG login.

PC games, playtimes, and official cover art: [Steam](https://steamcommunity.com/id/LordScorpy/) (profile LordScorpy). Store links go to each game's Steam page. Nintendo games, official titles, and official cover art: transcribed from Shea's Switch 2 library and [Nintendo.com](https://www.nintendo.com/) product pages when a match was verified. Official cover art © its publishers. Cards marked Art by Scorpy are original title art made for this shelf when no official cover could be found; they are not official box art.

Stark keeps this page up to date. Not affiliated with BoardGameGeek, Valve, Steam, Nintendo, or any publisher.
