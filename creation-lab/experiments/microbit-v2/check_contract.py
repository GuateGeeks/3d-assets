"""Check a micro:bit GLB against the Studio node contract. Stdlib only, no Blender.

    python3 check_contract.py GLB [--contract PATH] [--brief PATH]

Exits 1 and prints one problem per line when the GLB breaks the contract:
every contract ``part_id`` must appear exactly once in a node's ``extras``
(Blender custom property ``part_id`` exported with ``export_extras``), each of
the 25 LED nodes must be a single-primitive mesh on a material that no other node
(LED or not) uses, as the Studio factory requires, and the board's bounding box
must match the brief's ``displayScale`` on its longest dimension.

Bounding box: each mesh primitive's POSITION accessor min/max (the eight box
corners) is carried through the node's full world transform (matrix or
TRS, parents included). It is a box of boxes, so a rotated mesh is measured by
the rotated corner box, which can over-estimate a tilted part. Accessors without
min/max, and skinned or morphed meshes, are not supported and are reported.
"""
import argparse
import itertools
import json
import math
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CONTRACT = HERE.parents[2] / 'studio' / 'examples' / 'microbit' / 'node-contract.json'
DEFAULT_BRIEF = HERE / 'brief.json'
LED_PART = re.compile(r'^led_[0-4]_[0-4]$')
MAGIC, JSON_CHUNK = 0x46546C67, 0x4E4F534A


def read_glb_json(path):
    """Return the JSON chunk of a binary glTF as a dict."""
    data = Path(path).read_bytes()
    if len(data) < 20:
        raise ValueError('Not a GLB: file too short')
    magic, version, length = struct.unpack_from('<III', data, 0)
    if magic != MAGIC or version != 2:
        raise ValueError('Not a glTF 2.0 binary (GLB)')
    chunk_length, chunk_type = struct.unpack_from('<II', data, 12)
    if chunk_type != JSON_CHUNK or 20+chunk_length > len(data):
        raise ValueError('GLB first chunk is not a complete JSON chunk')
    return json.loads(data[20:20+chunk_length].decode('utf-8'))


def _multiply(a, b):
    """4x4 column-major matrices as flat lists: a @ b."""
    return [sum(a[k*4+row]*b[col*4+k] for k in range(4)) for col in range(4) for row in range(4)]


def _local_matrix(node):
    if 'matrix' in node:
        return [float(x) for x in node['matrix']]
    tx, ty, tz = node.get('translation', (0, 0, 0))
    x, y, z, w = node.get('rotation', (0, 0, 0, 1))
    sx, sy, sz = node.get('scale', (1, 1, 1))
    return [(1-2*(y*y+z*z))*sx, 2*(x*y+z*w)*sx, 2*(x*z-y*w)*sx, 0,
            2*(x*y-z*w)*sy, (1-2*(x*x+z*z))*sy, 2*(y*z+x*w)*sy, 0,
            2*(x*z+y*w)*sz, 2*(y*z-x*w)*sz, (1-2*(x*x+y*y))*sz, 0,
            tx, ty, tz, 1]


def _apply(m, p):
    return tuple(m[0+i]*p[0]+m[4+i]*p[1]+m[8+i]*p[2]+m[12+i] for i in range(3))


