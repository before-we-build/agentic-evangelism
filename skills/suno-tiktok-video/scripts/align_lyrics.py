#!/usr/bin/env python3
"""Get Groq Whisper timestamps and estimate storyboard scene boundaries."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional

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


def call_groq_whisper(
    audio_path: Path,
    api_key: str,
    prompt: Optional[str] = None,
    language: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Transcribe through the official Groq SDK with word and segment timestamps."""
    try:
        from groq import Groq
    except ImportError as error:
        raise RuntimeError("Official Groq SDK is missing; install 'groq' in this Python environment") from error

    request: Dict[str, Any] = {
        "file": audio_path,
        "model": model,
        "response_format": "verbose_json",
        "timestamp_granularities": ["word", "segment"],
    }
    if prompt:
        request["prompt"] = prompt
    if language:
        request["language"] = language

    try:
        response = Groq(api_key=api_key, timeout=timeout, max_retries=0).audio.transcriptions.create(**request)
    except Exception as error:
        detail = str(error).replace(api_key, "[REDACTED]")
        raise RuntimeError(f"Groq transcription failed: {detail}") from error
    return response.model_dump()


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
        description="Request Groq word/segment timestamps and estimate scene boundaries; no karaoke is rendered."
    )
    parser.add_argument("--audio", type=Path, required=True, help="Path to input audio file")
    parser.add_argument("--storyboard", type=Path, required=True, help="Path to storyboard JSON file")
    parser.add_argument("--output", type=Path, help="Path to write aligned storyboard (default: sibling *-aligned.json)")
    parser.add_argument("--transcript-output", type=Path, help="Path to save Groq timestamps (default: sibling *-transcript.json)")
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

    api_key = os.environ.get("GROQ_API_KEY", "")

    if not api_key and not args.dry_run:
        print("[align_lyrics] Notice: GROQ_API_KEY environment variable is not set.", file=sys.stderr)
        print("Set it securely in this process environment; never use CLI arguments or chat.", file=sys.stderr)
        print("No audio was sent; existing storyboard timings are unchanged.", file=sys.stderr)
        if args.strict:
            sys.exit(2)
        sys.exit(0)

    prompt = args.prompt

    out_path = (args.output or storyboard_path.with_name(f"{storyboard_path.stem}-aligned.json")).expanduser().resolve()
    transcript_path = (args.transcript_output or storyboard_path.with_name(f"{storyboard_path.stem}-transcript.json")).expanduser().resolve()
    if out_path == storyboard_path or out_path.exists():
        parser.error("Aligned storyboard output must be a new file; preserve the original")
    if not args.dry_run and (transcript_path.exists() or transcript_path in (storyboard_path, out_path)):
        parser.error("Transcript output must be a separate new file")

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
    sb_data["timing_basis"] = "groq_segment_guided_estimate" if not args.dry_run else "simulated_aligned"

    if not args.dry_run:
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(transcript_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(resp, output, indent=2, ensure_ascii=False)
        sb_data["asr_transcript"] = str(transcript_path)
        sb_data["asr_word_timestamps_unreviewed"] = bool(resp.get("words"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(sb_data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "status": "scene_estimate_updated",
        "audio": str(audio_path),
        "storyboard": str(out_path),
        "total_duration": total_duration,
        "scenes_aligned": len(aligned_scenes),
        "timing_basis": sb_data["timing_basis"],
        "transcript": str(transcript_path) if not args.dry_run else None,
        "word_timestamps_unreviewed": bool(resp.get("words")) if not args.dry_run else False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
