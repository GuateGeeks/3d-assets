"""Concatena kit + módulos + compositor en un generador único para iterate.py.

python3 assemble.py OUT.py MODULE.py [MODULE.py ...]
No modifica los módulos: los copia literalmente, en orden, con su sha256.
"""
import hashlib
import sys
from pathlib import Path

SPEC = Path(__file__).resolve().parent
COMPOSER = '''

# ==== COMPOSITOR (coordinador) ====
def build():
    parts = {}
    for fn in (%s):
        got = fn()
        overlap = set(parts) & set(got)
        if overlap:
            raise ValueError('Partes duplicadas entre módulos: ' + str(sorted(overlap)))
        parts.update(got)
    return {
        'title': 'Escuela · diorama Flat Minimal',
        'design_notes': [
            'Estilo Flat Shaded / Minimalist: caras planas, paleta limitada, sin texturas.',
            'Condición solo-Opus: todos los módulos, animación y visor escritos por Opus 5.5; kit y composición (coordinador Opus).',
            'Los objetos animados llevan anim_* para el paso de animación; esta escena es estática.',
        ],
        'parts': parts,
    }
'''


def main(out, modules):
    chunks = [(SPEC / 'kit.py').read_text(encoding='utf-8')]
    names = []
    for path in modules:
        path = Path(path)
        text = path.read_text(encoding='utf-8')
        digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
        name = path.stem.removeprefix('module_')
        names.append('module_' + name)
        chunks.append(f'\n\n# ==== MÓDULO {name} · {path.name} · sha256 {digest} ====\n{text}')
    chunks.append(COMPOSER % ', '.join(names))
    Path(out).write_text(''.join(chunks), encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
