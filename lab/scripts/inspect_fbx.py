"""Inspect generated FBX/GLB with Blender; structural checks do not imply visual approval."""
import argparse
import json
import math
import os
import sys
from pathlib import Path
import bpy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--require-weights', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if args.input.suffix.lower() == '.fbx':
        bpy.ops.import_scene.fbx(filepath=str(args.input.resolve()))
    elif args.input.suffix.lower() == '.glb':
        bpy.ops.import_scene.gltf(filepath=str(args.input.resolve()))
    else:
        parser.error('Expected FBX or GLB')
    meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    armatures = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
    bone_names = {bone.name for obj in armatures for bone in obj.data.bones}
    failures = []
    if not meshes or not bone_names:
        failures.append('Expected a mesh and armature with bones')
    for obj in armatures:
        for bone in obj.data.bones:
            if not all(math.isfinite(value) for row in bone.matrix_local for value in row):
                failures.append('Non-finite bone matrix')
    vertices = sum(len(obj.data.vertices) for obj in meshes)
    weighted = 0
    unweighted = 0
    bad_sums = 0
    for obj in meshes:
        if not all(math.isfinite(value) for vertex in obj.data.vertices for value in vertex.co):
            failures.append('Non-finite vertex coordinates')
        if obj.find_armature() is None:
            continue
        group_map = {group.index: group.name for group in obj.vertex_groups}
        for vertex in obj.data.vertices:
            weights = [group.weight for group in vertex.groups if group_map.get(group.group) in bone_names]
            if any(not math.isfinite(weight) or weight < 0 for weight in weights):
                failures.append('Invalid vertex weight')
            total = sum(weights)
            if total <= 0:
                unweighted += 1
            else:
                weighted += 1
                if abs(total - 1) > 0.01:
                    bad_sums += 1
    if args.require_weights and (not weighted or unweighted or bad_sums):
        failures.append('Missing or non-normalized deformation weights')
    report = {'schemaVersion': 1, 'status': 'passed' if not failures else 'failed',
              'meshes': len(meshes), 'vertices': vertices, 'armatures': len(armatures),
              'bones': len(bone_names), 'weightedVertices': weighted,
              'unweightedDeformableVertices': unweighted, 'nonNormalizedVertices': bad_sums,
              'actions': len(bpy.data.actions), 'failures': sorted(set(failures)),
              'visualReview': 'pending'}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return 1 if failures else 0


if __name__ == '__main__':
    code = main()
    # bpy 4.2.0 may SIGSEGV in Python finalization after a successful GLB import.
    # This read-only worker has already closed its JSON report and Blender data.
    # Flush logs and exit with the actual validation status, without C++ teardown.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
