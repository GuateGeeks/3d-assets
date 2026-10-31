"""Node-contract checker for the micro:bit GLB, on synthetic minimal GLBs (no Blender)."""
import copy
import importlib.util
import json
import math
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
              led_shares_with=None, led_two_primitives=False, caps_share_material=False,
              logo_two_primitives=False, led_unlit=None, extensions_used=None):
    """Minimal glTF dict: one box node per contract part, each on its own material; the PCB sets the extent.

    shared_led_material: led_1_0 reuses led_0_0's material (LED vs LED only).
    led_shares_with: that part reuses led_0_0's material (LED vs a non-LED part).
    led_two_primitives: led_0_0's mesh has two primitives that share one material.
    caps_share_material: btn_b_cap reuses btn_a_cap's material (non-LED sharing is allowed).
    logo_two_primitives: logo_touch's mesh has two primitives that share one material.
    led_unlit: that LED's material carries KHR_materials_unlit.
    extensions_used: written to the glTF's extensionsUsed.
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
        two = (led_two_primitives and part == 'led_0_0') or (logo_two_primitives and part == 'logo_touch')
        primitives = [primitive, dict(primitive)] if two else [primitive]
        meshes.append({'name': part, 'primitives': primitives})
        nodes.append({'name': part+'__node', 'mesh': len(meshes)-1, 'extras': {'part_id': part}})
    gltf = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [len(nodes)]}],
            'nodes': nodes, 'meshes': meshes, 'accessors': accessors, 'materials': materials}
    nodes.append({'name': 'wrapper', 'children': list(range(len(nodes))), 'scale': [parent_scale]*3})
    if led_unlit:
        materials[material_of[led_unlit]]['extensions'] = {'KHR_materials_unlit': {}}
    if extensions_used:
        gltf['extensionsUsed'] = list(extensions_used)
    return gltf


def node_of(gltf, part):
    return next(n for n in gltf['nodes'] if (n.get('extras') or {}).get('part_id') == part)


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

    def test_logo_touch_mesh_with_two_primitives_is_reported(self):
        problems = self.problems(synthetic(logo_two_primitives=True))
        self.assertEqual(len(problems), 1, problems)
        self.assertIn('logo_touch must be a mesh with exactly one primitive (found 2)', problems[0])

    def test_unlit_led_material_is_reported(self):
        for extensions_used in (None, ['KHR_materials_unlit']):
            with self.subTest(extensions_used=extensions_used):
                problems = self.problems(synthetic(led_unlit='led_2_3', extensions_used=extensions_used))
                self.assertEqual(len(problems), 1, problems)
                self.assertIn('led_2_3', problems[0])
                self.assertIn('KHR_materials_unlit', problems[0])
                self.assertIn('emissive', problems[0])

    def test_unlit_extension_listed_but_unused_by_leds_passes(self):
        self.assertEqual(self.problems(synthetic(extensions_used=['KHR_materials_unlit'])), [])

    def test_non_led_parts_may_share_a_material(self):
        self.assertEqual(self.problems(synthetic(caps_share_material=True)), [])

    def test_unrotated_unscaled_translated_caps_pass(self):
        gltf = synthetic()
        for part in ('btn_a_cap', 'btn_b_cap'):
            node = node_of(gltf, part)
            node.update(translation=[0.02, 0.006, 0.0], rotation=[0, 0, 0, 1], scale=[1, 1, 1])
        self.assertEqual(self.problems(gltf), [])

    def test_rotated_or_scaled_cap_is_reported(self):
        quarter = [0, 0, math.sin(math.pi/4), math.cos(math.pi/4)]
        for change in ({'rotation': quarter}, {'scale': [1, 1.5, 1]},
                       {'matrix': [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 0.02, 0, 0, 1]}):
            for part in ('btn_a_cap', 'btn_b_cap'):
                with self.subTest(change=change, part=part):
                    gltf = synthetic()
                    node_of(gltf, part).update(change)
                    problems = self.problems(gltf)
                    self.assertEqual(len(problems), 1, problems)
                    self.assertIn(part, problems[0])
                    self.assertIn('rotation', problems[0])
                    self.assertIn('scale', problems[0])

    def test_cap_under_rotated_or_scaled_parent_is_reported(self):
        for change in ({'rotation': [0.7071068, 0, 0, 0.7071068]}, {'scale': [2, 2, 2]}):
            with self.subTest(change=change):
                gltf = synthetic()
                cap = gltf['nodes'].index(node_of(gltf, 'btn_a_cap'))
                wrapper = gltf['nodes'][-1]
                wrapper['children'].remove(cap)
                gltf['nodes'].append({'name': 'tilted holder', 'children': [cap], **change})
                wrapper['children'].append(len(gltf['nodes'])-1)
                problems = [p for p in self.problems(gltf) if 'longest dimension' not in p]
                self.assertEqual(len(problems), 1, problems)
                self.assertIn('btn_a_cap', problems[0])
                self.assertIn('tilted holder', problems[0])

    def test_other_parts_may_be_rotated(self):
        gltf = synthetic()
        node_of(gltf, 'btn_a')['rotation'] = [0, 0, math.sin(math.pi/8), math.cos(math.pi/8)]
        node_of(gltf, 'speaker')['rotation'] = [0, math.sin(math.pi/8), 0, math.cos(math.pi/8)]
        self.assertEqual(self.problems(gltf), [])

    def test_part_on_a_node_without_mesh_is_reported(self):
        for part in ('pcb', 'logo_touch', 'led_2_2', 'btn_b_cap'):
            with self.subTest(part=part):
                gltf = synthetic()
                node = node_of(gltf, part)
                child = dict(node, extras={})
                del node['mesh']
                gltf['nodes'].append(child)
                node['children'] = [len(gltf['nodes'])-1]
                problems = [p for p in self.problems(gltf) if 'longest dimension' not in p and 'measurable' not in p]
                self.assertEqual(len(problems), 1, problems)
                self.assertIn(part, problems[0])
                self.assertIn('without a mesh', problems[0])

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

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(EXPERIMENT / 'check_contract.py'), *map(str, args)], capture_output=True, text=True)

    def assert_one_line_fail(self, result):
        self.assertEqual(result.returncode, 1, result.stdout+result.stderr)
        self.assertNotIn('Traceback', result.stdout+result.stderr)
        lines = (result.stdout+result.stderr).strip().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].startswith('FAIL '), lines)

    def test_unreadable_input_prints_one_fail_line_without_a_traceback(self):
        good = write_glb  # alias for readability below
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp/'empty.glb').write_bytes(b'')
            (tmp/'text.glb').write_bytes(b'this is definitely not a binary glTF, just text padding it out')
            full = tmp/'full.glb'
            good(full, synthetic())
            (tmp/'truncated.glb').write_bytes(full.read_bytes()[:200])
            (tmp/'cut_header.glb').write_bytes(full.read_bytes()[:10])
            body = b'{not json}'
            body += b' '*(-len(body) % 4)
            (tmp/'badjson.glb').write_bytes(struct.pack('<III', 0x46546C67, 2, 20+len(body))+struct.pack('<II', len(body), 0x4E4F534A)+body)
            nokey = synthetic()
            nokey['meshes'][0]['primitives'][0]['attributes'] = {}
            good(tmp/'nokey.glb', nokey)
            for name in ('empty.glb', 'text.glb', 'truncated.glb', 'cut_header.glb', 'badjson.glb', 'nokey.glb', 'missing.glb'):
                with self.subTest(name=name):
                    self.assert_one_line_fail(self.run_cli(tmp/name))
            self.assertIn('Not a glTF 2.0 binary', self.run_cli(tmp/'text.glb').stdout)
            self.assertIn('missing.glb', self.run_cli(tmp/'missing.glb').stdout)

    def test_missing_contract_or_brief_file_prints_one_fail_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            glb = Path(tmp, 'good.glb')
            write_glb(glb, synthetic())
            self.assert_one_line_fail(self.run_cli(glb, '--contract', Path(tmp, 'nope.json')))
            self.assert_one_line_fail(self.run_cli(glb, '--brief', Path(tmp, 'nope.json')))

    def test_real_glb_still_passes(self):
        result = self.run_cli(ROOT / 'studio/examples/microbit/microbit.glb')
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertTrue(result.stdout.startswith('PASS'))

    def test_contract_led_grid_is_five_by_five(self):
        # ledGrid.columns/rows are not read by the code (the 5x5 size is hard-coded in microbit.ts, runtime.ts, core.py and the schema); pin them so the contract cannot drift.
        grid = CONTRACT['ledGrid']
        self.assertEqual((grid['columns'], grid['rows']), (5, 5))
        leds = [p['id'] for p in CONTRACT['parts'] if p['id'].startswith('led_')]
        self.assertEqual(len(leds), grid['columns']*grid['rows'])

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
