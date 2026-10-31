"""micro:bit V2 blockout: simple volumes at true positions and sizes.

Blender conventions: metres, Z up, front -Y. The board lies flat with the LED
face toward +Z and the edge connector toward -Y; the origin is the board centre
on the PCB mid-plane (glTF export turns +Z into +Y and -Y into +Z). Dimensions
come from https://tech.microbit.org/hardware/2-2-revision/ (51.60 x 42.00 mm,
11.65 mm deep with components: button 4.55 mm above the board, speaker 3.00 mm
and JST socket 5.50 mm below it) and positions from reference photos (proportion
only, never textures). PCB thickness 1.6 mm is assumed. No BBC / micro:bit
logos, FCC ID or text. LED x = column, y = row, origin top-left seen from the
LED face with the edge connector at the bottom, so y grows toward the edge.
"""
import math
from components import MeshData, circle_outline, cylinder, extruded_outline, material, mesh_object
from components import rounded_box, rounded_rect_outline

MM = 0.001
WIDTH, HEIGHT, THICK = 51.6*MM, 42.0*MM, 1.6*MM
TOP, BOTTOM = THICK/2, -THICK/2          # PCB face planes (z)
PIN_X = (-22.0*MM, -11.0*MM, 0.0, 11.0*MM, 22.0*MM)
PIN_Y = -14.3*MM
PIN_HOLE, PIN_RING = 2.4*MM, 3.4*MM      # hole radius must stay < 3.5 mm (tangent to the edge at +-22 mm)
LED_PITCH_X, LED_PITCH_Y, LED_CENTER_Y = 3.75*MM, 3.8*MM, -0.7*MM
BTN_X, BTN_Y = 20.5*MM, -0.5*MM


def board_outline():
    """Counter-clockwise outline: sharp edge-connector corners, rounded top corners (r = 3.5 mm)."""
    r, hx, hy = 3.5*MM, WIDTH/2, HEIGHT/2
    points = [(-hx, -hy), (hx, -hy)]
    for cx, start in ((hx-r, 0.0), (-hx+r, 90.0)):
        for k in range(7):
            angle = math.radians(start+90.0*k/6)
            points.append((cx+r*math.cos(angle), hy-r+r*math.sin(angle)))
    return points


def turned(mesh, degrees, center):
    """Rotate a mesh about its own Z axis (built around the origin), then move it to center."""
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    vertices = tuple((center[0]+c*x-s*y, center[1]+s*x+c*y, center[2]+z) for x, y, z in mesh.vertices)
    return MeshData(vertices, mesh.faces)


