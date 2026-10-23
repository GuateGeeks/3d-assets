"""Check repository skill entrypoints and local Markdown links using only stdlib."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


def check(root):
    root = root.resolve()
    skills = root / '.agents/skills'
    entries = sorted(skills.glob('*/SKILL.md'))
    errors, links = [], 0
    if not entries:
        errors.append('No .agents/skills/*/SKILL.md entrypoints found')
    for entry in entries:
        source = entry.read_text(encoding='utf-8-sig')
        frontmatter = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', source, re.S)
        if not frontmatter:
            errors.append(f'{entry.relative_to(root)}: missing frontmatter')
            continue
        fields = dict(re.findall(r'^(name|description):\s*(.+)$', frontmatter[1], re.M))
        name = fields.get('name', '').strip().strip('\"\'')
        if name != entry.parent.name or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name):
            errors.append(f'{entry.relative_to(root)}: name must match its folder')
        if not fields.get('description', '').strip():
            errors.append(f'{entry.relative_to(root)}: missing description')
    # Check the inline links used in our skills, not arbitrary Markdown/YAML
    # or remote URL availability. Anchors do not change the file target.
    for file in sorted(skills.rglob('*.md')):
        source = re.sub(r'^```.*?^```[^\n]*$', '', file.read_text(encoding='utf-8-sig'), flags=re.M | re.S)
        for target in re.findall(r'\]\((<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)', source):
            target = target.strip('<>')
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            links += 1
            resolved = (file.parent / unquote(url.path)).resolve()
            if not resolved.is_relative_to(root) or not resolved.exists():
                errors.append(f'{file.relative_to(root)}: unavailable local link {target}')
    return {'status': 'FAIL' if errors else 'PASS', 'skills': len(entries), 'localLinks': links, 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    report = check(args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(bool(report['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
