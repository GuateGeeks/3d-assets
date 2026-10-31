"""micro:bit V2 detail: the approved blockout refined into recognisable components.

Blender conventions: metres, Z up, front -Y. The board lies flat with the LED
face toward +Z and the edge connector toward -Y; the origin is the board centre
on the PCB mid-plane (glTF export turns +Z into +Y and -Y into +Z). Outline from
https://tech.microbit.org/hardware/2-2-revision/ (51.60 x 42.00 mm, 11.65 mm
deep: button 4.55 mm above the board, JST socket 5.50 mm and speaker 3.00 mm
below it). PCB thickness 1.6 mm is assumed; every component position and size
is estimated from reference photos (proportion only, never textures). No BBC /
micro:bit logos, FCC ID, text or silkscreen graphics.

Node contract (Studio): each contract part_id is exactly one object; pieces of a
part are joined into it. Each LED is one single-material mesh with its own
material ``led_x_y``; ``logo_touch`` is single-material too. The caps
``btn_a_cap``/``btn_b_cap`` are separate root objects with identity transforms.
All objects are root-level with identity transforms (geometry in world space).
Unlabelled board parts (interface chip, crystal, regulators, passives, status
LEDs, USB pads, microphone port) belong to ``pcb``. LED x = column, y = row,
origin top-left seen from the LED face with the edge connector at the bottom.
"""
import math
import random

import bpy

from components import MeshData, circle_outline, cylinder, extruded_outline, material, mesh_object
from components import refined_plate, rounded_box, rounded_rect_outline, sphere, validate_mesh

MM = 0.001
WIDTH, HEIGHT, THICK = 51.6*MM, 42.0*MM, 1.6*MM
TOP, BOTTOM = THICK/2, -THICK/2                     # PCB face planes (z)
HX, HY = WIDTH/2, HEIGHT/2
R_TOP, R_BOTTOM = 3.2*MM, 1.0*MM                    # board corner radii (photo estimate)
PIN_X = (-21.8*MM, -11.45*MM, 0.0, 11.45*MM, 21.8*MM)
PIN_Y = -14.1*MM
PIN_HOLE, BARREL, PCB_HOLE, PAD_R = 2.1*MM, 2.18*MM, 2.2*MM, 2.6*MM   # plated hole, barrel wall, drilled hole, pad
MOUNT_X, MOUNT_R = 24.5*MM, 0.6*MM                  # the two small mounting holes at y = 0
PLATING = 0.05*MM                                   # copper + gold thickness of pads and fingers
FINGER_TOP, FINGER_BOTTOM = -15.9*MM, -20.95*MM
LED_PITCH, LED_CENTER_Y = 4.0*MM, -1.0*MM
BTN_X, BTN_Y = 20.3*MM, -0.6*MM
BUTTON_TOP = 4.55*MM                                # official: button 4.55 mm above the board


# --- geometry helpers (pure; MeshData in, MeshData out) ---------------------

def combine(*meshes):
    """Concatenate closed meshes into one MeshData (each piece stays a separate closed shell)."""
    vertices, faces = [], []
    for mesh in meshes:
        offset = len(vertices)
        vertices.extend(mesh.vertices)
        faces.extend(tuple(i+offset for i in face) for face in mesh.faces)
    return MeshData(tuple(vertices), tuple(faces))


def turned(mesh, degrees, center=(0.0, 0.0)):
    """Rotate about Z through the origin (mesh built around it), then move by center (x, y)."""
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return MeshData(tuple((center[0]+c*x-s*y, center[1]+s*x+c*y, z) for x, y, z in mesh.vertices), mesh.faces)


def on_face(mesh, side):
    """Mesh built with z = height above a PCB face: side +1 puts it on the LED face, -1 on the back (mirrored in z)."""
    if side > 0:
        return MeshData(tuple((x, y, TOP+z) for x, y, z in mesh.vertices), mesh.faces)
    return MeshData(tuple((x, y, BOTTOM-z) for x, y, z in mesh.vertices), tuple((a, c, b) for a, b, c in mesh.faces))


def box(size, center):
    return rounded_box(size, 0, center=center)


def prism_y(outline_xz, y0, y1, holes=()):
    """Closed prism of an (x, z) outline between y0 and y1 (a proper rotation keeps the outward winding)."""
    mesh = extruded_outline(outline_xz, holes, thickness=y1-y0)
    return MeshData(tuple((a, y1-t, b) for a, b, t in mesh.vertices), mesh.faces)