def build():
    mats = {}

    def mat(name, color, roughness=0.5, metallic=0.0):
        mats[name] = material(name, color, roughness=roughness, metallic=metallic)
        return mats[name]

    labels = {}

    def add(part_id, mesh, material_, label, name='body', smooth=False):
        mesh_object(name, part_id, mesh, material_, smooth=smooth)
        labels[part_id] = {'label_position': [round(v, 6) for v in label]}

    pcb_mat = mat('mat_pcb', (0.035, 0.040, 0.048), 0.6)
    gold = mat('mat_edge_gold', (0.85, 0.56, 0.12), 0.35, 0.7)
    ring_gold = mat('mat_pin_gold', (0.90, 0.62, 0.16), 0.35, 0.7)
    logo_gold = mat('mat_logo_gold', (0.95, 0.66, 0.14), 0.35, 0.7)

    holes = [circle_outline(PIN_HOLE, 24, (x, PIN_Y)) for x in PIN_X]
    add('pcb', extruded_outline(board_outline(), holes, thickness=THICK, z0=BOTTOM), pcb_mat,
        (-0.020, 0.0125, TOP), name='plate')
    add('edge_connector', extruded_outline(rounded_rect_outline(51.0*MM, 4.0*MM, 0, center=(0, -19.0*MM)),
                                            thickness=0.1*MM, z0=TOP), gold, (0.0, -0.0190, TOP+0.001),
        name='gold fingers')
    pins = ('pin_0', 'pin_1', 'pin_2', 'pin_3v', 'pin_gnd')
    for part, x in zip(pins, PIN_X):
        add(part, extruded_outline(circle_outline(PIN_RING, 24, (x, PIN_Y)), [circle_outline(PIN_HOLE, 24, (x, PIN_Y))],
                                    thickness=0.1*MM, z0=TOP+0.1*MM), ring_gold, (x, PIN_Y, TOP+0.0035), name='ring')

    # Front face (+Z): LED grid, A / B buttons, touch logo, microphone indicator.
    btn_body = mat('mat_button_body', (0.30, 0.31, 0.34), 0.45, 0.3)
    for part, sign in (('a', -1), ('b', 1)):
        cx = sign*BTN_X
        add('btn_'+part, rounded_box((5.0*MM, 5.0*MM, 3.0*MM), 0.4*MM, center=(cx, BTN_Y, TOP+1.5*MM)),
            btn_body, (cx, BTN_Y, TOP+0.0056), name='body')
        cap = mat('mat_btn_%s_cap' % part, (0.55, 0.12, 0.10) if part == 'a' else (0.12, 0.30, 0.60), 0.5)
        add('btn_%s_cap' % part, cylinder(1.6*MM, 1.55*MM, center=(cx, BTN_Y, TOP+3.0*MM+0.775*MM), segments=20),
            cap, (cx, BTN_Y, TOP+0.0062), name='cap')
    add('logo_touch', extruded_outline(rounded_rect_outline(8.6*MM, 4.2*MM, 2.1*MM, segments=8, center=(0, 12.8*MM)),
                                        thickness=0.15*MM, z0=TOP), logo_gold, (0.0, 0.0148, TOP+0.0015), name='stadium')
    add('mic_led', rounded_box((0.8*MM, 0.8*MM, 0.4*MM), 0.15*MM, center=(7.9*MM, 10.3*MM, TOP+0.2*MM), segments=2),
        mat('mat_mic_led', (0.85, 0.75, 0.10), 0.4), (0.0079, 0.0103, TOP+0.0025), name='indicator')
    for y in range(5):
        for x in range(5):
            part = 'led_%d_%d' % (x, y)
            colour = (0.55+0.004*(5*y+x), 0.05, 0.03)  # distinct per LED so exporters cannot merge them
            cx, cy = (x-2)*LED_PITCH_X, LED_CENTER_Y-(y-2)*LED_PITCH_Y
            add(part, rounded_box((1.0*MM, 1.7*MM, 0.6*MM), 0.15*MM, center=(cx, cy, TOP+0.3*MM), segments=2),
                mat(part, colour, 0.4), (cx, cy, TOP+0.0015), name='diode')

    # Back face (-Z): USB, reset, battery socket, speaker, microphone, chips, antenna.
    # Positions are the front-view (x right) coordinates of the photographed back, mirrored.
    steel = mat('mat_usb_steel', (0.62, 0.64, 0.68), 0.3, 0.8)
    add('usb', rounded_box((7.5*MM, 5.4*MM, 2.6*MM), 0.3*MM, center=(0, 19.1*MM, BOTTOM-1.3*MM)), steel,
        (0.0, 0.0191, BOTTOM-0.0036), name='micro usb')
    add('reset_btn', rounded_box((6.0*MM, 6.0*MM, 3.5*MM), 0.4*MM, center=(-9.7*MM, 18.0*MM, BOTTOM-1.75*MM)),
        mat('mat_reset', (0.10, 0.10, 0.11), 0.5), (-0.0097, 0.018, BOTTOM-0.0045), name='tact')
    add('battery_socket', rounded_box((8.0*MM, 7.5*MM, 5.5*MM), 0.4*MM, center=(-19.6*MM, 17.25*MM, BOTTOM-2.75*MM)),
        mat('mat_battery_ivory', (0.80, 0.76, 0.62), 0.6), (-0.0196, 0.01725, BOTTOM-0.0065), name='jst')
    add('speaker', turned(rounded_box((7.6*MM, 7.6*MM, 3.0*MM), 0.8*MM, segments=3), 45, (-0.5*MM, 1.5*MM, BOTTOM-1.5*MM)),
        mat('mat_speaker', (0.06, 0.06, 0.07), 0.4), (-0.0005, 0.0015, BOTTOM-0.0040), name='buzzer')
    add('mic', rounded_box((3.8*MM, 3.0*MM, 1.1*MM), 0.3*MM, center=(8.0*MM, 10.5*MM, BOTTOM-0.55*MM)),
        mat('mat_mic', (0.80, 0.68, 0.22), 0.3, 0.8), (0.0080, 0.0105, BOTTOM-0.0021), name='mems')
    add('processor', turned(rounded_box((7.0*MM, 7.0*MM, 0.9*MM), 0.2*MM, segments=2), 45, (13.7*MM, 4.3*MM, BOTTOM-0.45*MM)),
        mat('mat_processor', (0.02, 0.02, 0.025), 0.5), (0.0137, 0.0043, BOTTOM-0.0019), name='qfn')
    add('accel_compass', rounded_box((2.0*MM, 2.0*MM, 0.9*MM), 0.2*MM, center=(19.8*MM, -6.5*MM, BOTTOM-0.45*MM), segments=2),
        mat('mat_accel', (0.10, 0.10, 0.12), 0.5), (0.0198, -0.0065, BOTTOM-0.0019), name='lga')
    add('antenna', extruded_outline(rounded_rect_outline(8.0*MM, 9.0*MM, 0.8*MM, segments=3, center=(19.9*MM, 13.6*MM)),
                                     thickness=0.1*MM, z0=BOTTOM-0.1*MM),
        mat('mat_antenna', (0.80, 0.52, 0.10), 0.35, 0.7), (0.0199, 0.0136, BOTTOM-0.0011), name='trace')

    return {
        'title': 'micro:bit V2 · blockout',
        'design_notes': [
            'Blockout of simple volumes at true size: board 51.6 x 42.0 x 1.6 mm (official V2.2 outline); no BBC/micro:bit logos, FCC ID or text.',
            'LED face +Z, edge connector toward -Y, origin at the board centre on the PCB mid-plane; Studio sees them as +Y and +Z.',
            'Five pin rings at x = -22, -11, 0, 11, 22 mm, y = -14.3 mm; PCB holes have radius 2.4 mm (below the 3.5 mm edge tangent).',
            '25 LEDs on a 3.75 x 3.8 mm grid, x = column, y = row from the top-left (edge connector at the bottom); one material each.',
            'Buttons A and B at x = -20.5 / +20.5 mm with separate caps (top 4.55 mm above the board); touch logo as a solid stadium plate for picking, ring detail later.',
            'Back (-Z): USB, reset, battery socket (5.5 mm), 45-degree speaker (3.0 mm), microphone, processor, accelerometer/compass and antenna trace.',
            'Positions are estimated from reference photos (proportion only); PCB thickness 1.6 mm is assumed, not published.',
        ],
        'parts': labels,
    }
