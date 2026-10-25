"""Restaura el último run de cada réplica del benchmark Claude (Python 3.10+, sin Blender).

python creation-lab/benchmarks/claude-animal-cell/restore.py [--check] [--output RUTA]
Verifica el sha256 de cada ZIP y de cada miembro antes de escribir; no sobrescribe archivos
distintos. Recrea la estructura del lote (coordinator/mapping.json, sessions/R*/runs/<id>/) para:
python creation-lab/benchmarks/claude-animal-cell/serve.py --root RUTA --port 4397
Destino por defecto: creation-lab/.local/benchmarks/claude-animal-cell/batch/.
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
DEFAULT = BASE.parents[1] / '.local' / 'benchmarks' / BASE.name / 'batch'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def put(target, data, expected):
    if target.exists():
        if sha(target.read_bytes()) != expected:
            raise SystemExit(f'Existe con contenido distinto, no se sobrescribe: {target}')
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='Solo verifica hashes, no escribe')
    parser.add_argument('--output', type=Path, default=DEFAULT)
    args = parser.parse_args()
    index = json.loads((BASE / 'fixtures' / 'index.json').read_text(encoding='utf-8'))
    mapping = (BASE / 'fixtures' / 'mapping.json').read_bytes()
    if sha(mapping) != index['mappingSha256']:
        raise SystemExit('Hash distinto en mapping.json')
    if not args.check:
        put(args.output / 'coordinator' / 'mapping.json', mapping, index['mappingSha256'])
    for replica, entry in index['fixtures'].items():
        path = BASE / 'fixtures' / entry['zip']
        if sha(path.read_bytes()) != entry['sha256']:
            raise SystemExit(f'Hash distinto en {path.name}')
        with zipfile.ZipFile(path) as archive:
            for member, expected in entry['members'].items():
                if '..' in Path(member).parts or Path(member).is_absolute():
                    raise SystemExit(f'Ruta no permitida en {path.name}: {member}')
                data = archive.read(member)
                if sha(data) != expected:
                    raise SystemExit(f'Hash distinto: {replica}/{member}')
                if not args.check:
                    put(args.output / member, data, expected)
        print(f'{replica} ({entry["finalStatus"]}): {len(entry["members"])} archivos ' + ('verificados' if args.check else 'restaurados'))
    if not args.check:
        print(f'Lote en {args.output}')


if __name__ == '__main__':
    main()