def cone(radius, height, center, segments=24):
    """Closed cone on the plane z = center[2], apex at +height."""
    cx, cy, cz = center
    ring = [(cx+radius*math.cos(math.tau*i/segments), cy+radius*math.sin(math.tau*i/segments), cz) for i in range(segments)]
    base, apex = segments, segments+1
    faces = []
    for i in range(segments):
        j = (i+1) % segments
        faces.append((base, j, i))
        faces.append((i, j, apex))
    return MeshData(tuple(ring+[(cx, cy, cz), (cx, cy, cz+height)]), tuple(faces))


def trace_outline(points, width):
    """Outline of a constant-width trace along a polyline (mitred corners, square ends)."""
    h, left, right = width/2, [], []
    for i, (px, py) in enumerate(points):
        normals = []
        for a, b in ((points[i-1] if i else None, (px, py)), ((px, py), points[i+1] if i+1 < len(points) else None)):
            if a is None or b is None:
                continue
            dx, dy = b[0]-a[0], b[1]-a[1]
            length = math.hypot(dx, dy)
            normals.append((-dy/length, dx/length))
        if len(normals) == 1:
            nx, ny = normals[0]
        else:
            (ax, ay), (bx, by) = normals
            dot = ax*bx+ay*by
            nx, ny = (ax+bx)/(1+dot), (ay+by)/(1+dot)
        left.append((px+h*nx, py+h*ny))
        right.append((px-h*nx, py-h*ny))
    return left+right[::-1]


def board_outline():
    """Counter-clockwise PCB outline: rounded top corners (3.2 mm) and small bottom corners (1 mm)."""
    points = []
    for cx, cy, r, start, steps in ((HX-R_BOTTOM, -HY+R_BOTTOM, R_BOTTOM, -90.0, 4), (HX-R_TOP, HY-R_TOP, R_TOP, 0.0, 8),
                                    (-HX+R_TOP, HY-R_TOP, R_TOP, 90.0, 8), (-HX+R_BOTTOM, -HY+R_BOTTOM, R_BOTTOM, 180.0, 4)):
        for k in range(steps+1):
            angle = math.radians(start+90.0*k/steps)
            points.append((cx+r*math.cos(angle), cy+r*math.sin(angle)))
    return points


def tombstone(px, radius=PAD_R, segments=16):
    """Pin pad: half circle above the hole centre joined to a strip down to the board edge (counter-clockwise)."""
    points = [(px+radius, FINGER_BOTTOM)]
    points += [(px+radius*math.cos(math.pi*k/segments), PIN_Y+radius*math.sin(math.pi*k/segments)) for k in range(segments+1)]
    points.append((px-radius, FINGER_BOTTOM))
    return points


def tactile_switch(cx, cy, width, depth, base_h, plunger_r, top_h, legs):
    """6 x 6 mm style tact switch built upward from z = 0: (black base, metal cover, legs, plunger)."""
    base = rounded_box((width, depth, base_h), 0.15*MM, center=(cx, cy, base_h/2), segments=1)
    corner = [(cx+sx*(width/2-0.75*MM), cy+sy*(depth/2-0.75*MM)) for sx in (-1, 1) for sy in (-1, 1)]
    cover = refined_plate(rounded_rect_outline(width, depth, 0.25*MM, segments=2, center=(cx, cy)),
                          [circle_outline(plunger_r+0.15*MM, 32, (cx, cy))]+[circle_outline(0.42*MM, 12, c) for c in corner],
                          thickness=0.25*MM, z0=base_h, spacing=1.0*MM)
    pieces = []
    if legs:
        for sx in (-1, 1):
            for sy in (-1, 1):
                x = cx+sx*2.0*MM
                pieces.append(box((0.7*MM, 0.9*MM, 0.2*MM), (x, cy+sy*(depth/2+0.45*MM), 0.1*MM)))
                pieces.append(box((0.7*MM, 0.2*MM, base_h), (x, cy+sy*(depth/2+0.1*MM), base_h/2)))
    stem_bottom = base_h-0.2*MM
    plunger = combine(cylinder(plunger_r, top_h-0.2*MM-stem_bottom, center=(cx, cy, (stem_bottom+top_h-0.2*MM)/2), segments=32),
                      cylinder(plunger_r-0.2*MM, 0.2*MM, center=(cx, cy, top_h-0.1*MM), segments=32))
    return base, cover, combine(*pieces) if pieces else None, plunger


