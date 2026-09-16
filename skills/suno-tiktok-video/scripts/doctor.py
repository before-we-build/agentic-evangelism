#!/usr/bin/env python3
"""Diagnostic doctor for suno-tiktok-video environment and dependencies."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

try:
    from platform_utils import detect_platform, get_downloads_dir, find_system_font
except ImportError:
    from .platform_utils import detect_platform, get_downloads_dir, find_system_font


def check_python() -> dict:
    return {
        'version': f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}',
        'ok': sys.version_info >= (3, 10),
    }


def find_tool(name: str, custom_path: str | None = None) -> str | None:
    if custom_path:
        p = Path(custom_path).expanduser().resolve()
        return str(p) if p.is_file() and shutil.which(str(p)) else None
    return shutil.which(name)


def check_groq() -> dict:
    sdk_installed = False
    try:
        import groq
        sdk_installed = True
    except ImportError:
        pass
    has_key = bool(os.environ.get("GROQ_API_KEY", "").strip())
    return {
        'sdk_installed': sdk_installed,
        'key_configured': has_key,
        'ok': sdk_installed and has_key,
    }


def check_disk_space(target_dir: Path | None = None) -> dict:
    p = target_dir or Path(tempfile.gettempdir())
    try:
        usage = shutil.disk_usage(p)
        free_mb = usage.free / (1024 * 1024)
        return {
            'free_mb': round(free_mb, 1),
            'ok': free_mb >= 200,
        }
    except Exception:
        return {'free_mb': None, 'ok': True}


def check_ffmpeg_features(ffmpeg_bin: str) -> dict:
    font = find_system_font()
    features = {
        'libx264': False,
        'aac': False,
        'scale_filter': False,
        'pad_filter': False,
        'xfade_filter': False,
        'ass_filter': False,
        'drawtext_filter': False,
        'system_font': str(font) if font else None,
    }
    try:
        codecs_proc = subprocess.run(
            [ffmpeg_bin, '-hide_banner', '-codecs'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            check=False
        )
        codecs_out = codecs_proc.stdout
        features['libx264'] = 'libx264' in codecs_out
        features['aac'] = ' aac ' in codecs_out or ' aac' in codecs_out

        filters_proc = subprocess.run(
            [ffmpeg_bin, '-hide_banner', '-filters'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            check=False
        )
        filters_out = filters_proc.stdout
        features['scale_filter'] = ' scale ' in filters_out or '\nscale ' in filters_out
        features['pad_filter'] = ' pad ' in filters_out or '\npad ' in filters_out
        features['xfade_filter'] = ' xfade ' in filters_out or '\nxfade ' in filters_out
        features['ass_filter'] = ' ass ' in filters_out or '\nass ' in filters_out
        features['drawtext_filter'] = ' drawtext ' in filters_out or '\ndrawtext ' in filters_out
    except Exception as e:
        features['error'] = str(e)

    features['ok'] = (
        features['libx264'] and
        features['aac'] and
        features['scale_filter'] and
        features['pad_filter'] and
        features['xfade_filter']
    )
    return features


def test_render(ffmpeg_bin: str, ffprobe_bin: str, work_dir: Path | None = None) -> dict:
    """Run a 1-second synthetic render test to verify the complete video pipeline."""
    target_dir = work_dir or Path(tempfile.mkdtemp(prefix='suno-doctor-'))
    test_out = target_dir / 'doctor_test.mp4'

    cmd = [
        ffmpeg_bin, '-hide_banner', '-loglevel', 'error', '-xerror', '-nostdin', '-y',
        '-f', 'lavfi', '-i', 'color=c=navy:s=1080x1920:d=1.0:r=25',
        '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo:d=1.0',
        '-vf', 'setsar=1',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k',
        '-movflags', '+faststart',
        str(test_out)
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        probe_proc = subprocess.run(
            [ffprobe_bin, '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(test_out)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=True
        )
        data = json.loads(probe_proc.stdout)
        video = [s for s in data.get('streams', []) if s.get('codec_type') == 'video']
        audio = [s for s in data.get('streams', []) if s.get('codec_type') == 'audio']
        ok = (
            len(video) == 1 and
            len(audio) == 1 and
            video[0].get('codec_name') == 'h264' and
            int(video[0].get('width', 0)) == 1080 and
            int(video[0].get('height', 0)) == 1920 and
            audio[0].get('codec_name') == 'aac'
        )
        return {'ok': ok, 'details': 'Synthetic 1080x1920 H.264/AAC render succeeded'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
    finally:
        if test_out.exists():
            try:
                test_out.unlink()
            except OSError:
                pass


def run_doctor(ffmpeg_arg: str | None = None,
               ffprobe_arg: str | None = None,
               test_render_flag: bool = False,
               json_output: bool = False) -> int:
    plat = detect_platform()
    downloads = get_downloads_dir()
    py_check = check_python()

    ffmpeg_path = find_tool('ffmpeg', ffmpeg_arg)
    ffprobe_path = find_tool('ffprobe', ffprobe_arg)

    ffmpeg_features = check_ffmpeg_features(ffmpeg_path) if ffmpeg_path else {'ok': False}
    groq_info = check_groq()
    disk_info = check_disk_space(downloads if downloads.is_dir() else None)

    base_video_ok = (
        py_check['ok'] and
        bool(ffmpeg_path) and
        bool(ffprobe_path) and
        ffmpeg_features.get('ok', False)
    )
    karaoke_ass_ok = base_video_ok and ffmpeg_features.get('ass_filter', False)
    badge_overlay_ok = base_video_ok and ffmpeg_features.get('drawtext_filter', False) and bool(ffmpeg_features.get('system_font'))

    report = {
        'platform': plat,
        'downloads_dir': str(downloads),
        'downloads_exists': downloads.is_dir(),
        'python': py_check,
        'ffmpeg_found': bool(ffmpeg_path),
        'ffmpeg_path': ffmpeg_path,
        'ffprobe_found': bool(ffprobe_path),
        'ffprobe_path': ffprobe_path,
        'ffmpeg_features': ffmpeg_features,
        'groq': groq_info,
        'disk': disk_info,
        'capabilities': {
            'base_video': base_video_ok,
            'karaoke_ass': karaoke_ass_ok,
            'badge_overlay': badge_overlay_ok,
            'groq_alignment': groq_info['ok'],
        },
    }

    if test_render_flag and ffmpeg_path and ffprobe_path and ffmpeg_features.get('ok'):
        report['test_render'] = test_render(ffmpeg_path, ffprobe_path)
    elif test_render_flag:
        report['test_render'] = {'ok': False, 'reason': 'FFmpeg or required codecs unavailable'}

    all_ok = (
        base_video_ok and
        (not test_render_flag or report.get('test_render', {}).get('ok', False))
    )
    report['overall_ok'] = all_ok

    if json_output:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        status_sym = '✓' if all_ok else '✗'
        print(f'=== Suno-TikTok-Video Doctor [{status_sym}] ===')
        print(f'Platform:      {plat}')
        print(f'Downloads:     {downloads} ({"exists" if downloads.is_dir() else "not found"})')
        print(f'Python:        {py_check["version"]} ({"OK" if py_check["ok"] else "Needs 3.10+"})')
        print(f'FFmpeg:        {ffmpeg_path or "NOT FOUND"}')
        print(f'FFprobe:       {ffprobe_path or "NOT FOUND"}')
        if ffmpeg_path:
            feats = ffmpeg_features
            print(f'  libx264:     {"✓" if feats.get("libx264") else "✗ MISSING"}')
            print(f'  aac:         {"✓" if feats.get("aac") else "✗ MISSING"}')
            print(f'  scale:       {"✓" if feats.get("scale_filter") else "✗ MISSING"}')
            print(f'  pad:         {"✓" if feats.get("pad_filter") else "✗ MISSING"}')
            print(f'  xfade:       {"✓" if feats.get("xfade_filter") else "✗ MISSING"}')
            print(f'  ass (libass):{"✓" if feats.get("ass_filter") else "✗ MISSING (karaoke disabled)"}')
            print(f'  drawtext:    {"✓" if feats.get("drawtext_filter") else "✗ MISSING"}')
            print(f'  system font: {"✓ (" + feats.get("system_font") + ")" if feats.get("system_font") else "✗ NOT FOUND"}')
        print(f'Groq SDK:      {"✓" if groq_info["sdk_installed"] else "✗ Not installed"} (Key: {"Configured" if groq_info["key_configured"] else "Missing"})')
        disk_str = f"{disk_info['free_mb']} MB" if disk_info['free_mb'] is not None else "Unknown"
        print(f'Free Disk:     {disk_str} ({"OK" if disk_info["ok"] else "LOW SPACE < 200MB"})')
        print(f'Capabilities:')
        print(f'  Base Video:  {"YES" if base_video_ok else "NO"}')
        print(f'  Karaoke ASS: {"YES" if karaoke_ass_ok else "NO"}')
        print(f'  Badge:       {"YES" if badge_overlay_ok else "NO"}')
        print(f'  Groq ASR:    {"YES" if groq_info["ok"] else "NO"}')
        if test_render_flag:
            tr = report.get('test_render', {})
            print(f'Test Render:   {"✓" if tr.get("ok") else "✗ FAILED (" + tr.get("error", "unknown") + ")"}')
        print(f'Overall Ready: {"YES" if all_ok else "NO"}')

    return 0 if all_ok else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffmpeg', help='Explicit path to ffmpeg binary')
    parser.add_argument('--ffprobe', help='Explicit path to ffprobe binary')
    parser.add_argument('--test-render', action='store_true', help='Execute 1-second synthetic render test')
    parser.add_argument('--json', action='store_true', help='Output JSON report')
    args = parser.parse_args()

    sys.exit(run_doctor(
        ffmpeg_arg=args.ffmpeg,
        ffprobe_arg=args.ffprobe,
        test_render_flag=args.test_render,
        json_output=args.json
    ))


if __name__ == '__main__':
    main()
