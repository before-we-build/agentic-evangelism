#!/usr/bin/env python3
"""Cross-platform utilities for suno-tiktok-video."""
import ctypes
import os
from pathlib import Path
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
