#!/usr/bin/env python3
"""
Zero-cost, universal lyrics-to-audio alignment using free Groq Whisper Large-v3.
Requires no credit cards, zero third-party dependencies, and runs smoothly on Android (Termux).
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"
DEFAULT_MODEL = "whisper-large-v3"


def probe_audio_duration(audio_path: Path, ffprobe_bin: str = "ffprobe") -> float:
    """Extract audio duration in seconds using ffprobe or fallback."""
    try:
        cmd = [
            ffprobe_bin,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        out = subprocess.check_output(cmd, text=True, encoding="utf-8").strip()
        val = float(out)
        if math.isfinite(val) and val > 0:
            return val
    except Exception:
        pass
    return 0.0


def encode_multipart(fields: Dict[str, Any], files: Dict[str, Tuple[str, bytes, str]]) -> Tuple[bytes, str]:
    """Encode multipart/form-data payload using standard library only."""
    boundary = f"----WebKitFormBoundary{os.urandom(16).hex()}"
    body = bytearray()

    for name, value in fields.items():
        if value is not None:
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
            body.extend(str(value).encode("utf-8"))
            body.extend(b"\r\n")

    for name, (filename, content, content_type) in files.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("utf-8"))
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(content)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    content_type_header = f"multipart/form-data; boundary={boundary}"
    return bytes(body), content_type_header


def call_groq_whisper(
    audio_path: Path,
    api_key: str,
    prompt: Optional[str] = None,
    language: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Transcribe audio via Groq Whisper API with verbose_json output format."""
    audio_bytes = audio_path.read_bytes()
    filename = audio_path.name

    ext = audio_path.suffix.lower()
    content_type_map = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/m4a",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
    }
    content_type = content_type_map.get(ext, "application/octet-stream")

    fields: Dict[str, Any] = {
        "model": model,
        "response_format": "verbose_json",
    }
    if prompt:
        # Prompt guides Whisper and prevents hallucinations on lyrics
        fields["prompt"] = prompt[:400]
    if language:
        fields["language"] = language

    files = {
        "file": (filename, audio_bytes, content_type)
    }

    body, ct_header = encode_multipart(fields, files)

    req = urllib.request.Request(
        GROQ_ENDPOINT,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": ct_header,
            "User-Agent": "agentic-evangelism/align_lyrics",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            return json.loads(data.decode("utf-8"))
    except urllib.error.HTTPError as err:
        err_msg = err.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Groq API error (HTTP {err.code}): {err_msg}") from err
    except Exception as err:
        raise RuntimeError(f"Network error contacting Groq API: {err}") from err


def extract_lyrics_text_from_storyboard(sb_data: Dict[str, Any]) -> str:
    """Extract full lyrics or subidea summaries to use as Whisper prompt."""
    parts: List[str] = []
    # If explicit lyrics or central_message
    if "central_message" in sb_data:
        parts.append(str(sb_data["central_message"]))

    # From subideas
    subideas = sb_data.get("subideas", [])
    if isinstance(subideas, list):
        for s in subideas:
            if isinstance(s, dict):
                if "summary" in s:
                    parts.append(str(s["summary"]))
                if "evidence" in s:
                    parts.append(str(s["evidence"]))

    return " ".join(parts).strip()


def align_segments_to_scenes(
    scenes: List[Dict[str, Any]],
    segments: List[Dict[str, Any]],
    total_duration: float,
) -> List[Dict[str, Any]]:
    """
    Distribute detected acoustic segments among scenes and align transition timestamps.
    Guarantees:
    - First scene starts at 0.0 (covers musical intro).
    - Last scene ends at total_duration (covers outro).
    - Every scene has duration >= 0.5s.
    - Sum of durations equals total_duration within 0.15s.
    """
    num_scenes = len(scenes)
    if num_scenes == 0:
        return []
    if num_scenes == 1:
        sc = dict(scenes[0])
        sc["start_time"] = 0.0
        sc["end_time"] = round(total_duration, 3)
        sc["duration_seconds"] = round(total_duration, 3)
        return [sc]

    # Filter valid segments
    valid_segs = [s for s in segments if s.get("end", 0) > s.get("start", 0)]
    if not valid_segs:
        # Fallback: divide evenly if no vocal segments detected
        equal_dur = round(total_duration / num_scenes, 3)
        updated = []
        elapsed = 0.0
        for i in range(num_scenes):
            sc = dict(scenes[i])
            dur = equal_dur if i < num_scenes - 1 else round(total_duration - elapsed, 3)
            sc["start_time"] = round(elapsed, 3)
            sc["end_time"] = round(elapsed + dur, 3)
            sc["duration_seconds"] = dur
            elapsed += dur
            updated.append(sc)
        return updated

    # Boundaries for transitions between scenes (num_scenes + 1 points)
    # T[0] = 0.0, T[num_scenes] = total_duration
    boundaries: List[float] = [0.0]

    num_segs = len(valid_segs)
    for i in range(1, num_scenes):
        # Calculate proportional index in detected segments
        seg_idx = min(int(round((i / num_scenes) * num_segs)), num_segs - 1)
        # Transition happens around the start of the next segment
        transition_point = valid_segs[seg_idx]["start"]

        # Ensure transition point is strictly increasing and has minimum padding
        min_prev = boundaries[-1] + 1.0
        max_next = total_duration - (num_scenes - i) * 1.0
        chosen = max(min_prev, min(transition_point, max_next))
        boundaries.append(round(chosen, 3))

    boundaries.append(round(total_duration, 3))

    updated_scenes: List[Dict[str, Any]] = []
    for i in range(num_scenes):
        sc = dict(scenes[i])
        st = boundaries[i]
        et = boundaries[i + 1]
        dur = round(et - st, 3)
        sc["start_time"] = st
        sc["end_time"] = et
        sc["duration_seconds"] = dur
        updated_scenes.append(sc)

    # Fine-tune last scene to exact total duration
    sum_dur = sum(s["duration_seconds"] for s in updated_scenes)
    diff = round(total_duration - sum_dur, 3)
    if abs(diff) > 0.001:
        updated_scenes[-1]["duration_seconds"] = round(updated_scenes[-1]["duration_seconds"] + diff, 3)
        updated_scenes[-1]["end_time"] = round(total_duration, 3)

    return updated_scenes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Zero-cost neural lyrics-to-audio alignment using free Groq Whisper Large-v3."
    )
    parser.add_argument("--audio", type=Path, required=True, help="Path to input audio file")
    parser.add_argument("--storyboard", type=Path, required=True, help="Path to storyboard JSON file")
    parser.add_argument("--output", type=Path, help="Path to write aligned storyboard (defaults to updating in-place)")
    parser.add_argument("--api-key", type=str, help="Groq API Key (defaults to GROQ_API_KEY environment variable)")
    parser.add_argument("--prompt", type=str, help="Optional text prompt / lyrics override for Whisper")
    parser.add_argument("--language", type=str, help="Language code (e.g. 'uk', 'ru', 'en')")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help=f"Groq model (default: {DEFAULT_MODEL})")
    parser.add_argument("--ffprobe", type=str, default="ffprobe", help="Path to ffprobe executable")
    parser.add_argument("--dry-run", action="store_true", help="Simulate alignment without sending network request")
    parser.add_argument("--strict", action="store_true", help="Fail with non-zero exit code if GROQ_API_KEY is missing")

    args = parser.parse_args()

    audio_path = args.audio.expanduser().resolve()
    if not audio_path.is_file():
        sys.exit(f"Error: audio file not found: {audio_path}")

    storyboard_path = args.storyboard.expanduser().resolve()
    if not storyboard_path.is_file():
        sys.exit(f"Error: storyboard file not found: {storyboard_path}")

    sb_data = json.loads(storyboard_path.read_text(encoding="utf-8"))
    scenes = sb_data.get("scenes", [])
    if not isinstance(scenes, list) or not scenes:
        sys.exit("Error: storyboard contains no scenes")

    total_duration = probe_audio_duration(audio_path, args.ffprobe)
    if total_duration <= 0:
        # Try calculating from storyboard durations if ffprobe duration unavailable
        total_duration = sum(float(s.get("duration_seconds", 0)) for s in scenes)
    if total_duration <= 0:
        sys.exit("Error: unable to determine audio duration")

    api_key = args.api_key or os.environ.get("GROQ_API_KEY", "")

    if not api_key and not args.dry_run:
        print("[align_lyrics] Notice: GROQ_API_KEY environment variable is not set.", file=sys.stderr)
        print("To enable 100% free neural lyric alignment (Whisper Large-v3, 8 hours/day free, zero credit cards):", file=sys.stderr)
        print("  1. Create a free API key in 30 seconds at: https://console.groq.com/keys", file=sys.stderr)
        print("  2. Run: export GROQ_API_KEY='gsk_...'", file=sys.stderr)
        print("Skipping neural alignment; existing storyboard timings are preserved.", file=sys.stderr)
        if args.strict:
            sys.exit(2)
        sys.exit(0)

    prompt = args.prompt or extract_lyrics_text_from_storyboard(sb_data)

    if args.dry_run:
        print("[align_lyrics] Running in dry-run mode (simulating Whisper response)")
        # Synthesize realistic mock segments
        num_mock = max(len(scenes) * 2, 4)
        mock_segments = []
        step = total_duration / num_mock
        for j in range(num_mock):
            mock_segments.append({
                "start": round(j * step, 2),
                "end": round((j + 0.8) * step, 2),
                "text": f"Mock sung line {j}",
            })
        segments = mock_segments
    else:
        print(f"[align_lyrics] Connecting to Groq Whisper ({args.model})...")
        resp = call_groq_whisper(
            audio_path=audio_path,
            api_key=api_key,
            prompt=prompt,
            language=args.language,
            model=args.model,
        )
        segments = resp.get("segments", [])

    aligned_scenes = align_segments_to_scenes(scenes, segments, total_duration)

    sb_data["scenes"] = aligned_scenes
    sb_data["timing_basis"] = f"groq_{args.model}_aligned" if not args.dry_run else "simulated_aligned"

    out_path = (args.output or storyboard_path).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(sb_data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "status": "aligned",
        "audio": str(audio_path),
        "storyboard": str(out_path),
        "total_duration": total_duration,
        "scenes_aligned": len(aligned_scenes),
        "timing_basis": sb_data["timing_basis"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
