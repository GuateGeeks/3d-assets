"""Restaura los entregables del benchmark escuela flat (Python 3.10+, sin Blender).

python creation-lab/benchmarks/school-flat-20261023/restore.py [--check] [--output RUTA]
Verifica el sha256 de cada ZIP y de cada miembro antes de escribir. No sobrescribe
archivos distintos; los idénticos se omiten. Destino por defecto:
creation-lab/.local/benchmarks/school-flat-20261023/<condición>/.
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
DEFAULT = BASE.parents[1] / '.local' / 'benchmarks' / BASE.name


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='Solo verifica hashes, no escribe')
    parser.add_argument('--output', type=Path, default=DEFAULT)
    args = parser.parse_args()
    index = json.loads((BASE / 'fixtures' / 'index.json').read_text(encoding='utf-8'))
    for name, entry in index['fixtures'].items():
        path = BASE / 'fixtures' / entry['zip']
        if sha(path.read_bytes()) != entry['sha256']:
            raise SystemExit(f'Hash distinto en {path.name}')
        with zipfile.ZipFile(path) as archive:
            for member, expected in entry['members'].items():
                if '..' in Path(member).parts or Path(member).is_absolute():
                    raise SystemExit(f'Ruta no permitida en {path.name}: {member}')
                data = archive.read(member)
                if sha(data) != expected:
                    raise SystemExit(f'Hash distinto: {name}/{member}')
                if args.check:
                    continue
                target = args.output / name / member
                if target.exists():
                    if sha(target.read_bytes()) != expected:
                        raise SystemExit(f'Existe con contenido distinto, no se sobrescribe: {target}')
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        print(f'{name}: {len(entry["members"])} archivos ' + ('verificados' if args.check else f'en {args.output / name}'))


if __name__ == '__main__':
    main()
