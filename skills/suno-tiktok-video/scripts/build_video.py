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

try:
    from platform_utils import detect_audio_attribution, find_system_font, is_valid_image_file
except ImportError:
    from .platform_utils import detect_audio_attribution, find_system_font, is_valid_image_file


def probe(path, ffprobe_bin='ffprobe'):
    return json.loads(subprocess.check_output([
        str(ffprobe_bin), '-v', 'error', '-show_format', '-show_streams',
        '-of', 'json', str(path)], text=True, encoding='utf-8'))


def run(args):
    subprocess.run(args, check=True)


def calculate_timeline(lengths, total_duration, transition='fade', transition_duration=0.75, fps=25):
    total_frames = math.ceil(total_duration * fps)
    num_scenes = len(lengths)
    boundaries = [0]
    elapsed = 0.0
    for length in lengths:
        elapsed += length
        boundaries.append(round(elapsed * fps))
    boundaries[-1] = total_frames
    nominal_frames = [b - a for a, b in zip(boundaries, boundaries[1:])]
    if min(nominal_frames) < 1:
        raise ValueError('Every scene must occupy at least one video frame')
    if transition == 'none' or num_scenes <= 1:
        return nominal_frames, None, None
    min_frames = min(nominal_frames)
    if min_frames < 4 or total_frames < 6:
        return nominal_frames, None, None
    desired_t_frames = max(2, round(transition_duration * fps))
    t_frames = min(desired_t_frames, max(2, min_frames // 2))
    offsets = []
    for k in range(1, num_scenes):
        nominal_o = boundaries[k] - t_frames // 2
        offsets.append(nominal_o)
    for i in range(len(offsets)):
        min_allowed = 1 if i == 0 else offsets[i - 1] + t_frames
        if offsets[i] < min_allowed:
            offsets[i] = min_allowed
    if offsets[-1] + t_frames >= total_frames:
        offsets[-1] = total_frames - t_frames - 1
    for i in range(len(offsets) - 2, -1, -1):
        if offsets[i] + t_frames > offsets[i + 1]:
            offsets[i] = offsets[i + 1] - t_frames
    if offsets[0] < 1 or any(offsets[i] + t_frames > offsets[i + 1] for i in range(len(offsets) - 1)) or offsets[-1] + t_frames >= total_frames:
        return nominal_frames, None, None
    clip_frames = [offsets[0] + t_frames]
    for k in range(1, num_scenes - 1):
        clip_frames.append((offsets[k] + t_frames) - offsets[k - 1])
    clip_frames.append(total_frames - offsets[-1])
    return clip_frames, offsets, t_frames


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', required=True, type=Path)
    visuals = parser.add_mutually_exclusive_group(required=True)
    visuals.add_argument('--image', type=Path, help='Explicit single-image mode')
    visuals.add_argument('--storyboard', type=Path, help='JSON with scenes and duration_seconds')
    parser.add_argument('--transition', choices=['none', 'fade'], default='fade',
                        help='Transition between storyboard scenes (default: fade)')
    parser.add_argument('--transition-duration', type=float, default=0.75,
                        help='Transition duration in seconds (default: 0.75)')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--ffmpeg', type=Path, help='Explicit path to ffmpeg binary')
    parser.add_argument('--ffprobe', type=Path, help='Explicit path to ffprobe binary')
    parser.add_argument('--work-dir', type=Path, help='Custom working directory for temp clips')
    parser.add_argument('--license', choices=['free', 'commercial'], default='free',
                        help='Audio license mode: free (enables attribution) or commercial (omits mandatory attribution)')
    parser.add_argument('--attribution', default='auto',
                        help='Attribution text: auto (detect generator), none (omit overlay), or custom text string')
    parser.add_argument('--attribution-lang', choices=['ru', 'uk', 'en'], default='ru',
                        help='Language for auto attribution and caption (default: ru)')
    args = parser.parse_args()

    if args.transition_duration <= 0 or not math.isfinite(args.transition_duration):
        parser.error('Transition duration must be a positive finite number')

    ffmpeg_bin = str(args.ffmpeg.expanduser().resolve()) if args.ffmpeg else 'ffmpeg'
    ffprobe_bin = str(args.ffprobe.expanduser().resolve()) if args.ffprobe else 'ffprobe'

    for name, tool in (('ffmpeg', ffmpeg_bin), ('ffprobe', ffprobe_bin)):
        if not shutil.which(tool) and not Path(tool).is_file():
            parser.error(f'{name} is not installed or not executable: {tool}')

    audio = args.audio.expanduser().resolve()
    output = args.output.expanduser().resolve()
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
    metadata = probe(audio, ffprobe_bin=ffprobe_bin)
    streams = [s for s in metadata['streams'] if s['codec_type'] == 'audio']
    if not streams:
        parser.error('Input contains no audio stream')
    duration = float(streams[0].get('duration') or metadata['format']['duration'])
    if not math.isfinite(duration) or duration <= 0:
        parser.error('Invalid audio duration')
    if args.storyboard:
        sb_data = json.loads(args.storyboard.read_text(encoding='utf-8'))
        scenes = sb_data.get('scenes', [])
        assets = sb_data.get('assets', [])
        assets_by_id = {}
        if isinstance(assets, list):
            for a in assets:
                if isinstance(a, dict) and 'id' in a:
                    assets_by_id[str(a['id'])] = a

        if not isinstance(scenes, list) or not scenes:
            parser.error('Storyboard needs a nonempty scenes list')
        images = []
        lengths = []
        for idx, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                parser.error(f'Scene at index {idx} must be an object')
            img_ref = scene.get('image')
            if not img_ref and 'asset_id' in scene:
                asset_id = str(scene['asset_id'])
                if asset_id not in assets_by_id:
                    parser.error(f"Scene {idx} references unknown asset_id '{asset_id}'")
                img_ref = assets_by_id[asset_id].get('image')
            if not img_ref:
                parser.error(f"Scene {idx} must specify an 'image' path or a valid 'asset_id'")

            path = Path(img_ref).expanduser()
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
        images = [args.image.expanduser().resolve()]
        lengths = [duration]
    for path in images:
        if not path.is_file() or path.stat().st_size == 0:
            parser.error(f'Missing or empty image: {path}')
        if not is_valid_image_file(path):
            parser.error(f'Corrupt or invalid image format (must be valid PNG, JPEG, or WebP): {path}')
    try:
        clip_frames, offsets, t_frames = calculate_timeline(
            lengths, duration, args.transition, args.transition_duration, fps=25)
    except ValueError as err:
        parser.error(str(err))
    # Decode the selected audio before spending time on rendering.
    run([ffmpeg_bin, '-v', 'error', '-xerror', '-nostdin', '-i', str(audio),
         '-map', '0:a:0', '-f', 'null', '-'])
    work = args.work_dir.expanduser().resolve() if args.work_dir else Path(tempfile.mkdtemp(prefix='suno-tiktok-'))
    work.mkdir(parents=True, exist_ok=True)
    stage = work / 'verified-video.mp4'
    print(json.dumps({'work_dir': str(work), 'audio_duration': duration}, ensure_ascii=False), flush=True)

    attr_info = detect_audio_attribution(metadata=metadata, filename=audio, lang=args.attribution_lang)
    if args.attribution == 'none' or args.license == 'commercial':
        active_attr_text = None
    elif args.attribution != 'auto':
        active_attr_text = args.attribution
    else:
        active_attr_text = attr_info['attribution_text']

    attr_filter = None
    system_font = find_system_font()
    if active_attr_text:
        if system_font:
            attr_file = work / 'attribution.txt'
            attr_file.write_text(active_attr_text, encoding='utf-8')
            font_esc = str(system_font).replace('\\', '/').replace(':', '\\:')
            text_esc = str(attr_file).replace('\\', '/').replace(':', '\\:')
            attr_filter = (
                f"drawtext=fontfile='{font_esc}':textfile='{text_esc}':"
                f"fontsize=38:fontcolor=white@0.92:box=1:boxcolor=black@0.5:boxborderw=14:"
                f"x=60:y=1450:enable='between(t,0.5,4.0)':"
                f"alpha='if(lt(t,1.0),(t-0.5)*2,if(gt(t,3.5),(4.0-t)*2,1.0))'"
            )
        else:
            print(json.dumps({
                'attribution_warning': 'System font not found; skipping on-screen badge but applying metadata & guidance.'
            }, ensure_ascii=False), flush=True)

    meta_args = ['-map_metadata', '-1']
    if active_attr_text or attr_info['name']:
        meta_args.extend([
            '-metadata', f"title={audio.stem}",
            '-metadata', f"artist={attr_info['name'] or 'AI Music'}",
            '-metadata', f"comment={active_attr_text or 'Created with AI'}",
        ])

    for index, (image, count) in enumerate(zip(images, clip_frames)):
        clip = work / f'scene-{index:05d}.mp4'
        print(json.dumps({'scene': index + 1, 'total': len(images)}, ensure_ascii=False), flush=True)
        run([ffmpeg_bin, '-hide_banner', '-loglevel', 'error', '-xerror', '-nostdin',
             '-n', '-loop', '1', '-framerate', '25', '-i', str(image),
             '-map', '0:v:0', '-map_metadata', '-1',
             '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1',
             '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'stillimage',
             '-crf', '22', '-pix_fmt', 'yuv420p', '-threads', '4',
             '-frames:v', str(count), '-an', str(clip)])
    if offsets is not None and len(images) > 1:
        t_sec = t_frames / 25
        filter_steps = []
        last_label = '0:v'
        for idx in range(1, len(images)):
            next_label = f'{idx}:v'
            out_label = 'v_xfade' if (idx == len(images) - 1 and attr_filter) else ('v' if idx == len(images) - 1 else f'x{idx}')
            fmt = ',format=yuv420p' if (idx == len(images) - 1 and not attr_filter) else ''
            o_sec = offsets[idx - 1] / 25
            filter_steps.append(
                f'[{last_label}][{next_label}]xfade=transition=fade:duration={t_sec:.4f}:offset={o_sec:.4f}{fmt}[{out_label}]'
            )
            last_label = out_label
        if attr_filter:
            filter_steps.append(f'[v_xfade]{attr_filter},format=yuv420p[v]')
        filter_complex = ';'.join(filter_steps)
        cmd = [ffmpeg_bin, '-hide_banner', '-loglevel', 'error', '-xerror', '-nostdin', '-n']
        for i in range(len(images)):
            cmd.extend(['-i', str(work / f'scene-{i:05d}.mp4')])
        cmd.extend([
            '-i', str(audio),
            '-filter_complex', filter_complex,
            '-map', '[v]', '-map', f'{len(images)}:a:0', *meta_args,
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '22',
            '-pix_fmt', 'yuv420p', '-threads', '4',
            '-c:a', 'aac', '-b:a', '192k', '-t', str(duration),
            '-movflags', '+faststart', str(stage)
        ])
        run(cmd)
    else:
        # Only generated ASCII filenames enter the concat syntax, never user paths.
        playlist = work / 'scenes.txt'
        playlist.write_text(''.join(f"file 'scene-{i:05d}.mp4'\n" for i in range(len(images))), encoding='utf-8')
        if attr_filter:
            cmd = [ffmpeg_bin, '-hide_banner', '-loglevel', 'error', '-xerror', '-nostdin',
                   '-n', '-f', 'concat', '-safe', '1', '-i', str(playlist), '-i', str(audio),
                   '-vf', f'{attr_filter},format=yuv420p',
                   '-map', '0:v:0', '-map', '1:a:0', *meta_args,
                   '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '22', '-pix_fmt', 'yuv420p',
                   '-c:a', 'aac', '-b:a', '192k', '-t', str(duration),
                   '-movflags', '+faststart', str(stage)]
        else:
            cmd = [ffmpeg_bin, '-hide_banner', '-loglevel', 'error', '-xerror', '-nostdin',
                   '-n', '-f', 'concat', '-safe', '1', '-i', str(playlist), '-i', str(audio),
                   '-map', '0:v:0', '-map', '1:a:0', *meta_args,
                   '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', str(duration),
                   '-movflags', '+faststart', str(stage)]
        run(cmd)
    result = probe(stage, ffprobe_bin=ffprobe_bin)
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
    run([ffmpeg_bin, '-v', 'error', '-xerror', '-nostdin', '-i', str(stage),
         '-map', '0:v:0', '-map', '0:a:0', '-f', 'null', '-'])
    if before != (audio.stat().st_size, audio.stat().st_mtime_ns):
        raise RuntimeError('Source audio changed during rendering')
    (work / 'verification.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    # Exclusive creation also protects against a destination created during render.
    with output.open('xb') as dst, stage.open('rb') as src:
        shutil.copyfileobj(src, dst)
    if output.stat().st_size != stage.stat().st_size:
        raise RuntimeError('Destination copy size mismatch')
    effective_transition = args.transition if (offsets is not None and len(images) > 1) else 'none'
    report = {
        'output': str(output),
        'bytes': output.stat().st_size,
        'duration': float(result['format']['duration']),
        'resolution': '1080x1920',
        'decode_verified': True,
        'transition': effective_transition,
        'attribution': {
            'applied': bool(attr_filter),
            'text': active_attr_text,
            'generator': attr_info['generator'],
            'caption': attr_info['caption_text'],
            'ai_toggle_required': attr_info['requires_ai_toggle'],
        },
        'delivery_status': 'ready_for_export',
        'android_indexing': 'not checked by this script',
        'report': str(work / 'verification.json')
    }
    print(json.dumps(report, ensure_ascii=False))

    if attr_info['requires_ai_toggle'] or active_attr_text:
        print('\n' + '=' * 60)
        print('🛡️ ЗАХИСТ ВІД БЛОКУВАННЯ / ЗАЩИТА ОТ БЛОКИРОВОК / ACCOUNT SAFETY:')
        if attr_info['name']:
            print(f"• Джерело / Источник / Source: {attr_info['name']}")
        print('• TikTok / Shorts: обов’язково увімкніть перемикач «Створено за допомогою ШІ» /')
        print('  обязательно включите тумблер «Создано с помощью ИИ» (AI-generated content).')
        if attr_info['caption_text']:
            print('• Рекомендований підпис / Рекомендуемое описание:')
            print(f"  {attr_info['caption_text']}")
        print('=' * 60 + '\n')


if __name__ == '__main__':
    main()
