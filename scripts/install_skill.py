#!/usr/bin/env python3
import argparse
from pathlib import Path
import shutil


SKILL_NAME = 'suno-tiktok-video'


def install(destination, source=None):
    if source is None:
        source = Path(__file__).resolve().parents[1] / 'skills' / SKILL_NAME
    source = Path(source)
    if not (source / 'SKILL.md').is_file():
        raise FileNotFoundError(f'SKILL.md: {source}')
    destination = Path(destination).expanduser().absolute()
    target = destination / SKILL_NAME
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    return target


def main():
    parser = argparse.ArgumentParser(
        description='Встановити скіл / Установить скилл / Install skill')
    parser.add_argument('--destination', type=Path,
                        default=Path.home() / '.agents' / 'skills',
                        help='Каталог скілів / Каталог скиллов / Skills directory')
    args = parser.parse_args()
    try:
        target = install(args.destination)
    except FileExistsError as error:
        parser.exit(2, f'Вже існує; не змінено / Уже существует; не изменено / '
                       f'Already exists; unchanged: {error}\n')
    except OSError as error:
        parser.exit(1, f'Помилка / Ошибка / Error: {error}\n')
    print(f'Встановлено / Установлено / Installed: {target}')
    print('Codex: /skills → suno-tiktok-video')


if __name__ == '__main__':
    main()
