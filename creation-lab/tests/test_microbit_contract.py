"""Node-contract checker for the micro:bit GLB, on synthetic minimal GLBs (no Blender)."""
import copy
import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB.parent
EXPERIMENT = LAB / 'experiments' / 'microbit-v2'
CONTRACT = json.loads((ROOT / 'studio/examples/microbit/node-contract.json').read_text(encoding='utf-8'))
SCALE = {'longestDimension': 0.052, 'tolerance': 0.02}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic(width=0.052, shared_led_material=False, duplicate=None, omit=None, parent_scale=1.0,
              led_shares_with=None, led_two_primitives=False, caps_share_material=False):
    """Minimal glTF dict: one box node per contract part, each on its own material; the PCB sets the extent.

    shared_led_material: led_1_0 reuses led_0_0's material (LED vs LED only).
    led_shares_with: that part reuses led_0_0's material (LED vs a non-LED part).
    led_two_primitives: led_0_0's mesh has two primitives that share one material.
    caps_share_material: btn_b_cap reuses btn_a_cap's material (non-LED sharing is allowed).
    """
    ids = [p['id'] for p in CONTRACT['parts'] if p['id'] != omit]
    if duplicate:
        ids.append(duplicate)
    nodes, meshes, accessors, materials = [], [], [], []
    material_of = {}
    for part in ids:
        materials.append({'name': part if part.startswith('led_') else 'other_'+part})
        material_of[part] = len(materials)-1
    if shared_led_material:
        material_of['led_1_0'] = material_of['led_0_0']
    if led_shares_with:
        material_of[led_shares_with] = material_of['led_0_0']
    if caps_share_material:
        material_of['btn_b_cap'] = material_of['btn_a_cap']
    for part in ids:
        accessors.append({'componentType': 5126, 'count': 8, 'type': 'VEC3',
                          'min': [-width/2, -0.001, -0.021] if part == 'pcb' else [-0.001]*3,
                          'max': [width/2, 0.001, 0.021] if part == 'pcb' else [0.001]*3})
        primitive = {'attributes': {'POSITION': len(accessors)-1}, 'material': material_of[part]}
        primitives = [primitive, dict(primitive)] if led_two_primitives and part == 'led_0_0' else [primitive]
        meshes.append({'name': part, 'primitives': primitives})
        nodes.append({'name': part+'__node', 'mesh': len(meshes)-1, 'extras': {'part_id': part}})
    gltf = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [len(nodes)]}],
            'nodes': nodes, 'meshes': meshes, 'accessors': accessors, 'materials': materials}
    nodes.append({'name': 'wrapper', 'children': list(range(len(nodes))), 'scale': [parent_scale]*3})
    return gltf


def write_glb(path, gltf):
    body = json.dumps(gltf).encode()
    body += b' '*(-len(body) % 4)
    binary = b'\0'*4
    data = struct.pack('<III', 0x46546C67, 2, 12+8+len(body)+8+len(binary))
    data += struct.pack('<II', len(body), 0x4E4F534A)+body+struct.pack('<II', len(binary), 0x004E4942)+binary
    Path(path).write_bytes(data)


class MicrobitContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checker = load('check_contract', EXPERIMENT / 'check_contract.py')

    def problems(self, gltf, scale=SCALE):
        return self.checker.check_contract(gltf, CONTRACT, scale)

    def test_conformant_glb_passes(self):
        self.assertEqual(self.problems(synthetic()), [])

    def test_missing_led_is_named(self):
        problems = self.problems(synthetic(omit='led_3_4'))
        self.assertTrue(any('led_3_4' in p for p in problems), problems)

    def test_duplicate_part_id_is_reported(self):
        problems = self.problems(synthetic(duplicate='btn_a'))
        self.assertTrue(any('btn_a' in p and 'duplicate' in p.lower() for p in problems), problems)

    def test_shared_led_material_is_reported(self):
        gltf = synthetic(shared_led_material=True)
        # The helper isolates LED-vs-LED sharing: no non-LED part uses that material.
        shared = gltf['meshes'][[n['extras']['part_id'] for n in gltf['nodes'][:-1]].index('led_0_0')]['primitives'][0]['material']
        users = [n['extras']['part_id'] for n in gltf['nodes'][:-1]
                 if gltf['meshes'][n['mesh']]['primitives'][0]['material'] == shared]
        self.assertEqual(users, ['led_0_0', 'led_1_0'])
        problems = self.problems(gltf)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn('distinct material', problems[0])
        self.assertIn('led_0_0', problems[0])
        self.assertIn('led_1_0', problems[0])

    def test_led_sharing_material_with_a_non_led_part_is_reported(self):
        for other in ('btn_a', 'pcb', 'logo_touch'):
            problems = self.problems(synthetic(led_shares_with=other))
            self.assertEqual(len(problems), 1, (other, problems))
            self.assertIn('led_0_0', problems[0])
            self.assertIn(other, problems[0])
            self.assertIn('shares material', problems[0])

    def test_led_mesh_with_two_primitives_is_reported(self):
        problems = self.problems(synthetic(led_two_primitives=True))
        self.assertTrue(any('led_0_0' in p and 'exactly one primitive' in p for p in problems), problems)

    def test_non_led_parts_may_share_a_material(self):
        self.assertEqual(self.problems(synthetic(caps_share_material=True)), [])

    def test_box_twenty_percent_too_large(self):
        problems = self.problems(synthetic(width=0.052*1.2))
        self.assertTrue(any('longest dimension' in p for p in problems), problems)

    def test_box_within_tolerance_passes(self):
        self.assertEqual(self.problems(synthetic(width=0.0516)), [])

    def test_node_transforms_are_applied(self):
        # A parent scale of 1.2 enlarges the board even though accessor bounds are in tolerance.
        problems = self.problems(synthetic(parent_scale=1.2))
        self.assertTrue(any('longest dimension' in p for p in problems), problems)

    def test_roundtrip_through_glb_file_and_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = Path(tmp, 'good.glb'), Path(tmp, 'bad.glb')
            write_glb(good, synthetic())
            write_glb(bad, synthetic(omit='led_3_4'))
            self.assertEqual(self.checker.read_glb_json(good)['asset']['version'], '2.0')
            script = str(EXPERIMENT / 'check_contract.py')
            ok = subprocess.run([sys.executable, script, str(good)], capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stdout+ok.stderr)
            failed = subprocess.run([sys.executable, script, str(bad)], capture_output=True, text=True)
            self.assertEqual(failed.returncode, 1)
            self.assertIn('led_3_4', failed.stdout+failed.stderr)

    def test_brief_is_valid_and_matches_contract(self):
        iterate = load('iterate', LAB / 'iterate.py')
        brief = json.loads((EXPERIMENT / 'brief.json').read_text(encoding='utf-8'))
        iterate.validate_brief(brief)
        self.assertEqual([p['id'] for p in brief['parts']], [p['id'] for p in CONTRACT['parts']])
        self.assertEqual(brief['displayScale'], {'units': 'm', 'longestDimension': 0.052, 'tolerance': 0.02})
        self.assertEqual(brief['budgets'], {'triangles': 30000, 'materials': 45, 'meshObjects': 150, 'glbBytes': 3145728})
        self.assertIn('https://tech.microbit.org/hardware/', brief['provenance']['origin'])


if __name__ == '__main__':
    unittest.main()
