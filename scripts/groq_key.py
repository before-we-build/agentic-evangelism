#!/usr/bin/env python3
"""Keep a Groq key in private PRoot storage and pass it only to lyric alignment."""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile


KEY_PATH = Path.home() / ".config" / "agentic-evangelism" / "groq-api-key"
ALIGN_SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "suno-tiktok-video" / "scripts" / "align_lyrics.py"


def save_key(path: Path, key: str) -> None:
    key = key.strip()
    if not key or any(char.isspace() for char in key):
        raise ValueError("Groq key must be nonempty and contain no whitespace")

    parent = path.parent
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError("Private key directory must be a real directory")
    parent.chmod(0o700)

    descriptor, temporary_name = tempfile.mkstemp(prefix=".groq-key-", dir=parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(key)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def load_key(path: Path) -> str:
    if path.is_symlink():
        raise ValueError("Groq key file must not be a symlink")
    details = path.stat()
    if not stat.S_ISREG(details.st_mode) or details.st_mode & 0o077:
        raise ValueError("Groq key file must be private (mode 600)")
    if details.st_uid != os.getuid():
        raise ValueError("Groq key file must belong to the current user")
    key = path.read_text(encoding="utf-8").strip()
    if not key:
        raise ValueError("Groq key file is empty")
    return key


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("set", "status", "align"))
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if args.command == "set":
        if args.arguments:
            parser.error("set accepts no arguments; never pass the key on the command line")
        if not sys.stdin.isatty():
            parser.error("set needs an interactive terminal for hidden input")
        key = getpass.getpass("Groq API key (hidden): ")
        save_key(KEY_PATH, key)
        print(f"Saved private key at {KEY_PATH}; value not shown")
        return 0

    if args.command == "status":
        if args.arguments:
            parser.error("status accepts no arguments")
        try:
            load_key(KEY_PATH)
        except FileNotFoundError:
            print("Groq key: not configured")
            return 1
        print("Groq key: configured and private; value not shown")
        return 0

    if not ALIGN_SCRIPT.is_file():
        parser.error(f"Lyric alignment script not found: {ALIGN_SCRIPT}")
    arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
    if not arguments:
        parser.error("align needs arguments such as --audio and --storyboard")
    key = load_key(KEY_PATH)
    environment = os.environ.copy()
    environment["GROQ_API_KEY"] = key
    sdk_python = Path.home() / ".local" / "share" / "agentic-evangelism" / "groq-sdk-venv" / "bin" / "python"
    python = str(sdk_python) if sdk_python.is_file() and "--dry-run" not in arguments else sys.executable
    return subprocess.run([python, str(ALIGN_SCRIPT), *arguments], env=environment, check=False).returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        sys.exit(f"Groq key error: {error}")
