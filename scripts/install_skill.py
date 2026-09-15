#!/usr/bin/env python3
import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import tempfile
import uuid


SKILL_NAME = 'suno-tiktok-video'
SKILL_NAMES = (SKILL_NAME, 'dual-image-pipeline')

# These bundled skills consist of instructions and Python helpers. In particular,
# runtime credentials, artwork, generated media and bytecode are not packages.
SOURCE_SUFFIXES = {'.md', '.py'}
EXCLUDED_NAMES = {
    '__pycache__', '.git', '.cache', 'cache', 'caches', 'node_modules',
    '.venv', 'venv', 'logs', 'outputs', 'generated_images', 'secrets',
    'credentials', 'private',
}


def source_files(source):
    """Validate links before filtering; return only distributable skill files."""
    if source.is_symlink():
        raise ValueError(f'Source symlinks are not supported: {source}')
    files = []

    def walk(directory, excluded=False):
        for entry in sorted(directory.iterdir()):
            if entry.is_symlink():
                raise ValueError(f'Source symlinks are not supported: {entry}')
            skip = excluded or entry.name.startswith('.') or entry.name.lower() in EXCLUDED_NAMES
            if entry.is_dir():
                walk(entry, skip)
            elif not skip and entry.suffix.lower() in SOURCE_SUFFIXES:
                if not entry.is_file():
                    raise ValueError(f'Source must contain regular files: {entry}')
                files.append(entry.relative_to(source))

    walk(source)
    if Path('SKILL.md') not in files:
        raise FileNotFoundError(f'SKILL.md: {source}')
    return files


def check_overlay(target, files):
    """Never follow an installed link while replacing a packaged file."""
    for relative in files:
        for parent in reversed(relative.parents):
            location = target / parent
            if location.is_symlink() or (location.exists() and not location.is_dir()):
                raise ValueError(f'Installed path conflicts with source directory: {location}')
        location = target / relative
        if location.is_symlink() or (location.exists() and not location.is_file()):
            raise ValueError(f'Installed path conflicts with source file: {location}')


def install(destination, source=None, *, skill_name=SKILL_NAME, update=False):
    """Install code/docs; opt-in updates preserve originals in a sibling backup."""
    if skill_name not in SKILL_NAMES:
        raise ValueError(f'Unknown skill: {skill_name}')
    if source is None:
        source = Path(__file__).resolve().parents[1] / 'skills' / skill_name
    source = Path(source).expanduser().absolute()
    if source.is_symlink():
        raise ValueError(f'Source symlinks are not supported: {source}')
    if not (source / 'SKILL.md').is_file():
        raise FileNotFoundError(f'SKILL.md: {source}')
    destination = Path(destination).expanduser().absolute()
    target = destination / skill_name
    if (target.exists() or target.is_symlink()) and not update:
        raise FileExistsError(target)
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        raise ValueError(f'Existing skill must be a real directory: {target}')
    if (source.resolve() == target.resolve() or source.resolve() in destination.resolve().parents
            or destination.resolve() == source.resolve() or target.resolve() in source.resolve().parents):
        raise ValueError('Source and installed destination must not overlap')
    files = source_files(source)
    if target.exists():
        check_overlay(target, files)
    destination.mkdir(parents=True, exist_ok=True)
    # Build entirely before moving the original. Copies of existing local files
    # remain local; the source allowlist applies only to the repository package.
    stage = Path(tempfile.mkdtemp(prefix=f'.{skill_name}.staging-', dir=destination))
    backup = None
    try:
        if target.exists():
            shutil.copytree(target, stage, symlinks=True, dirs_exist_ok=True)
        for relative in files:
            output = stage / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relative, output)
        if target.exists():
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            backup = destination / f'.{skill_name}.backup-{stamp}-{uuid.uuid4().hex[:12]}'
            target.rename(backup)
        try:
            stage.rename(target)
        except OSError:
            if backup is not None:
                backup.rename(target)
            raise
    finally:
        # Only a uniquely named, installer-owned staging copy can be removed.
        if stage.exists():
            shutil.rmtree(stage)
    if backup is not None:
        print(f'Резервна копія / Резервная копия / Backup: {backup}')
    return target


def main():
    parser = argparse.ArgumentParser(
        description='Встановити скіл / Установить скилл / Install skill')
    parser.add_argument('--destination', type=Path,
                        default=Path.home() / '.agents' / 'skills',
                        help='Каталог скілів / Каталог скиллов / Skills directory')
    parser.add_argument('--skill', choices=SKILL_NAMES, default=SKILL_NAME,
                        help='Скіл / Скилл / Skill to install or update')
    parser.add_argument('--update', action='store_true',
                        help='Оновити з резервною копією / Обновить с резервной копией / '
                             'Update with a complete backup; retain local-only files')
    args = parser.parse_args()
    try:
        target = install(args.destination, skill_name=args.skill, update=args.update)
    except FileExistsError as error:
        parser.exit(2, f'Вже існує; не змінено / Уже существует; не изменено / '
                       f'Already exists; unchanged: {error}\n')
    except (OSError, ValueError) as error:
        parser.exit(1, f'Помилка / Ошибка / Error: {error}\n')
    print(f'Встановлено / Установлено / Installed: {target}')
    print(f'Codex: /skills → {args.skill}')


if __name__ == '__main__':
    main()