def _world_matrices(gltf):
    nodes = gltf.get('nodes', [])
    world = {}
    stack = [(i, [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
             for scene in ([gltf['scenes'][gltf.get('scene', 0)]] if gltf.get('scenes') else [])
             for i in scene.get('nodes', [])]
    while stack:
        index, parent = stack.pop()
        if index in world:
            continue
        world[index] = _multiply(parent, _local_matrix(nodes[index]))
        stack.extend((child, world[index]) for child in nodes[index].get('children', []))
    return world


def bounding_box(gltf, problems=None):
    """(min, max) over all mesh primitives in world space, or None when nothing is measurable."""
    problems = problems if problems is not None else []
    lows, highs = [math.inf]*3, [-math.inf]*3
    accessors, meshes = gltf.get('accessors', []), gltf.get('meshes', [])
    for index, matrix in _world_matrices(gltf).items():
        node = gltf['nodes'][index]
        if 'mesh' not in node:
            continue
        for primitive in meshes[node['mesh']].get('primitives', []):
            accessor = accessors[primitive['attributes']['POSITION']]
            if 'min' not in accessor or 'max' not in accessor:
                problems.append(f"node {node.get('name', index)} has a POSITION accessor without min/max")
                continue
            for corner in itertools.product(*zip(accessor['min'], accessor['max'])):
                point = _apply(matrix, corner)
                lows = [min(a, b) for a, b in zip(lows, point)]
                highs = [max(a, b) for a, b in zip(highs, point)]
    return None if lows[0] == math.inf else (lows, highs)


def check_contract(gltf, contract, display_scale=None):
    """List the problems between a glTF dict and the node contract (empty means pass).

    display_scale is the brief's ``displayScale`` (``longestDimension``,
    ``tolerance`` relative); without it the size check is skipped.
    """
    problems = []
    nodes = gltf.get('nodes', [])
    by_part = {}
    for index, node in enumerate(nodes):
        part = (node.get('extras') or {}).get('part_id')
        if isinstance(part, str):
            by_part.setdefault(part, []).append(index)
    for part in contract['parts']:
        found = by_part.get(part['id'], [])
        if not found:
            problems.append(f"missing part_id {part['id']}")
        elif len(found) > 1:
            names = ', '.join(str(nodes[i].get('name', i)) for i in found)
            problems.append(f"duplicate part_id {part['id']} on {len(found)} nodes ({names})")

    # Material ownership over every mesh node, as the Studio factory enforces it: an LED needs
    # exactly one primitive and a material that no other node (LED or not) uses.
    meshes = gltf.get('meshes', [])
    owners = {}
    for index, node in enumerate(nodes):
        if 'mesh' not in node:
            continue
        part = (node.get('extras') or {}).get('part_id')
        name = part if isinstance(part, str) else f"node {node.get('name', index)}"
        primitives = meshes[node['mesh']].get('primitives', [])
        if isinstance(part, str) and LED_PART.match(part) and len(primitives) != 1:
            problems.append(f'{part} must be a mesh with exactly one primitive (found {len(primitives)})')
        for material in sorted({p.get('material') for p in primitives if p.get('material') is not None}):
            owners.setdefault(material, []).append(name)
        if isinstance(part, str) and LED_PART.match(part) and not any(p.get('material') is not None for p in primitives):
            problems.append(f'{part} has no material')
    for material, names in sorted(owners.items()):
        leds = [n for n in names if LED_PART.match(n)]
        others = [n for n in names if not LED_PART.match(n)]
        if len(leds) > 1:
            problems.append(f"LEDs need a distinct material each; material {material} is shared by {', '.join(leds)}")
        if leds and others:
            for led in leds:
                problems.append(f"{led} shares material {material} with {', '.join(others)}; each LED needs its own")

    if display_scale is not None:
        box = bounding_box(gltf, problems)
        target, tolerance = display_scale['longestDimension'], display_scale['tolerance']
        if box is None:
            problems.append('no measurable mesh geometry for the size check')
        else:
            dims = [high-low for low, high in zip(*box)]
            if abs(max(dims)-target) > target*tolerance:
                problems.append(f'longest dimension {max(dims):.5f} m is outside {target} m +/- {tolerance:.0%} '
                                f'(box {dims[0]:.5f} x {dims[1]:.5f} x {dims[2]:.5f} m)')
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('glb', type=Path)
    parser.add_argument('--contract', type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument('--brief', type=Path, default=DEFAULT_BRIEF)
    args = parser.parse_args(argv)
    contract = json.loads(args.contract.read_text(encoding='utf-8'))
    scale = json.loads(args.brief.read_text(encoding='utf-8'))['displayScale']
    problems = check_contract(read_glb_json(args.glb), contract, scale)
    for problem in problems:
        print('FAIL', problem)
    if problems:
        return 1
    print(f"PASS node contract: {len(contract['parts'])} parts, 25 distinct LED materials, size within displayScale")
    return 0


if __name__ == '__main__':
    sys.exit(main())
