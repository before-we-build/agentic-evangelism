#!/usr/bin/env python3
"""Build and verify a full-song storyboard or single-image video; never overwrite output."""
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_format', '-show_streams',
        '-of', 'json', str(path)], text=True))


def run(args):
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', required=True, type=Path)
    visuals = parser.add_mutually_exclusive_group(required=True)
    visuals.add_argument('--image', type=Path, help='Explicit single-image mode')
    visuals.add_argument('--storyboard', type=Path, help='JSON with scenes and duration_seconds')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    for tool in ('ffmpeg', 'ffprobe'):
        if not shutil.which(tool):
            parser.error(f'{tool} is not installed')
    audio, output = (p.expanduser().absolute() for p in (args.audio, args.output))
    if output.exists() or output.is_symlink():
        parser.error('Output already exists; choose a fresh filename')
    if output.suffix.lower() != '.mp4' or not output.parent.is_dir():
        parser.error('Output must be an .mp4 in an existing directory')
    for path in (audio,):
        if not path.is_file() or path.stat().st_size == 0:
            parser.error(f'Missing or empty input: {path}')
    before = (audio.stat().st_size, audio.stat().st_mtime_ns)
    time.sleep(2)
    if before != (audio.stat().st_size, audio.stat().st_mtime_ns):
        parser.error('Audio is still changing; wait for download completion')
    metadata = probe(audio)
    streams = [s for s in metadata['streams'] if s['codec_type'] == 'audio']
    if not streams:
        parser.error('Input contains no audio stream')
    duration = float(streams[0].get('duration') or metadata['format']['duration'])
    if not math.isfinite(duration) or duration <= 0:
        parser.error('Invalid audio duration')
    if args.storyboard:
        scenes = json.loads(args.storyboard.read_text())['scenes']
        if not isinstance(scenes, list) or not scenes:
            parser.error('Storyboard needs a nonempty scenes list')
        images = []
        lengths = []
        for scene in scenes:
            path = Path(scene['image']).expanduser()
            if not path.is_absolute():
                path = args.storyboard.resolve().parent / path
            images.append(path)
            length = float(scene['duration_seconds'])
            if not math.isfinite(length) or length <= 0:
                parser.error('Scene durations must be finite and positive')
            lengths.append(length)
        if abs(sum(lengths) - duration) > 0.15:
            parser.error('Storyboard durations must cover the full audio within 0.15 seconds')
    else:
        images = [args.image.expanduser().absolute()]
        lengths = [duration]
    for path in images:
        if not path.is_file() or path.stat().st_size == 0:
            parser.error(f'Missing or empty image: {path}')
    # Round cumulative boundaries, not each duration, to avoid accumulated drift.
    boundaries = [0]
    elapsed = 0.0
    for length in lengths:
        elapsed += length
        boundaries.append(round(elapsed * 25))
    boundaries[-1] = math.ceil(duration * 25)
    frames = [b - a for a, b in zip(boundaries, boundaries[1:])]
    if min(frames) < 1:
        parser.error('Every scene must occupy at least one video frame')
    # Decode the selected audio before spending time on rendering.
    run(['ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-i', str(audio),
         '-map', '0:a:0', '-f', 'null', '-'])
    work = Path(tempfile.mkdtemp(prefix='suno-tiktok-'))
    stage = work / 'verified-video.mp4'
    print(json.dumps({'work_dir': str(work), 'audio_duration': duration}), flush=True)
    for index, (image, count) in enumerate(zip(images, frames)):
        clip = work / f'scene-{index:05d}.mp4'
        print(json.dumps({'scene': index + 1, 'total': len(images)}), flush=True)
        run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-xerror', '-nostdin',
             '-n', '-loop', '1', '-framerate', '25', '-i', str(image),
             '-map', '0:v:0', '-map_metadata', '-1',
             '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1',
             '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'stillimage',
             '-crf', '22', '-pix_fmt', 'yuv420p', '-threads', '4',
             '-frames:v', str(count), '-an', str(clip)])
    # Only generated ASCII filenames enter the concat syntax, never user paths.
    playlist = work / 'scenes.txt'
    playlist.write_text(''.join(f"file 'scene-{i:05d}.mp4'\n" for i in range(len(images))))
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-xerror', '-nostdin',
         '-n', '-f', 'concat', '-safe', '1', '-i', str(playlist), '-i', str(audio),
         '-map', '0:v:0', '-map', '1:a:0', '-map_metadata', '-1',
         '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', str(duration),
         '-movflags', '+faststart', str(stage)])
    result = probe(stage)
    video = [s for s in result['streams'] if s['codec_type'] == 'video']
    sound = [s for s in result['streams'] if s['codec_type'] == 'audio']
    if len(video) != 1 or len(sound) != 1:
        raise RuntimeError('Expected exactly one video and one audio stream')
    v, a = video[0], sound[0]
    if (v['codec_name'], v['width'], v['height'], v['pix_fmt'], a['codec_name']) != (
            'h264', 1080, 1920, 'yuv420p', 'aac'):
        raise RuntimeError('Output codec or dimensions mismatch')
    # Allow MP3 encoder delay/AAC padding and a single video frame.
    for stream in (v, a):
        if abs(float(stream['duration']) - duration) > 0.15:
            raise RuntimeError('Output stream does not cover the full song')
    run(['ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-i', str(stage),
         '-map', '0:v:0', '-map', '0:a:0', '-f', 'null', '-'])
    if before != (audio.stat().st_size, audio.stat().st_mtime_ns):
        raise RuntimeError('Source audio changed during rendering')
    (work / 'verification.json').write_text(json.dumps(result, indent=2))
    # Exclusive creation also protects against a destination created during render.
    with output.open('xb') as dst, stage.open('rb') as src:
        shutil.copyfileobj(src, dst)
    if output.stat().st_size != stage.stat().st_size:
        raise RuntimeError('Destination copy size mismatch')
    print(json.dumps({'output': str(output), 'bytes': output.stat().st_size,
                      'duration': float(result['format']['duration']),
                      'resolution': '1080x1920', 'decode_verified': True,
                      'android_indexing': 'not checked by this script',
                      'report': str(work / 'verification.json')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
