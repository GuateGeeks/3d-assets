"""Opt-in real Blender check of the optional extra views (underside, top-down) on a tiny flat fixture."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('iterate', BASE / 'iterate.py')
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)

GENERATOR = '''import bpy


def material(name, color):
    item = bpy.data.materials.new(name)
    item.use_nodes = True
    item.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = color
    return item


def box(name, part, size, location, color):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material(name, color))
    obj['part_id'] = part


def build():
    box('board', 'board', (.052, .042, .002), (0, 0, 0), (.1, .5, .2, 1))
    box('chip', 'chip', (.008, .008, .002), (.01, .005, -.002), (.02, .02, .02, 1))
    return {'title': 'Flat fixture', 'design_notes': 'test', 'parts': {
        'board': {'label_position': [0, 0, .001]}, 'chip': {'label_position': [.01, .005, -.003]}}}
'''


@unittest.skipUnless(os.environ.get('CREATION_TEST_BLENDER'), 'Set CREATION_TEST_BLENDER to opt into real Blender')
class ExtraViewsBlender(unittest.TestCase):
    def test_both_extra_views_render_and_are_hashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief = {'schemaVersion': 1, 'id': 'flat-fixture', 'purpose': 'Extra view fixture',
                     'parts': [{'id': 'board', 'label': 'Board'}, {'id': 'chip', 'label': 'Chip'}], 'seed': 1,
                     'displayScale': {'units': 'm', 'longestDimension': .052, 'tolerance': .02},
                     'budgets': {'triangles': 1000, 'materials': 4, 'meshObjects': 4, 'glbBytes': 100000},
                     'provenance': {'author': 'test', 'origin': 'test fixture', 'license': 'CC0-1.0'},
                     'contentChecks': ['Both parts exist.']}
            flow.write(root / 'brief.json', brief)
            (root / 'generator.py').write_text(GENERATOR)
            author = {'actorId': 'author-1', 'model': flow.SOL, 'reasoningEffort': 'medium'}
            session = flow.init_session(root / 'brief.json', root / 'session', 'mixed', author)
            args = flow.parser().parse_args([
                'run', '--session', str(session), '--generator', str(root / 'generator.py'), '--stage', 'blockout',
                '--blender', os.environ['CREATION_TEST_BLENDER'], '--actor-id', 'author-1', '--model', flow.SOL,
                '--extra-view', 'underside', '--extra-view', 'top-down'])
            result = flow.run_generator(args)
            run = Path(result['run'])
            manifest = flow.read(run / 'manifest.json')
            self.assertEqual(manifest['technical'], 'PASS', manifest.get('error'))
            self.assertEqual(manifest['extraViews'], ['underside', 'top-down'])
            names = (*flow.VIEWS, 'underside', 'top-down')
            for name in names:
                image = run / 'renders' / (name + '.png')
                self.assertGreater(image.stat().st_size, 1000, name)
                self.assertEqual(manifest['artifacts']['renders/' + name + '.png'], flow.digest(image))
            self.assertEqual(len({manifest['artifacts']['renders/' + n + '.png'] for n in names}), len(names))
            flow.load_run(session, manifest['runId'])
            self.assertEqual(list(flow.review_template(session, manifest['runId'])['images']), list(names))
            self.assertEqual(json.loads((run / 'reopen-result.json').read_text())['extraViews'], ['underside', 'top-down'])


if __name__ == '__main__':
    unittest.main()
