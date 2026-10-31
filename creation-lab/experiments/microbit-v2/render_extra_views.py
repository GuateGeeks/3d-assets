"""Supplementary renders of a finished run: back face, top-down, back three-quarter.

NOT part of the common six-view renderer (scripts/iteration_worker.py is not
changed). Run it with Blender on the same adapter, against an existing run:

    blender --background --factory-startup --python render_extra_views.py -- RUN_DIR SUPPLEMENTARY_ROOT

It opens RUN_DIR/source.blend read-only (never saved), keeps the lights, world and
camera that worker stored there, re-applies the worker's renderer settings
(Cycles CPU, two threads, 24 samples, 768 px, AgX, opaque world) and writes the
images plus supplementary.json into the NEW folder SUPPLEMENTARY_ROOT/<run name>/.
Nothing inside RUN_DIR is touched. SUPPLEMENTARY_ROOT must already exist (the WSL
adapter only converts existing paths); the run folder is refused if it exists.

Conventions as in the brief: Blender Z up, LED face +Z, edge connector toward -Y.
Under-board cameras look up; the 'back-face' frame keeps the edge connector at the
bottom of the image (so the board appears mirrored left-right versus the LED face).
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

# (camera position in units of the presentation factor, rotation_euler or None to track the origin)
VIEWS = {
    'back-face': ((0, 0, -.7), (0, math.pi, 0)),            # below, looking up (+Z), edge connector at the bottom
    'top-down': ((0, 0, .7), (0, 0, 0)),                    # above, looking down (-Z), edge connector at the bottom
    'back-three-quarter': ((.45, -.60, -.55), None),        # below, from the edge-connector side
    'back-three-quarter-rear': ((-.45, .60, -.55), None),   # below, from the USB / battery side
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    args = sys.argv[sys.argv.index('--')+1:]
    run, root = Path(args[0]).resolve(), Path(args[1]).resolve()
    out = root/run.name
    if not (run/'source.blend').is_file() or not root.is_dir():
        raise SystemExit('RUN_DIR/source.blend and an existing SUPPLEMENTARY_ROOT are required')
    out.mkdir(exist_ok=False)
    bpy.ops.wm.open_mainfile(filepath=str(run/'source.blend'), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    factor = scene.get('presentation_scale', 1)
    cam = scene.camera
    if cam is None:
        raise SystemExit('source.blend has no presentation camera')
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.render.film_transparent = False
    images = {}
    for name, (position, rotation) in VIEWS.items():
        cam.location = Vector(position)*factor
        if rotation is None:
            cam.rotation_euler = (Vector((0, 0, 0))-cam.location).to_track_quat('-Z', 'Y').to_euler()
        else:
            cam.rotation_euler = rotation
        scene.render.filepath = str(out/(name+'.png'))
        bpy.ops.render.render(write_still=True)
        images[name+'.png'] = digest(out/(name+'.png'))
    manifest = {'kind': 'supplementary, not part of the common six-view renderer', 'run': run.name,
                'blender': bpy.app.version_string, 'script': 'creation-lab/experiments/microbit-v2/render_extra_views.py',
                'sourceBlendSha256': digest(run/'source.blend'), 'presentationScale': factor,
                'renderer': {'engine': 'CYCLES', 'device': 'CPU', 'threads': 2, 'samples': 24, 'resolution': 768,
                             'viewTransform': 'AgX'}, 'imagesSha256': images}
    (out/'supplementary.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
