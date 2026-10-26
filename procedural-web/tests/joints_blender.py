"""World joint positions of the exported armature at frame 1 of a few clips (three.js axes), for the convention test."""
import json
import sys

import bpy

blend = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.open_mainfile(filepath=blend)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'gg_model' in o)
out = {}
for clip in ('highFive(R)', 'walk', 'think'):
    arm.animation_data.action = bpy.data.actions['clip.' + clip]
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    out[clip] = {pb.name: [v.x, v.z, -v.y] for pb in arm.pose.bones for v in [arm.matrix_world @ pb.head]}
print('JOINTS' + json.dumps(out))
