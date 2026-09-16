#!/usr/bin/env python3
"""Cross-platform utilities for suno-tiktok-video."""
import ctypes
import os
from pathlib import Path
import re
import subprocess
import sys
import time

AUDIO_EXTENSIONS = ('.wav', '.flac', '.mp3', '.m4a')


def detect_platform() -> str:
    """Detect current runtime platform environment."""
    if os.environ.get('TERMUX_VERSION') or Path('/data/data/com.termux').is_dir():
        return 'android_termux'

    if sys.platform == 'darwin':
        return 'macos'

    if sys.platform.startswith('win') or os.name == 'nt':
        return 'windows'

    if sys.platform.startswith('linux'):
        # Check Android / PRoot environment
        if Path('/storage/emulated/0').is_dir() or Path('/data/data/com.termux').exists():
            return 'android_proot'

        # Check WSL
        try:
            if Path('/proc/version').is_file():
                version_text = Path('/proc/version').read_text(encoding='utf-8', errors='ignore').lower()
                if 'microsoft' in version_text or 'wsl' in version_text:
                    return 'wsl'
        except Exception:
            pass

        return 'linux'

    return sys.platform


def get_windows_downloads_dir() -> Path:
    """Resolve Windows Downloads folder via Win32 Shell API or %USERPROFILE%."""
    try:
        from ctypes import wintypes
        import uuid

        # FOLDERID_Downloads: {374DE290-123F-4565-9164-39C4925E467B}
        fid = uuid.UUID('{374DE290-123F-4565-9164-39C4925E467B}')
        fid_bytes = fid.bytes_le

        class GUID(ctypes.Structure):
            _fields_ = [('Data', ctypes.c_byte * 16)]

        guid = GUID()
        ctypes.memmove(ctypes.byref(guid.Data), fid_bytes, 16)

        path_ptr = wintypes.LPWSTR()
        # SHGetKnownFolderPath(REFKNOWNFOLDERID rfid, DWORD dwFlags, HANDLE hToken, PWSTR *ppszPath)
        res = ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(guid), 0, None, ctypes.byref(path_ptr)
        )
        if res == 0 and path_ptr.value:
            folder = Path(path_ptr.value)
            ctypes.windll.ole32.CoTaskMemFree(path_ptr)
            return folder
    except Exception:
        pass

    userprofile = os.environ.get('USERPROFILE')
    if userprofile:
        candidate = Path(userprofile) / 'Downloads'
        if candidate.is_dir():
            return candidate

    return Path.home() / 'Downloads'


