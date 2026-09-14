#!/usr/bin/env python3
"""Create a fresh local video workspace and extract embedded song lyrics."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re

from extract_lyrics import extract
from platform_utils import check_file_stability, get_downloads_dir


def prepare(audio: Path, slug: str, downloads: Path | None = None) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_]{1,48}", slug):
        raise ValueError("Slug must contain only ASCII letters, digits, and underscores")
    downloads = (downloads or get_downloads_dir()).expanduser().resolve()
    audio = audio.expanduser().resolve()
    if not downloads.is_dir() or audio.parent != downloads:
        raise ValueError("Audio must be a file directly inside Downloads")
    if audio.suffix.lower() not in (".wav", ".flac", ".mp3", ".m4a"):
        raise ValueError("Unsupported audio format")
    if not check_file_stability(audio):
        raise ValueError("Audio is missing, empty, or still changing")
    selected = {"path": str(audio), "filename": audio.name, "size_bytes": audio.stat().st_size,
                "mtime": datetime.fromtimestamp(audio.stat().st_mtime).astimezone().isoformat()}
    print(json.dumps({"selected": selected}, ensure_ascii=False), flush=True)
    lyrics = extract(audio)
    for number in range(1, 1000):
        workspace = downloads / f"Video_{slug}_{number:02d}"
        try:
            workspace.mkdir()
            break
        except FileExistsError:
            continue
    else:
        raise ValueError("No fresh workspace name available")
    lyrics_path = workspace / "lyrics.json"
    with lyrics_path.open("x", encoding="utf-8") as target:
        json.dump(lyrics, target, ensure_ascii=False, indent=2)
    result = {"workspace": str(workspace), "lyrics": str(lyrics_path),
              "duration_seconds": lyrics["duration_seconds"], "lyrics_status": lyrics["status"],
              "lyric_candidates": len(lyrics["lyrics_candidates"])}
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--slug", required=True)
    args = parser.parse_args()
    try:
        prepare(args.audio, args.slug)
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
