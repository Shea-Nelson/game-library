#!/usr/bin/env python3
"""Apply scripts/created_art.json to video-game records (idempotent).

Sets image.portrait to the local original title-art file, records
image.credit, and clears broken Steam CDN fallbacks for those games.
Also used by build_videogames.py and build_switch.py so a rebuild
does not drop the created art.

Run after hand-editing, or on its own:

  python3 scripts/apply_created_art.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = Path(__file__).resolve().parent / "created_art.json"
OUT_JSON = ROOT / "data" / "videogames.json"
OUT_JS = ROOT / "js" / "videogames-data.js"

NOTE_SENTENCE = (
    "When no official cover could be found, the card uses original title art "
    "credited as Art by Scorpy, not official box art."
)


def load_map():
    raw = json.loads(MAP_PATH.read_text())
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def apply_to_records(records, art_map=None):
    art_map = art_map if art_map is not None else load_map()
    applied = 0
    missing = []
    for rec in records:
        entry = art_map.get(rec.get("id"))
        if not entry:
            continue
        path = entry["file"]
        if not (ROOT / path).is_file():
            missing.append(path)
            continue
        image = rec.get("image") or {}
        image["portrait"] = path
        image["header"] = None
        image["capsule"] = None
        image["credit"] = entry.get("credit") or "Art by Scorpy"
        rec["image"] = image
        applied += 1
    if missing:
        raise FileNotFoundError("created art files missing: " + ", ".join(missing))
    return applied


def apply_note(note: str) -> str:
    note = note or ""
    # Tidy a leftover semicolon if a previous apply already inserted the sentence.
    note = note.replace("; When no official cover", ". When no official cover")
    if "Art by Scorpy" in note:
        return note
    # Replace the old monogram-only fallback wording when present.
    old = "otherwise the card uses a monogram."
    if old in note:
        note = note.replace("; " + old, ". " + NOTE_SENTENCE)
        note = note.replace(old, NOTE_SENTENCE)
        return note
    if note and not note.endswith(" "):
        if not note.endswith("."):
            note += "."
        note += " "
    return note + NOTE_SENTENCE


def write_payload(payload):
    OUT_JSON.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    OUT_JS.write_text(
        "/* Fallback copy of data/videogames.json for file:// viewing. Regenerate when data changes. */\n"
        "window.VIDEOGAMES_DATA="
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )


def main():
    if not OUT_JSON.exists():
        sys.exit(f"Missing {OUT_JSON}")
    payload = json.loads(OUT_JSON.read_text())
    applied = apply_to_records(payload.get("games") or [])
    payload["note"] = apply_note(payload.get("note") or "")
    write_payload(payload)
    print(f"applied created art to {applied} video games")


if __name__ == "__main__":
    main()
