"""Comprobación pura (sin Blender) de un módulo del diorama escolar.

python3 check_module.py RUTA/module_<nombre>.py
Ejecuta kit.py + el módulo, llama module_<nombre>() y valida mallas, partes,
región, metadatos de animación y conteos. Imprime JSON; "ok" resume el resultado.
"""
import ast
import json
import sys
from pathlib import Path

SPEC = Path(__file__).resolve().parent
CREATION = SPEC.parents[2]
sys.path.insert(0, str(CREATION))
ASSIGN = {
    'entorno': {'terreno', 'camino', 'autobus'},
    'edificio': {'edificio', 'techo', 'ventanas', 'puerta', 'torre_reloj'},
    'patio': {'asta_bandera', 'juegos', 'cancha'},
    'vida': {'arboles', 'nubes', 'estudiantes'},
}


def main(path):
    path = Path(path).resolve()
    name = path.stem.removeprefix('module_')
    errors, warnings = [], []
    source = path.read_text(encoding='utf-8')
    tree = ast.parse(source)
    if any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(tree)):
        errors.append('El módulo no debe tener imports')
    public = [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')]
    if public != [f'module_{name}']:
        errors.append(f'Debe haber una sola función pública module_{name}; hay {public}')
    kit_names = set()
    kit_tree = ast.parse((SPEC / 'kit.py').read_text(encoding='utf-8'))
    for n in kit_tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            kit_names.add(n.name)
        elif isinstance(n, ast.Assign):
            kit_names.update(t.id for t in n.targets if isinstance(t, ast.Name))
    for n in tree.body:
        defined = [n.name] if isinstance(n, (ast.FunctionDef, ast.ClassDef)) else [t.id for t in getattr(n, 'targets', []) if isinstance(t, ast.Name)]
        for d in defined:
            if d in kit_names:
                errors.append(f'Redefine un nombre del kit: {d}')
            elif d != f'module_{name}' and not d.startswith(f'_{name}_'):
                errors.append(f'Nombre de nivel superior sin prefijo _{name}_: {d}')
    ns = {'__name__': 'school_check'}
    exec(compile((SPEC / 'kit.py').read_text(encoding='utf-8'), 'kit.py', 'exec'), ns)
    result = {}
    if not errors:
        try:
            exec(compile(source, str(path), 'exec'), ns)
            result = ns[f'module_{name}']()
        except Exception as exc:  # noqa: BLE001 - informe para el autor
            errors.append(f'{type(exc).__name__}: {exc}')
    registry = ns['REGISTRY']
    expected = ASSIGN.get(name, set())
    used = {r[1] for r in registry}
    if not expected:
        errors.append('Nombre de módulo desconocido: ' + name)
    if used - expected:
        errors.append(f'part_id no asignados: {sorted(used - expected)}')
    if expected - used and not errors:
        errors.append(f'Partes sin objetos: {sorted(expected - used)}')
    if isinstance(result, dict):
        for part in expected:
            point = (result.get(part) or {}).get('label_position')
            if not (isinstance(point, (list, tuple)) and len(point) == 3):
                errors.append('Falta label_position para ' + part)
    else:
        errors.append('module_ debe devolver un dict')
    lo, hi = [1e9]*3, [-1e9]*3
    per_part, tris, clips = {}, 0, {}
    for obj_name, part, mesh, color, anim in registry:
        tris += mesh.triangles
        per_part.setdefault(part, {'objects': 0, 'triangles': 0})
        per_part[part]['objects'] += 1
        per_part[part]['triangles'] += mesh.triangles
        for v in mesh.vertices:
            for k in range(3):
                lo[k], hi[k] = min(lo[k], v[k]), max(hi[k], v[k])
        if anim:
            clips.setdefault(anim['clip'], []).append(obj_name)
    if registry:
        if lo[0] < -0.2005 or hi[0] > 0.2005 or lo[1] < -0.1505 or hi[1] > 0.1505:
            errors.append(f'Fuera de la base X/Y: min {lo} max {hi}')
        if lo[2] < -0.0565 or hi[2] > 0.14:
            warnings.append(f'Altura fuera de lo esperado: Z {lo[2]:.4f}..{hi[2]:.4f}')
    report = {'ok': not errors, 'module': name, 'errors': errors, 'warnings': warnings,
              'objects': len(registry), 'triangles': tris, 'materials': sorted({r[3] for r in registry}),
              'bboxMin': [round(x, 4) for x in lo], 'bboxMax': [round(x, 4) for x in hi],
              'parts': per_part, 'animClips': {k: len(v) for k, v in clips.items()},
              'labels': result if isinstance(result, dict) else None}
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
