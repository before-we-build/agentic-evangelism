#!/usr/bin/env python3
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
LANGS = ('en', 'ru', 'uk')


def check(root=ROOT):
    errors = []
    catalogs = {lang: {p.name for p in (root / 'docs' / lang).glob('*.md')}
                for lang in LANGS}
    all_names = set().union(*catalogs.values())
    if not all_names:
        errors.append('docs: empty')
    for lang, names in catalogs.items():
        for name in all_names - names:
            errors.append(f'docs/{lang}/{name}: missing')
    for name in all_names:
        commands = {}
        for lang in LANGS:
            p = root / 'docs' / lang / name
            if p.exists():
                commands[lang] = re.findall(r'```sh\n(.*?)\n```', p.read_text(), re.S)
        if len(commands) == 3 and not all(v == commands['en'] for v in commands.values()):
            errors.append(f'{name}: shell commands differ between languages')
    skill = root / 'skills' / 'suno-tiktok-video'
    for base in (skill / 'SKILL.md', skill / 'references' / 'android.md',
                 skill / 'references' / 'storyboard.md'):
        for suffix in ('', '.ru', '.uk'):
            p = base.with_name(base.stem + suffix + '.md')
            if not p.is_file():
                errors.append(f'{p.relative_to(root)}: missing')
    for p in root.rglob('*.md'):
        if '.git' in p.parts:
            continue
        prose = re.sub(r'```.*?```', '', p.read_text(), flags=re.S)
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', prose):
            target = target.strip().strip('<>')
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith('#'):
                continue
            local = unquote(parsed.path)
            if local and not (p.parent / local).exists():
                errors.append(f'{p.relative_to(root)}: broken link {target}')
    return errors


if __name__ == '__main__':
    errors = check()
    for error in errors:
        print(error)
    print('Документація / Документация / Documentation: ' + ('FAIL' if errors else 'OK'))
    sys.exit(bool(errors))
