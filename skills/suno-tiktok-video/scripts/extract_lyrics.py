#!/usr/bin/env python3
"""Extract embedded lyrics without ASR or invented word timestamps."""
import argparse
import json
from pathlib import Path
import re
import subprocess


def extract(audio):
    data = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json',
        str(audio)], text=True))
    tracks = [s for s in data['streams'] if s['codec_type'] == 'audio']
    if not tracks:
        raise ValueError('No audio stream')
    candidates = []
    for location, tags in [('format', data.get('format', {}).get('tags', {}))] + [
            (f'stream:{s["index"]}', s.get('tags', {})) for s in data['streams']]:
        for key, value in tags.items():
            if any(marker in key.casefold() for marker in ('lyrics', 'unsyncedlyrics', 'uslt', 'sylt')) and str(value).strip():
                raw = str(value)
                # Preserve original separately; clean only recognizable bracketed cues.
                clean = re.sub(r'\[[^\]\n]*\]', '', raw)
                clean = '\n'.join(line.strip() for line in clean.splitlines() if line.strip())
                candidates.append({'location': location, 'tag': key, 'raw': raw, 'clean': clean})
    return {'audio': str(audio.resolve()),
            'duration_seconds': float(tracks[0].get('duration') or data['format']['duration']),
            'lyrics_candidates': candidates,
            'status': 'found' if candidates else 'missing',
            'timing': 'none; embedded text is not verified against the performed recording'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = extract(args.audio)
    with args.output.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({'output': str(args.output), 'status': result['status'],
                      'candidates': len(result['lyrics_candidates'])}))


if __name__ == '__main__':
    main()
