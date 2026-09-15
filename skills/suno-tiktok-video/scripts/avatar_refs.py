#!/usr/bin/env python3
"""Resolve optional character avatars for image-tool calls without copying them."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _image_file(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 8:
        return False
    with path.open("rb") as source:
        header = source.read(12)
    return (
        header.startswith(b"\x89PNG\r\n\x1a\n")
        or header.startswith(b"\xff\xd8\xff")
        or (header.startswith(b"RIFF") and header[8:12] == b"WEBP")
    )


def reference_manifest(storyboard_path: Path) -> dict:
    board = storyboard_path.resolve()
    data = json.loads(board.read_text(encoding="utf-8"))
    characters = {}
    for character in data.get("characters", []):
        character_id = character["id"]
        if character_id in characters:
            raise ValueError(f"Duplicate character id: {character_id}")
        avatar = character.get("avatar_image")
        if avatar:
            path = Path(avatar)
            path = (path if path.is_absolute() else board.parent / path).resolve()
            if not _image_file(path):
                raise ValueError(f"Avatar for {character_id} is missing or not a PNG, JPEG, or WebP image: {path}")
            characters[character_id] = str(path)
        else:
            characters[character_id] = None

    assets = []
    for asset in data.get("assets", []):
        refs = []
        for character_id in asset.get("character_ids", []):
            if character_id not in characters:
                raise ValueError(f"Asset {asset.get('id')} names unknown character: {character_id}")
            avatar = characters[character_id]
            if avatar and avatar not in refs:
                refs.append(avatar)
        assets.append({"id": asset["id"], "reference_images": refs})
    return {"storyboard": str(board), "assets": assets}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storyboard", required=True, type=Path)
    args = parser.parse_args()
    try:
        manifest = reference_manifest(args.storyboard)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
