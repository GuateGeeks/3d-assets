"""Bridge tests. The round trip runs only with a Python that has `bpy` and a cotizador checkout:

    GG_TEST_BPY=<python with bpy> GG_COTIZADOR=<cotizador> python3 -m unittest discover -s procedural-web/tests -v
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pw', HERE / 'pw.py')
pw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pw)


class ModuleFormat(unittest.TestCase):
    def test_write_then_read_keeps_values_and_writes_like_json_stringify(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / 'm.js'
            data = {'SOURCE': {'file': 'a.glb', 'edited': None}, 'RIG_H': {'hips': {'parent': 'root', 'at': [0.0, 0.37, 1.0]}}}
            pw.write_module(file, '// cabecera', data)
            text = file.read_text(encoding='utf-8')
            self.assertIn('"at":[0,0.37,1]', text)  # integral floats as JavaScript prints them
            self.assertEqual(pw.read_module(file), {'SOURCE': {'file': 'a.glb', 'edited': None}, 'RIG_H': {'hips': {'parent': 'root', 'at': [0, 0.37, 1]}}})

    def test_close_compares_nested_numbers_with_tolerance(self):
        self.assertTrue(pw.close([[0, 1.0001], [2]], [[0, 1], [2.0001]]))
        self.assertFalse(pw.close([[0, 1.001]], [[0, 1]]))
        self.assertFalse(pw.close([1, 2], [1, 2, 3]))

    def test_landmarks_follow_the_rig(self):
        rig = {k: {'parent': None, 'at': [x, y, 0]} for k, x, y in [('hips', 0, .4), ('shinL', .07, .2), ('foreL', .17, .5), ('armL', .15, .63), ('head', 0, .68), ('legL', .07, .4)]}
        parts = [{'id': 'head', 'bone': 'head', 'vertices': [[.1, .8, .1], [-.12, .79, 0], [0, 1, 0]]}, {'id': 'eyeL', 'bone': 'head', 'vertices': [[.05, .79, .12]]}]
        L = pw.landmarks_from({'ankle': .07, 'chin': .7}, rig, {'bag': {'parts': parts}}, .0075)
        self.assertEqual((L['hip'], L['knee'], L['elbow'], L['shoulder'], L['neckBase'], L['legX'], L['top']), (.4, .2, .5, .63, .68, .07, 1))
        self.assertEqual(L['ankle'], .07)


@unittest.skipUnless(os.environ.get('GG_TEST_BPY') and os.environ.get('GG_COTIZADOR'), 'GG_TEST_BPY y GG_COTIZADOR')
class RoundTrip(unittest.TestCase):
    def test_export_then_import_without_edits_changes_nothing(self):
        node = os.environ.get('GG_NODE') or shutil.which('node')
        base = [sys.executable, str(HERE / 'pw.py'), '--engine', 'bpy', '--bpy', os.environ['GG_TEST_BPY'], '--cotizador', os.environ['GG_COTIZADOR'], '--node', node]
        for model in ('nino', 'nina'):
            out = json.loads(subprocess.check_output(base + ['export', '--model', model], text=True))
            run = HERE / '.local/runs' / sorted(p.name for p in (HERE / '.local/runs').glob(f'*-export-{model}'))[-1]
            back = json.loads(subprocess.check_output(base + ['import', '--model', model, '--blend', str(run / out['blend'])], text=True))
            self.assertEqual(back['modelChanges'], [], model)
            self.assertFalse(back['applied'])
            self.assertEqual(out['actions'], len(json.loads((HERE / 'poses.json').read_text())['clips']))
            # convention: three.js 'YXZ' rotations = Blender 'ZXY' pose rotations, (x, y, z) -> (x, -z, y)
            three = json.loads(subprocess.check_output([node, str(HERE / 'tests/joints_three.mjs'), os.environ['GG_COTIZADOR'], model], text=True))
            text = subprocess.check_output([os.environ['GG_TEST_BPY'], str(HERE / 'tests/joints_blender.py'), '--', str(run / out['blend'])], text=True)
            blend = json.loads(next(line for line in text.splitlines() if line.startswith('JOINTS'))[6:])
            for clip, joints in three.items():
                for bone, p in joints.items():
                    self.assertLess(max(abs(a - b) for a, b in zip(p, blend[clip][bone])), 1e-4, f'{model} {clip} {bone}')


if __name__ == '__main__':
    unittest.main()
