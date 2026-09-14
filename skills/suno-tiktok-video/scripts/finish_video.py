#!/usr/bin/env python3
"""Finish a reviewed Android song video with karaoke and local verification.

This intentionally has no upload, deletion, network, or arbitrary command option.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys

from platform_utils import check_file_stability, get_downloads_dir
from render_karaoke import probe, validate_lines, video_details


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def choose_outputs(downloads: Path, workspace: Path, slug: str) -> tuple[Path, Path]:
    for number in range(1, 1000):
        suffix = f"{number:02d}"
        base = workspace / f"base_{slug}_{suffix}.mp4"
        final = downloads / f"TikTok_{slug}_Karaoke_{suffix}.mp4"
        if not base.exists() and not base.is_symlink() and not final.exists() and not final.is_symlink():
            return base, final
    raise ValueError("No fresh output filename available")


def image_paths(storyboard: Path) -> list[Path]:
    data = json.loads(storyboard.read_text(encoding="utf-8"))
    assets = {str(asset["id"]): asset for asset in data.get("assets", []) if isinstance(asset, dict) and "id" in asset}
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Storyboard needs scenes")
    paths = []
    for scene in scenes:
        image = scene.get("image") or assets.get(str(scene.get("asset_id")), {}).get("image")
        if not image:
            raise ValueError("Each scene needs an image")
        path = Path(image).expanduser()
        paths.append((path if path.is_absolute() else storyboard.parent / path).resolve())
    return paths


def scan_android(path: Path) -> str:
    command = Path("/data/data/com.termux/files/usr/bin/am")
    if not command.is_file():
        return "unavailable; open or refresh Downloads manually"
    result = subprocess.run(
        [str(command), "broadcast", "--user", "0", "-a",
         "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", path.as_uri()],
        capture_output=True, text=True, check=False, timeout=20,
    )
    return "requested" if result.returncode == 0 else f"failed (exit {result.returncode})"


def finish(audio: Path, storyboard: Path, timing: Path, workspace: Path, slug: str,
           downloads: Path | None = None) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_]{1,48}", slug):
        raise ValueError("Slug must contain only ASCII letters, digits, and underscores")
    downloads = (downloads or get_downloads_dir()).expanduser().resolve()
    audio = audio.expanduser().resolve()
    storyboard = storyboard.expanduser().resolve()
    timing = timing.expanduser().resolve()
    workspace = workspace.expanduser().resolve()
    if not downloads.is_dir() or not workspace.is_dir():
        raise ValueError("Downloads and workspace must already exist")
    if not (inside(workspace, downloads) or inside(workspace, Path("/tmp"))):
        raise ValueError("Workspace must be inside Downloads or /tmp")
    if not inside(audio, downloads) or audio.suffix.lower() not in (".wav", ".flac", ".mp3", ".m4a"):
        raise ValueError("Audio must be a supported file in Downloads")
    if not audio.is_file() or not check_file_stability(audio):
        raise ValueError("Audio is missing, empty, or still changing")
    if not all(inside(path, workspace) and path.is_file() for path in (storyboard, timing)):
        raise ValueError("Storyboard and timing must be files inside the workspace")
    images = image_paths(storyboard)
    if not all(inside(path, workspace) and path.is_file() for path in images):
        raise ValueError("All storyboard images must exist inside the workspace")
    audio_metadata = probe(audio, "ffprobe")
    audio_stream = next((stream for stream in audio_metadata["streams"] if stream.get("codec_type") == "audio"), None)
    if audio_stream is None:
        raise ValueError("Audio file has no audio stream")
    duration = float(audio_stream.get("duration") or audio_metadata["format"]["duration"])
    lines = validate_lines(json.loads(timing.read_text(encoding="utf-8")), duration)
    base, final = choose_outputs(downloads, workspace, slug)
    scripts = Path(__file__).resolve().parent
    print(json.dumps({"audio": str(audio), "size_bytes": audio.stat().st_size,
                      "mtime": datetime.fromtimestamp(audio.stat().st_mtime).astimezone().isoformat(),
                      "base": str(base), "final": str(final), "scenes": len(images),
                      "karaoke_lines": len(lines)}, ensure_ascii=False), flush=True)
    subprocess.run([sys.executable, str(scripts / "build_video.py"), "--audio", str(audio),
                    "--storyboard", str(storyboard), "--output", str(base),
                    "--attribution-lang", "uk"], check=True)
    subprocess.run([sys.executable, str(scripts / "render_karaoke.py"), "--video", str(base),
                    "--timing", str(timing), "--output", str(final)], check=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-xerror", "-nostdin",
                    "-i", str(final), "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"], check=True)
    width, height, final_duration = video_details(probe(final, "ffprobe"))
    if (width, height) != (1080, 1920) or abs(final_duration - duration) > 0.15:
        raise RuntimeError("Final dimensions or duration failed verification")
    result = {"final": str(final), "base": str(base), "size_bytes": final.stat().st_size,
              "duration_seconds": final_duration, "dimensions": [width, height],
              "scenes": len(images), "karaoke_lines": len(lines), "full_decode": "passed",
              "media_scan": scan_android(final)}
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--timing", required=True, type=Path, help="Human-reviewed word timing JSON")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--slug", required=True)
    args = parser.parse_args()
    try:
        finish(args.audio, args.storyboard, args.timing, args.workspace, args.slug)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