def chip(size, height, pads_per_side, pad_pitch, degrees, center, pad_size=(0.22*MM, 0.4*MM, 0.12*MM)):
    """Square IC body with a comb of tin pads peeking out along each side; built from z = 0 upward."""
    body = rounded_box((size, size, height), 0.12*MM, center=(0, 0, height/2), segments=1)
    pads = []
    span = (pads_per_side-1)*pad_pitch
    for k in range(pads_per_side):
        t = -span/2+k*pad_pitch
        for angle in (0, 90, 180, 270):
            pad = box((pad_size[0], pad_size[1], pad_size[2]), (t, size/2+0.05*MM, pad_size[2]/2))
            pads.append(turned(pad, angle))
    return turned(body, degrees, center), turned(combine(*pads), degrees, center)


def build():
    rng = random.Random(20261031)   # private generator: passive placement does not depend on global random state

    mats = {}

    def mat(name, color, roughness=0.5, metallic=0.0):
        mats[name] = material(name, color, roughness=roughness, metallic=metallic)
        return mats[name]

    labels = {}

    def part(part_id, name, pieces, label):
        """One object per part: pieces is [(MeshData, material)], joined with one material slot each."""
        materials, vertices, faces, slots = [], [], [], []
        for mesh, material_ in pieces:
            if material_ not in materials:
                materials.append(material_)
            offset = len(vertices)
            vertices.extend(mesh.vertices)
            faces.extend(tuple(i+offset for i in face) for face in mesh.faces)
            slots.extend([materials.index(material_)]*len(mesh.faces))
        joined = MeshData(tuple(vertices), tuple(faces))
        if len(materials) == 1:
            obj = mesh_object(name, part_id, joined, materials[0], smooth=False)
        else:
            validate_mesh(joined)
            for m in materials:
                if not m.use_nodes or not any(n.type == 'BSDF_PRINCIPLED' for n in m.node_tree.nodes):
                    raise ValueError('A Principled material is required')
            data = bpy.data.meshes.new(name+'__mesh')
            data.from_pydata(joined.vertices, [], joined.faces)
            for m in materials:
                data.materials.append(m)
            for polygon, slot in zip(data.polygons, slots):
                polygon.material_index = slot
                polygon.use_smooth = False
            data.update()
            data.normals_split_custom_set([tuple(n.vector) for n in data.corner_normals])
            data.update()
            obj = bpy.data.objects.new(part_id+'__'+name, data)
            obj['part_id'] = part_id
            obj['component_library'] = 'creation-lab/components/v1'
            bpy.context.collection.objects.link(obj)
        labels[part_id] = {'label_position': [round(v, 6) for v in label]}
        return obj

    # Palette: the blockout's 16 non-LED materials (retuned toward the photos) + 2 new ones + 25 private LED materials.
    pcb_mat = mat('mat_pcb', (0.035, 0.040, 0.048), 0.6)
    edge_gold = mat('mat_edge_gold', (0.85, 0.56, 0.12), 0.35, 0.7)
    pin_gold = mat('mat_pin_gold', (0.90, 0.62, 0.16), 0.35, 0.7)
    logo_gold = mat('mat_logo_gold', (0.95, 0.66, 0.14), 0.35, 0.7)
    switch_metal = mat('mat_button_body', (0.60, 0.61, 0.64), 0.3, 0.85)
    cap_a = mat('mat_btn_a_cap', (0.020, 0.020, 0.022), 0.45)
    cap_b = mat('mat_btn_b_cap', (0.021, 0.020, 0.022), 0.45)
    amber = mat('mat_mic_led', (0.95, 0.30, 0.01), 0.3)
    steel = mat('mat_usb_steel', (0.62, 0.64, 0.68), 0.3, 0.8)
    reset_black = mat('mat_reset', (0.022, 0.022, 0.024), 0.45)
    ivory = mat('mat_battery_ivory', (0.80, 0.76, 0.62), 0.6)
    speaker_grey = mat('mat_speaker', (0.13, 0.13, 0.14), 0.85)
    mic_gold = mat('mat_mic', (0.80, 0.68, 0.22), 0.3, 0.8)
    ic_black = mat('mat_processor', (0.075, 0.075, 0.08), 0.55)
    accel_black = mat('mat_accel', (0.10, 0.10, 0.11), 0.55)
    antenna_gold = mat('mat_antenna', (0.80, 0.52, 0.10), 0.35, 0.7)
    black = mat('mat_black_plastic', (0.012, 0.012, 0.014), 0.6)
    passive = mat('mat_passive', (0.33, 0.27, 0.18), 0.6)

    # --- edge connector and pins (both faces) ---------------------------------------------
    pins = ('pin_0', 'pin_1', 'pin_2', 'pin_3v', 'pin_gnd')
    for part_id, px in zip(pins, PIN_X):
        hole = [circle_outline(PIN_HOLE, 32, (px, PIN_Y))]
        front = refined_plate(tombstone(px), hole, thickness=PLATING, z0=TOP, spacing=0.9*MM)
        back = refined_plate(tombstone(px), hole, thickness=PLATING, z0=BOTTOM-PLATING, spacing=0.9*MM)
        barrel = extruded_outline(circle_outline(BARREL, 32, (px, PIN_Y)), hole, thickness=THICK, z0=BOTTOM)
        part(part_id, 'pad', [(combine(front, back, barrel), pin_gold)], (px, PIN_Y+PAD_R, TOP+0.0015))

    fingers = []
    edges = [px+s*PAD_R for px in PIN_X for s in (-1, 1)]
    for left, right in zip(edges[1::2], edges[2::2]):
        usable, width, pitch = right-left-0.7*MM, 0.85*MM, 1.27*MM
        count = int((usable+pitch-width)/pitch+1e-9)
        start = (left+right)/2-(count-1)*pitch/2
        for k in range(count):
            x = start+k*pitch
            for z in (TOP+PLATING/2, BOTTOM-PLATING/2):
                fingers.append(box((width, FINGER_TOP-FINGER_BOTTOM, PLATING), (x, (FINGER_TOP+FINGER_BOTTOM)/2, z)))
    part('edge_connector', 'fingers', [(combine(*fingers), edge_gold)], (0.0, -0.0185, TOP+0.001))

    # --- front face (+Z): LEDs, A / B switches with caps, touch logo, microphone LED -------
    for y in range(5):
        for x in range(5):
            part_id = 'led_%d_%d' % (x, y)
            cx, cy = (x-2)*LED_PITCH, LED_CENTER_Y-(y-2)*LED_PITCH
            body = rounded_box((1.0*MM, 1.8*MM, 0.3*MM), 0.08*MM, center=(cx, cy, TOP+0.15*MM), segments=1)
            lens = sphere((0.36*MM, 0.68*MM, 0.16*MM), center=(cx, cy, TOP+0.3*MM), segments=12, rings=6)
            colour = (0.80, 0.72-0.002*(5*y+x), 0.58)   # warm-white package; distinct per LED so nothing merges them
            part(part_id, 'smd led', [(combine(body, lens), mat(part_id, colour, 0.35))], (cx, cy, TOP+0.0015))

    for letter, sign, cap_mat in (('a', -1, cap_a), ('b', 1, cap_b)):
        cx = sign*BTN_X
        base, cover, legs, plunger = tactile_switch(cx, BTN_Y, 6.0*MM, 6.0*MM, 2.9*MM, 1.7*MM, BUTTON_TOP, legs=True)
        part('btn_'+letter, 'tact switch', [(on_face(base, 1), black), (on_face(cover, 1), switch_metal),
                                            (on_face(legs, 1), switch_metal)], (cx, BTN_Y+0.003, TOP+0.0035))
        part('btn_%s_cap' % letter, 'plunger', [(on_face(plunger, 1), cap_mat)], (cx, BTN_Y, TOP+BUTTON_TOP+0.0015))

    # Touch logo: gold stadium ring with two eyes, 0.3 mm proud so the 0.2 mm Studio press stays visible.
    ring = refined_plate(rounded_rect_outline(8.9*MM, 5.1*MM, 2.55*MM, segments=10, center=(0, 12.9*MM)),
                         [rounded_rect_outline(6.9*MM, 3.1*MM, 1.55*MM, segments=10, center=(0, 12.9*MM))],
                         thickness=0.3*MM, z0=TOP, spacing=1.0*MM)
    eyes = [cylinder(0.6*MM, 0.3*MM, center=(x, 12.9*MM, TOP+0.15*MM), segments=20) for x in (-1.9*MM, 1.9*MM)]
    part('logo_touch', 'stadium ring', [(combine(ring, *eyes), logo_gold)], (0.0, 0.0129, TOP+0.0018))
    part('mic_led', 'round indicator', [(sphere((0.45*MM, 0.45*MM, 0.35*MM), center=(9.5*MM, 12.4*MM, TOP), segments=16, rings=8), amber)],
         (0.0095, 0.0124, TOP+0.0015))

    # --- back face (-Z); x, y are front-view coordinates (the back photo mirrored) ----------
    # USB micro-B receptacle: trapezoid steel shell open toward +Y, 1.25 mm past the board edge, tongue inside.
    outer = [(-3.85*MM, BOTTOM), (3.85*MM, BOTTOM), (3.85*MM, BOTTOM-1.7*MM), (3.05*MM, BOTTOM-2.6*MM),
             (-3.05*MM, BOTTOM-2.6*MM), (-3.85*MM, BOTTOM-1.7*MM)]
    inner = [(-3.6*MM, BOTTOM-0.25*MM), (3.6*MM, BOTTOM-0.25*MM), (3.6*MM, BOTTOM-1.6*MM), (2.9*MM, BOTTOM-2.35*MM),
             (-2.9*MM, BOTTOM-2.35*MM), (-3.6*MM, BOTTOM-1.6*MM)]
    shell = combine(prism_y(outer, 17.3*MM, 22.25*MM, [inner]), prism_y(outer, 16.65*MM, 17.3*MM))
    usb_steel = [shell]
    usb_steel += [box((0.5*MM, 1.4*MM, 0.25*MM), (s*4.1*MM, 18.0*MM, BOTTOM-0.125*MM)) for s in (-1, 1)]
    usb_steel += [box((0.3*MM, 0.7*MM, 0.1*MM), (-1.3*MM+0.65*MM*k, 16.3*MM, BOTTOM-0.05*MM)) for k in range(5)]
    usb_black = [box((3.7*MM, 4.2*MM, 0.5*MM), (0, 19.4*MM, BOTTOM-0.9*MM))]
    usb_black += [box((0.7*MM, 1.5*MM, 0.04*MM), (s*2.2*MM, 20.6*MM, BOTTOM-2.61*MM)) for s in (-1, 1)]
    part('usb', 'micro usb', [(combine(*usb_steel), steel), (combine(*usb_black), black)], (0.0, 0.0195, BOTTOM-0.0036))

    # Reset: 6.0 x 5.8 mm tact switch (photo about 6 mm), black plunger 3.8 mm across, 3.5 mm deep.
    base, cover, _, plunger = tactile_switch(-9.75*MM, 18.1*MM, 6.0*MM, 5.8*MM, 2.0*MM, 1.9*MM, 3.5*MM, legs=False)
    part('reset_btn', 'tact switch', [(on_face(base, -1), black), (on_face(cover, -1), steel), (on_face(plunger, -1), reset_black)],
         (-0.00975, 0.0181, BOTTOM-0.0045))

    # JST PH battery socket: ivory body, mouth toward the board edge (+Y) with two contacts, two slots on the far face.
    jx, x0, x1, y0, ym, y1 = -19.3*MM, -23.45*MM, -15.15*MM, 14.8*MM, 19.0*MM, 20.8*MM
    far, depth = BOTTOM-5.5*MM, BOTTOM-4.2*MM
    mouth = prism_y([(x0, BOTTOM), (x1, BOTTOM), (x1, far), (x0, far)], ym, y1,
                    [[(x0+0.7*MM, BOTTOM-0.9*MM), (x1-0.7*MM, BOTTOM-0.9*MM), (x1-0.7*MM, far+0.7*MM), (x0+0.7*MM, far+0.7*MM)]])
    slots = [rounded_rect_outline(0.9*MM, 2.6*MM, 0, center=(jx+s*1.0*MM, 16.9*MM)) for s in (-1, 1)]
    rear = refined_plate(rounded_rect_outline(x1-x0, ym-y0, 0, center=(jx, (y0+ym)/2)), slots, thickness=depth-far, z0=far, spacing=1.2*MM)
    core = box((x1-x0, ym-y0, BOTTOM-depth), (jx, (y0+ym)/2, (BOTTOM+depth)/2))
    contacts = [box((0.5*MM, 1.4*MM, 0.5*MM), (jx+s*1.0*MM, ym+0.7*MM, BOTTOM-2.85*MM)) for s in (-1, 1)]
    contacts += [box((0.6*MM, 1.4*MM, 0.3*MM), (jx+s*3.7*MM, 14.1*MM, BOTTOM-0.15*MM)) for s in (-1, 1)]
    contacts += [box((0.5*MM, 1.2*MM, 0.25*MM), (jx+s*1.0*MM, 14.2*MM, BOTTOM-0.125*MM)) for s in (-1, 1)]
    part('battery_socket', 'jst ph', [(combine(mouth, rear, core), ivory), (combine(*contacts), steel)], (jx, 0.0178, BOTTOM-0.0065))

    # Speaker: 8.5 mm square magnetic transducer turned 45 degrees, 3.0 mm deep; ring, cone and four solder tabs.
    sx, sy = 0.0, 0.8*MM
    body = turned(rounded_box((8.5*MM, 8.5*MM, 2.85*MM), 0.5*MM, center=(0, 0, 1.425*MM), segments=2), 45, (sx, sy))
    ring = refined_plate(circle_outline(3.2*MM, 40, (sx, sy)), [circle_outline(2.7*MM, 40, (sx, sy))],
                         thickness=0.15*MM, z0=2.85*MM, spacing=0.6*MM)
    diaphragm = cone(2.6*MM, 0.12*MM, (sx, sy, 2.85*MM), segments=40)
    port = cylinder(0.35*MM, 0.03*MM, center=(sx+2.7*MM, sy-2.7*MM, 2.86*MM), segments=16)   # sound port outside the ring
    tabs = combine(*[turned(box((1.5*MM, 1.5*MM, 0.15*MM), (5.5*MM, 0, 0.075*MM)), 90*k, (sx, sy)) for k in range(4)])
    part('speaker', 'transducer', [(on_face(body, -1), speaker_grey), (on_face(combine(ring, port), -1), black),
                                   (on_face(diaphragm, -1), ic_black), (on_face(tabs, -1), steel)], (sx, sy, BOTTOM-0.0045))

    # MEMS microphone: gold can on a dark substrate, port hole on the lid.
    mxy = (7.8*MM, 10.3*MM)
    substrate = box((3.5*MM, 3.0*MM, 0.25*MM), (mxy[0], mxy[1], 0.125*MM))
    lid = rounded_box((3.2*MM, 2.7*MM, 0.75*MM), 0.15*MM, center=(mxy[0], mxy[1], 0.625*MM), segments=1)
    hole = cylinder(0.3*MM, 0.04*MM, center=(mxy[0]-0.8*MM, mxy[1], 1.015*MM), segments=16)
    part('mic', 'mems can', [(on_face(lid, -1), mic_gold), (on_face(combine(substrate, hole), -1), black)],
         (mxy[0], mxy[1], BOTTOM-0.0025))

    # Processor (6.5 mm, turned 45 degrees) and accelerometer/compass (2 mm LGA), with pad combs.
    body, pads = chip(6.5*MM, 0.85*MM, 12, 0.45*MM, 45, (14.1*MM, 4.4*MM))
    part('processor', 'qfn', [(on_face(body, -1), ic_black), (on_face(pads, -1), steel)], (0.0141, 0.0044, BOTTOM-0.0023))
    body, pads = chip(2.0*MM, 1.0*MM, 3, 0.5*MM, 0, (17.5*MM, -8.0*MM), pad_size=(0.25*MM, 0.35*MM, 0.12*MM))
    part('accel_compass', 'lga', [(on_face(body, -1), accel_black), (on_face(pads, -1), steel)], (0.0175, -0.0080, BOTTOM-0.0024))

    # Antenna: thin meander trace on a 45-degree axis in the corner, about 11 x 12.5 mm (photo about 10 x 13 mm).
    origin, axis, across = (24.88*MM, 11.63*MM), (-math.sqrt(0.5), math.sqrt(0.5)), (-math.sqrt(0.5), -math.sqrt(0.5))
    local = [(0, 5.1), (0, 0), (4.5, 0), (4.5, 2.75), (6.85, 2.75), (6.85, 0), (9.35, 0), (9.35, 2.75), (11.9, 2.75), (11.9, 0)]

    def world(u, v):
        return (origin[0]+(u*axis[0]+v*across[0])*MM, origin[1]+(u*axis[1]+v*across[1])*MM)
    meander = refined_plate(trace_outline([world(u, v) for u, v in local], 0.55*MM), thickness=PLATING, z0=BOTTOM-PLATING)
    # The stub starts at the meander's edge (v = half width): overlapping coplanar tops would render dark specks.
    stub = refined_plate(trace_outline([world(1.35, 0.275), world(1.35, 3.0)], 0.55*MM), thickness=PLATING, z0=BOTTOM-PLATING)
    part('antenna', 'meander trace', [(combine(meander, stub), antenna_gold)], (0.0197, 0.0140, BOTTOM-0.0011))

    # --- PCB with unlabelled parts ------------------------------------------------------------
    holes = [circle_outline(PCB_HOLE, 32, (x, PIN_Y)) for x in PIN_X]
    holes += [circle_outline(MOUNT_R, 12, (s*MOUNT_X, 0.0)) for s in (-1, 1)]
    plate = refined_plate(board_outline(), holes, thickness=THICK, z0=BOTTOM, spacing=2.6*MM)
    dark, tin, cream, brown, lens, port_black = [], [], [], [], [], []
    body, pads = chip(5.0*MM, 0.85*MM, 8, 0.5*MM, 45, (-15.0*MM, 3.0*MM))          # USB interface MCU
    dark.append(on_face(body, -1)); tin.append(on_face(pads, -1))
    cream.append(on_face(box((3.2*MM, 2.5*MM, 0.2*MM), (20.6*MM, -1.3*MM, 0.1*MM)), -1))          # crystal base
    tin.append(on_face(rounded_box((3.0*MM, 2.3*MM, 0.6*MM), 0.1*MM, center=(20.6*MM, -1.3*MM, 0.5*MM), segments=1), -1))
    for (x, y) in ((7.3*MM, 19.1*MM), (-5.0*MM, 19.7*MM)):                               # status LEDs by the USB
        cream.append(on_face(box((0.8*MM, 1.6*MM, 0.35*MM), (x, y, 0.175*MM)), -1))
        lens.append(on_face(box((0.5*MM, 1.0*MM, 0.08*MM), (x, y, 0.38*MM)), -1))
    sots = ((-14.0*MM, 17.6*MM, 90), (-21.4*MM, 11.4*MM, 0), (-16.8*MM, 9.6*MM, 0))
    for x, y, angle in sots:                                                               # SOT-23 regulators
        dark.append(on_face(turned(box((2.9*MM, 1.3*MM, 1.0*MM), (0, 0, 0.5*MM)), angle, (x, y)), -1))
        legs = [box((0.4*MM, 0.6*MM, 0.15*MM), (dx, dy, 0.075*MM)) for dx, dy in ((-0.95*MM, -0.85*MM), (0.95*MM, -0.85*MM), (0, 0.85*MM))]
        tin.append(on_face(turned(combine(*legs), angle, (x, y)), -1))
    for s in (-1, 1):                                                                     # front: USB shell through-hole pads
        tin.append(on_face(refined_plate(rounded_rect_outline(1.0*MM, 1.7*MM, 0.5*MM, segments=4, center=(s*3.65*MM, 19.4*MM)),
                                         thickness=0.04*MM), 1))
        tin.append(on_face(cylinder(0.45*MM, 0.04*MM, center=(s*2.4*MM, 16.7*MM, 0.02*MM), segments=16), 1))
    tin.append(on_face(refined_plate(circle_outline(0.45*MM, 16, (8.2*MM, 10.8*MM)), [circle_outline(0.25*MM, 16, (8.2*MM, 10.8*MM))],
                                     thickness=0.04*MM), 1))                              # front: microphone port ring
    port_black.append(on_face(cylinder(0.25*MM, 0.03*MM, center=(8.2*MM, 10.8*MM, 0.015*MM), segments=16), 1))

    # Passives (0603 size) scattered on the free back areas, kept off every component and the edge connector.
    keep_out = [(-4.4, 4.4, 16.0, 22.3), (-12.9, -6.6, 15.1, 21.0), (-23.6, -15.0, 13.3, 21.0), (6.6, 8.0, 18.1, 20.1),
                (-5.6, -4.4, 18.7, 20.7), (-15.7, -12.3, 15.9, 19.3), (-23.1, -19.7, 10.5, 12.3), (-18.5, -15.1, 8.7, 10.5),
                (5.7, 9.9, 8.4, 12.2), (13.6, 25.6, 7.2, 20.8), (9.0, 19.2, -0.6, 9.4), (-19.0, -11.0, -1.0, 7.0),
                (-7.0, 7.0, -6.2, 7.8), (18.6, 22.6, -3.0, 0.4), (16.0, 19.0, -9.5, -6.5), (23.3, 26.0, -1.2, 1.2),
                (-26.0, -23.3, -1.2, 1.2), (-26.0, 26.0, -21.0, -15.3)]
    keep_out += [(x/MM-3.1, x/MM+3.1, -21.0, -10.9) for x in PIN_X]
    placed = []
    for _ in range(20000):
        if len(placed) == 60:
            break
        x, y = rng.uniform(-24.6, 24.6), rng.uniform(-14.8, 19.8)
        if abs(x) > 22.3 and y > 17.5 or any(a-0.9 < x < b+0.9 and c-0.9 < y < d+0.9 for a, b, c, d in keep_out):
            continue
        if any(math.hypot(x-px, y-py) < 1.6 for px, py in placed):
            continue
        placed.append((x, y))
        angle = rng.choice((0, 0, 90, 90, 45))
        brown.append(on_face(turned(box((1.0*MM, 0.5*MM, 0.35*MM), (0, 0, 0.175*MM)), angle, (x*MM, y*MM)), -1))
        ends = combine(*[box((0.2*MM, 0.52*MM, 0.37*MM), (s*0.5*MM, 0, 0.185*MM)) for s in (-1, 1)])
        tin.append(on_face(turned(ends, angle, (x*MM, y*MM)), -1))
    part('pcb', 'board', [(plate, pcb_mat), (combine(*dark), ic_black), (combine(*tin), steel), (combine(*cream), ivory),
                          (combine(*brown), passive), (combine(*lens), amber), (combine(*port_black), black)],
         (-0.020, 0.0125, TOP))

    return {
        'title': 'micro:bit V2 · detail',
        'design_notes': [
            'Detail of the approved blockout at true size: board 51.6 x 42.0 x 1.6 mm (official V2.2 outline), 11.65 mm deep with components; no BBC/micro:bit logos, FCC ID, text or silkscreen graphics.',
            'One object per contract part_id, flat hierarchy, identity transforms; LEDs and the touch logo are single-material meshes, each LED with its own material led_x_y; caps are separate root objects.',
            'PCB: rounded corners (3.2 mm top, 1 mm bottom), five plated pin holes (4.2 mm) and two 1.2 mm mounting holes; caps re-triangulated with components.refined_plate.',
            'Pins 0, 1, 2, 3V, GND: gold tombstone pads on both faces joined by a plated barrel; edge_connector: 14 narrow fingers per face with dark slits between them.',
            'Front: 25 SMD LED packages (1.0 x 1.8 mm, warm white, 4.0 mm pitch), 6 x 6 mm tact switches A/B with metal cover, legs and black plungers (top 4.55 mm), gold stadium touch logo with two eyes (0.3 mm proud), small round amber microphone LED.',
            'Back: micro-B USB shell with opening and tongue, 6 x 5.8 mm reset switch, JST PH socket with mouth, contacts and slots (5.5 mm), 8.5 mm speaker turned 45 degrees with ring, cone and tabs (3.0 mm), 6.5 mm processor and 2 mm accelerometer/compass with pad combs, gold MEMS microphone can with port, 11 x 12.5 mm meander antenna trace with stub.',
            'Unlabelled parts in pcb: USB interface chip, crystal, three SOT-23 regulators, two status LEDs, 60 passives, USB through-hole pads and the front microphone port.',
            'All component positions and sizes are estimates from reference photos (proportion only); PCB thickness 1.6 mm is assumed, not published.',
        ],
        'parts': labels,
    }
