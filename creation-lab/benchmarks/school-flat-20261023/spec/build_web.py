"""Inyecta window.SCHOOL (GLB animado + partes + clips) en el visor web.

python3 build_web.py INDEX.html ANIMATED.glb PARTS.json BRIEF.json OUT.html
"""
import base64
import hashlib
import json
import sys
from pathlib import Path


def main(index, glb, parts, brief, out):
    page = Path(index).read_text(encoding='utf-8')
    assert page.count('<!--SCHOOL_DATA-->') == 1, 'marcador SCHOOL_DATA ausente o repetido'
    parts_doc = json.loads(Path(parts).read_text(encoding='utf-8'))
    brief_doc = json.loads(Path(brief).read_text(encoding='utf-8'))
    data = {
        'glb': 'data:model/gltf-binary;base64,' + base64.b64encode(Path(glb).read_bytes()).decode('ascii'),
        'title': parts_doc.get('title'),
        'designNotes': parts_doc.get('designNotes'),
        'parts': [{k: p.get(k) for k in ('id', 'label', 'function', 'objects', 'positionGltf')} for p in parts_doc['parts']],
        'clips': brief_doc['animations']['clips'],
    }
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    script = f'<script>window.SCHOOL = {payload};</script>'
    Path(out).write_text(page.replace('<!--SCHOOL_DATA-->', script), encoding='utf-8')
    print(json.dumps({'out': out, 'bytes': Path(out).stat().st_size,
                      'glbSha256': hashlib.sha256(Path(glb).read_bytes()).hexdigest(),
                      'indexSha256': hashlib.sha256(Path(index).read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main(*sys.argv[1:6])
