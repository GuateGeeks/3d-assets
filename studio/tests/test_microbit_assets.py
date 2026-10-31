import json
import unittest
from pathlib import Path
from studio import core

ROOT=Path(__file__).resolve().parents[2]
EXAMPLES=ROOT/'studio/examples/microbit'
PUBLIC=ROOT/'studio/web/public/microbit'


class MicrobitAssetCopyTests(unittest.TestCase):
    def test_glb_copies_are_byte_identical_and_match_the_recorded_hash(self):
        a,b=(EXAMPLES/'microbit.glb').read_bytes(),(PUBLIC/'microbit.glb').read_bytes()
        self.assertEqual(a,b)
        provenance=(EXAMPLES/'PROVENANCE.md').read_text(encoding='utf-8')
        self.assertIn(core.sha256(EXAMPLES/'microbit.glb'),provenance)
        self.assertRegex(provenance,r'\b[0-9a-f]{64}\b')

    def test_scene_copies_are_byte_identical_and_valid(self):
        a,b=(EXAMPLES/'microbit.scene.json').read_bytes(),(PUBLIC/'microbit.scene.json').read_bytes()
        self.assertEqual(a,b)
        scene=core.validate_record(json.loads(a))
        self.assertEqual(scene['kind'],'scene')
        board=scene['instances'][0]
        self.assertEqual((board['id'],board['asset'],board['behavior']),('Board','microbit.glb','microbit'))
        self.assertEqual(board['scale'],[1,1,1])
        # The asset path is relative to the scene file and really exists next to it, in both places.
        for folder in (EXAMPLES,PUBLIC): core.validate_glb(core.checked_path(folder,board['asset']))

    def test_patterns_are_distinct_and_tracks_cover_all_leds(self):
        scene=json.loads((EXAMPLES/'microbit.scene.json').read_text(encoding='utf-8'))
        patterns={p['source']:p['pressed'] for p in scene['patternBindings']}
        self.assertEqual(set(patterns),{'a','b','logo'})
        self.assertEqual(len({json.dumps(g) for g in patterns.values()}),3)
        for grid in patterns.values():
            self.assertTrue(any(v>0 for row in grid for v in row))
        self.assertEqual({t['channel'] for t in scene['tracks']},{f'led.{x}.{y}' for x in range(5) for y in range(5)})


if __name__=='__main__':
    unittest.main()