def get_linux_downloads_dir() -> Path:
    """Resolve Linux Downloads directory via xdg-user-dir or user-dirs.dirs."""
    # Try xdg-user-dir binary
    try:
        proc = subprocess.run(
            ['xdg-user-dir', 'DOWNLOAD'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=False,
            timeout=2
        )
        if proc.returncode == 0 and proc.stdout.strip():
            candidate = Path(proc.stdout.strip()).expanduser()
            if candidate.is_dir():
                return candidate
    except Exception:
        pass

    # Try ~/.config/user-dirs.dirs
    user_dirs = Path.home() / '.config' / 'user-dirs.dirs'
    if user_dirs.is_file():
        try:
            content = user_dirs.read_text(encoding='utf-8', errors='ignore')
            for line in content.splitlines():
                line = line.strip()
                if line.startswith('XDG_DOWNLOAD_DIR='):
                    val = line.split('=', 1)[1].strip('"\'')
                    val = val.replace('$HOME', str(Path.home()))
                    candidate = Path(val).expanduser()
                    if candidate.is_dir():
                        return candidate
        except Exception:
            pass

    return Path.home() / 'Downloads'


def get_downloads_dir() -> Path:
    """Get the primary Downloads directory for the current platform."""
    plat = detect_platform()

    if plat == 'android_termux':
        termux_storage = Path.home() / 'storage' / 'downloads'
        if termux_storage.is_dir():
            return termux_storage
        shared = Path('/storage/emulated/0/Download')
        if shared.is_dir():
            return shared

    elif plat == 'android_proot':
        shared = Path('/storage/emulated/0/Download')
        if shared.is_dir():
            return shared
        termux_storage = Path.home() / 'storage' / 'downloads'
        if termux_storage.is_dir():
            return termux_storage

    elif plat == 'windows':
        return get_windows_downloads_dir()

    elif plat in ('linux', 'wsl'):
        return get_linux_downloads_dir()

    elif plat == 'macos':
        return Path.home() / 'Downloads'

    # Universal default fallback
    fallback = Path.home() / 'Downloads'
    if fallback.is_dir():
        return fallback
    return Path.cwd()


def check_file_stability(path: Path, wait_seconds: float = 2.0) -> bool:
    """Verify that a file is not still being downloaded or written to."""
    if not path.is_file():
        return False
    stat_before = (path.stat().st_size, path.stat().st_mtime_ns)
    if stat_before[0] == 0:
        return False
    time.sleep(wait_seconds)
    stat_after = (path.stat().st_size, path.stat().st_mtime_ns)
    return stat_before == stat_after


def find_audio_candidates(directory: Path | None = None) -> list[dict]:
    """Find and return potential audio candidates in directory, sorted by mtime descending."""
    search_dir = directory or get_downloads_dir()
    if not search_dir.is_dir():
        return []

    candidates = []
    for item in search_dir.iterdir():
        if item.name.startswith('.') or not item.is_file():
            continue
        ext = item.suffix.lower()
        if ext in AUDIO_EXTENSIONS:
            try:
                st = item.stat()
                if st.st_size > 0:
                    candidates.append({
                        'path': item,
                        'name': item.name,
                        'size': st.st_size,
                        'mtime': st.st_mtime,
                        'suffix': ext
                    })
            except (OSError, PermissionError):
                continue

    candidates.sort(key=lambda x: x['mtime'], reverse=True)
    return candidates


GENERATOR_RULES = [
    {
        'id': 'suno',
        'keywords': ['suno.com', 'suno'],
        'pattern': r'(\bsuno\.com\b|\bsuno\b|suno_)',
        'name': 'Suno AI',
        'hashtags': '#sunoai',
        'default_attribution': {
            'ru': 'Музыка: Suno AI',
            'uk': 'Музика: Suno AI',
            'en': 'Music: Suno AI'
        }
    },
    {
        'id': 'udio',
        'keywords': ['udio.com', 'udio'],
        'pattern': r'(\budio\.com\b|\budio\b|udio_)',
        'name': 'Udio AI',
        'hashtags': '#udioai',
        'default_attribution': {
            'ru': 'Музыка: Udio AI',
            'uk': 'Музика: Udio AI',
            'en': 'Music: Udio AI'
        }
    },
    {
        'id': 'mubert',
        'keywords': ['mubert.com', 'mubert'],
        'pattern': r'(\bmubert\.com\b|\bmubert\b)',
        'name': 'Mubert AI (mubert.com)',
        'hashtags': '#mubert',
        'default_attribution': {
            'ru': 'Музыка: Mubert AI (mubert.com)',
            'uk': 'Музика: Mubert AI (mubert.com)',
            'en': 'Music: Mubert AI (mubert.com)'
        }
    },
    {
        'id': 'aiva',
        'keywords': ['aiva.ai', 'aiva'],
        'pattern': r'(\baiva\.ai\b|\baiva\b)',
        'name': 'AIVA AI',
        'hashtags': '#aiva',
        'default_attribution': {
            'ru': 'Музыка: AIVA AI',
            'uk': 'Музика: AIVA AI',
            'en': 'Music: AIVA AI'
        }
    },
    {
        'id': 'boomy',
        'keywords': ['boomy.com', 'boomy'],
        'pattern': r'(\bboomy\.com\b|\bboomy\b)',
        'name': 'Boomy AI',
        'hashtags': '#boomy',
        'default_attribution': {
            'ru': 'Музыка: Boomy AI',
            'uk': 'Музика: Boomy AI',
            'en': 'Music: Boomy AI'
        }
    },
    {
        'id': 'soundraw',
        'keywords': ['soundraw.io', 'soundraw'],
        'pattern': r'(\bsoundraw\.io\b|\bsoundraw\b)',
        'name': 'Soundraw AI',
        'hashtags': '#soundraw',
        'default_attribution': {
            'ru': 'Музыка: Soundraw AI',
            'uk': 'Музика: Soundraw AI',
            'en': 'Music: Soundraw AI'
        }
    },
    {
        'id': 'musicgen',
        'keywords': ['musicgen', 'audiocraft'],
        'pattern': r'(\bmusicgen\b|\baudiocraft\b)',
        'name': 'Meta MusicGen',
        'hashtags': '#musicgen #audiocraft',
        'default_attribution': {
            'ru': 'Музыка: Meta MusicGen',
            'uk': 'Музика: Meta MusicGen',
            'en': 'Music: Meta MusicGen'
        }
    },
    {
        'id': 'yue',
        'keywords': ['yue', 'diff-rhythm', 'diffrhythm'],
        'pattern': r'(\byue\b|yue_|\bdiff-rhythm\b|\bdiffrhythm\b)',
        'name': 'YuE AI',
        'hashtags': '#yueai',
        'default_attribution': {
            'ru': 'Музыка: YuE AI',
            'uk': 'Музика: YuE AI',
            'en': 'Music: YuE AI'
        }
    },
]


def is_valid_image_file(path: str | Path) -> bool:
    """Check whether file exists, is non-empty, and has valid image magic bytes (PNG, JPEG, WebP, Netpbm, GIF, BMP)."""
    p = Path(path)
    if not p.is_file():
        return False
    try:
        size = p.stat().st_size
        if size < 8:
            return False
        with open(p, 'rb') as f:
            header = f.read(16)
        if header.startswith(b'\x89PNG\r\n\x1a\n'):
            return True
        if header.startswith(b'\xff\xd8\xff'):
            return True
        if header.startswith(b'RIFF') and header[8:12] == b'WEBP':
            return True
        if len(header) >= 3 and header[0:1] == b'P' and header[1:2] in b'123456' and header[2:3] in (b'\n', b'\r', b' ', b'\t'):
            return True
        if header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
            return True
        if header.startswith(b'BM'):
            return True
        return False
    except (OSError, PermissionError):
        return False


def is_valid_video_file(path: str | Path) -> bool:
    """Check whether file exists, is non-empty, and has valid video magic bytes (MP4/MOV, WebM/MKV)."""
    p = Path(path)
    if not p.is_file():
        return False
    try:
        size = p.stat().st_size
        if size < 16:
            return False
        with open(p, 'rb') as f:
            header = f.read(32)
        # MP4/MOV ftyp box
        if len(header) >= 12 and header[4:8] == b'ftyp':
            return True
        # WebM / MKV EBML header
        if header.startswith(b'\x1a\x45\xdf\xa3'):
            return True
        return False
    except (OSError, PermissionError):
        return False


TIKTOK_SAFE_ZONE_X = (108, 842)
TIKTOK_SAFE_ZONE_Y = (230, 1380)

EXCLUDED_CLUE_TAGS = {
    'lyrics', 'unsyncedlyrics', 'unsynced lyrics', 'syncedlyrics',
    'lyrics-xxx', 'lyrics-eng', 'lyrics-rus', 'lyrics-ukr', 'lyrics-und',
    'text', 'subtitles',
}


def escape_ffmpeg_filter_path(path: str | Path) -> str:
    """Safely escape a filesystem path for inclusion in FFmpeg filtergraphs.

    Normalizes backslashes to forward slashes (valid on Windows and POSIX),
    escapes colons for Windows drive letters (C\\:/...), and escapes
    single quotes, brackets, and commas.
    """
    p = str(Path(path).resolve()).replace('\\', '/')
    p = p.replace(':', r'\:')
    p = p.replace("'", r"\'").replace('[', r'\[').replace(']', r'\]')
    return p


def detect_audio_attribution(
    metadata: dict | None = None,
    filename: str | Path | None = None,
    lang: str = 'ru',
    user_provenance: str | None = None,
) -> dict:
    """Detect AI music generator and prepare attribution, disclosure & provenance data.

    Explicit user_provenance='human' always takes precedence over heuristic detection.
    Lyrical content tags are excluded from clues to avoid false-positive detections.
    """
    lang_code = lang.lower() if lang else 'ru'
    if lang_code not in ('ru', 'uk', 'en'):
        lang_code = 'ru'

    if user_provenance == 'human':
        return {
            'generator': None,
            'name': None,
            'is_ai': False,
            'provenance': 'human',
            'detection_source': 'user_choice',
            'attribution_text': None,
            'caption_text': None,
            'hashtags': '',
            'requires_ai_toggle': False,
            'requires_attribution': False,
        }

    detection_sources = []
    if filename:
        fname = Path(filename).name
        detection_sources.append(('filename', fname))

    if metadata and isinstance(metadata, dict):
        fmt_tags = metadata.get('format', {}).get('tags', {})
        if isinstance(fmt_tags, dict):
            for k, v in fmt_tags.items():
                if k.lower() not in EXCLUDED_CLUE_TAGS:
                    detection_sources.append((f'tag:{k}', str(v)))
        for s in metadata.get('streams', []):
            st_tags = s.get('tags', {})
            if isinstance(st_tags, dict):
                for k, v in st_tags.items():
                    if k.lower() not in EXCLUDED_CLUE_TAGS:
                        detection_sources.append((f'tag:{k}', str(v)))

    detected = None
    matched_source = None
    for src_type, src_val in detection_sources:
        for rule in GENERATOR_RULES:
            if re.search(rule['pattern'], src_val, re.IGNORECASE):
                detected = rule
                matched_source = src_type
                break
        if detected:
            break

    if not detected:
        prov = user_provenance if user_provenance in ('human', 'ai', 'mixed') else 'unknown'
        return {
            'generator': None,
            'name': None,
            'is_ai': (prov == 'ai'),
            'provenance': prov,
            'detection_source': 'user_choice' if user_provenance in ('human', 'ai', 'mixed') else 'none',
            'attribution_text': None,
            'caption_text': None,
            'hashtags': '',
            'requires_ai_toggle': (prov == 'ai'),
            'requires_attribution': False,
        }

    name = detected['name']
    attr_text = detected['default_attribution'].get(lang_code, detected['default_attribution']['ru'])
    hashtags = detected['hashtags']

    if lang_code == 'uk':
        caption = f"Музика створена за допомогою {name}. {hashtags} #християнськіпісні"
    elif lang_code == 'en':
        caption = f"Music created with {name}. {hashtags} #christiansongs"
    else:
        caption = f"Музыка создана с помощью {name}. {hashtags} #христианскиепесни"

    prov = user_provenance if user_provenance in ('ai', 'mixed') else 'ai'
    return {
        'generator': detected['id'],
        'name': name,
        'is_ai': True,
        'provenance': prov,
        'detection_source': matched_source or 'heuristic',
        'attribution_text': attr_text,
        'caption_text': caption,
        'hashtags': hashtags,
        'requires_ai_toggle': True,
        'requires_attribution': True,
    }


def find_system_font(platform: str | None = None) -> Path | None:
    """Find an available TrueType/OpenType system font for FFmpeg drawtext."""
    plat = platform or detect_platform()
    candidates: list[Path] = []

    if plat in ('android_termux', 'android_proot'):
        candidates = [
            Path('/system/fonts/Roboto-Regular.ttf'),
            Path('/system/fonts/DroidSans.ttf'),
            Path.home() / '.termux' / 'font.ttf',
        ]
    elif plat == 'macos':
        candidates = [
            Path('/System/Library/Fonts/Supplemental/Arial.ttf'),
            Path('/System/Library/Fonts/Helvetica.ttc'),
            Path('/Library/Fonts/Arial.ttf'),
            Path('/System/Library/Fonts/SFNS.ttf'),
        ]
    elif plat == 'windows':
        windir = os.environ.get('WINDIR', 'C:\\Windows')
        fonts_dir = Path(windir) / 'Fonts'
        candidates = [
            fonts_dir / 'arial.ttf',
            fonts_dir / 'calibri.ttf',
            fonts_dir / 'segoeui.ttf',
        ]
    elif plat in ('linux', 'wsl'):
        candidates = [
            Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
            Path('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'),
            Path('/usr/share/fonts/truetype/freefont/FreeSans.ttf'),
        ]
    else:
        candidates = [
            Path('/System/Library/Fonts/Supplemental/Arial.ttf'),
            Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
            Path('/system/fonts/Roboto-Regular.ttf'),
        ]

    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate
        except (OSError, PermissionError):
            continue
    return None

