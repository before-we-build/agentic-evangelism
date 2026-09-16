#!/usr/bin/env python3
"""Burn reviewed word-timed lyrics into a copy of a vertical MP4."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile


try:
    from platform_utils import escape_ffmpeg_filter_path
except ImportError:
    try:
        from .platform_utils import escape_ffmpeg_filter_path
    except ImportError:
        def escape_ffmpeg_filter_path(path: str | Path) -> str:
            p = str(Path(path).resolve()).replace('\\', '/')
            p = p.replace(':', r'\:')
            p = p.replace("'", r"\'").replace('[', r'\[').replace(']', r'\]')
            return p


def ass_time(seconds: float) -> str:
    centiseconds = round(seconds * 100)
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02}:{seconds:02}.{centiseconds:02}"


def escape_ass(text: str) -> str:
    return text.replace("\\", "＼").replace("{", "｛").replace("}", "｝").replace("\n", " ").strip()


def validate_lines(data: dict, duration: float) -> list[dict]:
    lines = data.get("lines")
    if not isinstance(lines, list) or not lines:
        raise ValueError("Timing JSON needs a nonempty lines list")
    previous_end = 0.0
    for index, line in enumerate(lines):
        if not isinstance(line, dict):
            raise ValueError(f"Line {index} must be an object")
        start = float(line["start"])
        end = float(line["end"])
        if not (math.isfinite(start) and math.isfinite(end) and previous_end <= start < end <= duration + 0.1):
            raise ValueError(f"Line {index} has invalid or overlapping times")
        words = line.get("words")
        if not isinstance(words, list) or not words:
            raise ValueError(f"Line {index} needs timed words")
        previous_word_end = start
        for word_index, word in enumerate(words):
            if not isinstance(word, dict) or not isinstance(word.get("text"), str) or not word["text"].strip():
                raise ValueError(f"Line {index} word {word_index} needs text")
            word_start = float(word["start"])
            word_end = float(word["end"])
            if not (math.isfinite(word_start) and math.isfinite(word_end) and
                    start - 0.01 <= word_start < word_end <= end + 0.01 and
                    previous_word_end <= word_start + 0.01):
                raise ValueError(f"Line {index} word {word_index} has invalid times")
            previous_word_end = word_end
        previous_end = end
    return lines


def validate_timing_data(data: dict, duration: float) -> tuple[list[dict], dict]:
    """Validate timing file structure, line timings, and optional review/hash metadata."""
    metadata = {
        "reviewed": data.get("reviewed", True),
        "audio_hash": data.get("audio_hash"),
        "lyrics_hash": data.get("lyrics_hash"),
        "version": data.get("version"),
    }
    if data.get("reviewed") is False:
        import sys
        print("[WARNING] Timing data has reviewed=False; human review of lyrics is recommended.", file=sys.stderr)
    lines = validate_lines(data, duration)
    return lines, metadata


def make_ass(lines: list[dict], width: int, height: int) -> str:
    font_size = round(height * 0.031)
    margin_left = round(width * 0.10)
    margin_right = round(width * 0.21)
    margin_bottom = round(height * 0.32)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,DejaVu Sans,{font_size},&H0000D7FF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,2,{margin_left},{margin_right},{margin_bottom},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for line in lines:
        cursor = round(float(line["start"]) * 100)
        chunks = []
        for index, word in enumerate(line["words"]):
            word_start = round(float(word["start"]) * 100)
            word_end = round(float(word["end"]) * 100)
            if word_start > cursor:
                chunks.append(r"{\k" + str(word_start - cursor) + "} ")
            duration = max(1, word_end - word_start)
            chunks.append(r"{\kf" + str(duration) + "}" + escape_ass(word["text"]))
            if index < len(line["words"]) - 1:
                chunks.append(" ")
            cursor = word_end
        events.append(
            f"Dialogue: 0,{ass_time(float(line['start']))},{ass_time(float(line['end']))},"
            f"Karaoke,,0,0,0,,{''.join(chunks)}"
        )
    return header + "\n".join(events) + "\n"


def probe(path: Path, ffprobe: str) -> dict:
    return json.loads(subprocess.check_output(
        [ffprobe, "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,codec_name,width,height", "-of", "json", str(path)],
        text=True, encoding="utf-8",
    ))


def video_details(metadata: dict) -> tuple[int, int, float]:
    video = next((s for s in metadata["streams"] if s.get("codec_type") == "video"), None)
    audio = next((s for s in metadata["streams"] if s.get("codec_type") == "audio"), None)
    if not video or not audio:
        raise ValueError("Input needs video and audio streams")
    width, height = int(video["width"]), int(video["height"])
    duration = float(metadata["format"]["duration"])
    if width <= 0 or height <= 0 or not math.isfinite(duration) or duration <= 0:
        raise ValueError("Invalid input dimensions or duration")
    return width, height, duration


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path, help="Original MP4; preserved")
    parser.add_argument("--timing", required=True, type=Path, help="Reviewed line/word timing JSON")
    parser.add_argument("--output", required=True, type=Path, help="New MP4 filename")
    parser.add_argument("--ass-output", type=Path, help="Optional new ASS file to retain")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--ass-only", action="store_true", help="Write only --ass-output for review")
    args = parser.parse_args()

    video = args.video.expanduser().resolve()
    timing = args.timing.expanduser().resolve()
    output = args.output.expanduser().resolve()
    ass_output = args.ass_output.expanduser().resolve() if args.ass_output else None
    if not video.is_file() or not timing.is_file():
        parser.error("Video and timing files must exist")
    if video.suffix.lower() != ".mp4" or output.suffix.lower() != ".mp4":
        parser.error("Video and output must be MP4")
    if output.exists() or output.is_symlink() or output == video:
        parser.error("Output must be a new file; preserve the original")
    if not output.parent.is_dir():
        parser.error("Output directory must exist")
    if ass_output and (ass_output.exists() or ass_output.is_symlink() or ass_output in (video, timing, output)):
        parser.error("ASS output must be a separate new file")
    if args.ass_only and not ass_output:
        parser.error("--ass-only requires --ass-output")
    if not shutil.which(args.ffprobe) and not Path(args.ffprobe).is_file():
        parser.error("ffprobe not found")
    if not args.ass_only and not shutil.which(args.ffmpeg) and not Path(args.ffmpeg).is_file():
        parser.error("ffmpeg not found")

    width, height, duration = video_details(probe(video, args.ffprobe))
    timing_data = json.loads(timing.read_text(encoding="utf-8"))
    lines, timing_meta = validate_timing_data(timing_data, duration)
    ass_text = make_ass(lines, width, height)
    if ass_output:
        ass_output.write_text(ass_text, encoding="utf-8")
    if args.ass_only:
        print(json.dumps({"ass": str(ass_output), "lines": len(lines), "metadata": timing_meta}, ensure_ascii=False))
        return

    with tempfile.TemporaryDirectory(prefix="suno-karaoke-") as temporary:
        temporary_path = Path(temporary)
        ass_file = temporary_path / "karaoke.ass"
        ass_file.write_text(ass_text, encoding="utf-8")
        escaped_ass = escape_ffmpeg_filter_path(ass_file)
        stage = temporary_path / "stage.mp4"
        command = [
            args.ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-xerror",
            "-i", str(video), "-vf", f"ass='{escaped_ass}'",
            "-map", "0:v:0", "-map", "0:a:0", "-map_metadata", "0",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
            str(stage),
        ]
        subprocess.run(command, check=True)
        result = probe(stage, args.ffprobe)
        out_width, out_height, out_duration = video_details(result)
        if (out_width, out_height) != (width, height) or abs(out_duration - duration) > 0.15:
            raise RuntimeError("Rendered video dimensions or duration differ from original")
        with output.open("xb") as target, stage.open("rb") as source:
            shutil.copyfileobj(source, target, length=1024 * 1024)
    print(json.dumps({
        "output": str(output), "duration": out_duration, "lines": len(lines),
        "size_bytes": output.stat().st_size, "audio_codec": next(
            s.get("codec_name") for s in result["streams"] if s.get("codec_type") == "audio"
        ),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
