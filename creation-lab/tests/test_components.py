"""Geometric regressions, runnable without bpy; optional real Blender probe."""
import math
import os
import random
from pathlib import Path
import subprocess
import sys
import unittest

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from components import CutawayProfile, FlattenedCisterna, MeshData, sphere, validate_mesh
from components import circle_outline, cylinder, extruded_outline, refined_plate, rounded_box, rounded_rect_outline


class GeometryComponents(unittest.TestCase):
    def test_sphere_single_poles_closed_outward(self):
        for segments, rings in ((3, 2), (8, 4), (24, 12)):
            mesh = sphere((0.12, 0.09, 0.03), center=(1, -2, 0.5), segments=segments, rings=rings)
            metrics = validate_mesh(mesh)
            self.assertEqual(metrics['boundary_edges'], 0)
            self.assertEqual(len(mesh.vertices), 2+segments*(rings-1))
            self.assertEqual(len(set(mesh.vertices)), len(mesh.vertices))
            self.assertEqual(mesh.triangles, 2*segments*(rings-1))
            for face in mesh.faces:
                a, b, c = [mesh.vertices[i] for i in face]
                ab = [b[k]-a[k] for k in range(3)]
                ac = [c[k]-a[k] for k in range(3)]
                normal = (ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0])
                outward = [sum(v[k] for v in (a, b, c))/3-(1, -2, 0.5)[k] for k in range(3)]
                self.assertGreater(sum(x*y for x, y in zip(normal, outward)), 0)

    def test_shell_lip_is_continuous_and_fill_inside_facets(self):
        for cut in (-0.6, 0, 0.65):
            for segments, rings in ((5, 3), (24, 10)):
                profile = CutawayProfile((0.15, 0.11, 0.08), cut_fraction=cut, wall_fraction=0.12,
                                          center=(0.3, -0.2, 0.1))
                shell, fill = profile.shell(segments=segments, rings=rings), profile.fill(
                    clearance=0.04, inset=0.05, segments=segments, rings=rings)
                validate_mesh(shell)
                validate_mesh(fill)
                offset = segments*rings+1
                # Exactly two connected top rings; one continuous annular strip.
                lip = shell.faces[-2*segments:]
                self.assertEqual(len({i for face in lip for i in face}), 2*segments)
                self.assertTrue(all(abs(shell.vertices[i][2]-profile.cut_z) < 1e-14 for f in lip for i in f))
                # Convex cavity halfspaces, taken from reversed inner shell faces.
                # This catches the old error where an analytic inset can escape facets.
                for raw in shell.faces[segments*(2*rings-1): -2*segments]:
                    self.assertTrue(all(i >= offset for i in raw))
                    a, b, c = [shell.vertices[i] for i in reversed(raw)]
                    u, v = [b[k]-a[k] for k in range(3)], [c[k]-a[k] for k in range(3)]
                    n = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
                    for point in fill.vertices:
                        self.assertLessEqual(sum(n[k]*(point[k]-a[k]) for k in range(3)), 1e-15)
                self.assertLess(max(v[2] for v in fill.vertices), profile.cut_z)
                self.assertGreater(min(v[2] for v in fill.vertices), profile.center[2]-profile.inner_radii[2])

    def test_cisterna_anchor_uses_same_mesh_surface_and_normal(self):
        sheet = FlattenedCisterna((0.07, 0.04, 0.004), wave=0.006, center=(0.1, 0.2, -0.3))
        segments, rings = 20, 12
        mesh = sheet.mesh(segments=segments, rings=rings)
        validate_mesh(mesh)
        for j in (1, 4, 7, 11):
            for i in (0, 5, 13):
                theta, phi = math.pi*j/rings, math.tau*i/segments
                point, normal = sheet.surface(theta, phi)
                self.assertEqual(point, mesh.vertices[1+(j-1)*segments+i])
                center, same_normal = sheet.anchor(theta, phi, offset=0.002)
                self.assertEqual(normal, same_normal)
                self.assertAlmostEqual(math.dist(center, point), 0.002)
                self.assertAlmostEqual(sum(v*v for v in normal), 1)
                delta = 1e-6
                for before, after in ((sheet.surface(theta-delta, phi)[0], sheet.surface(theta+delta, phi)[0]),
                                      (sheet.surface(theta, phi-delta)[0], sheet.surface(theta, phi+delta)[0])):
                    tangent = [after[k]-before[k] for k in range(3)]
                    self.assertAlmostEqual(sum(tangent[k]*normal[k] for k in range(3)), 0, places=12)

    def test_invalid_parameters_and_budget(self):
        operations = [lambda: sphere((1, 0, 1)), lambda: sphere(center=(math.nan, 0, 0)),
                      lambda: sphere(segments=2), lambda: sphere(rings=1), lambda: sphere(segments=3.5),
                      lambda: CutawayProfile(wall_fraction=1), lambda: CutawayProfile(cut_fraction=0.95),
                      lambda: CutawayProfile(cut_fraction=math.nan), lambda: CutawayProfile().fill(clearance=-1),
                      lambda: CutawayProfile().fill(inset=8), lambda: FlattenedCisterna((1, 1, 1)),
                      lambda: FlattenedCisterna(wave=math.inf), lambda: FlattenedCisterna().surface(-1, 0),
                      lambda: FlattenedCisterna().anchor(1, 0, offset=-1),
                      lambda: validate_mesh(sphere(), max_triangles=3)]
        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises(ValueError):
                    operation()

    def test_validator_detects_real_geometry_errors(self):
        good = sphere(segments=8, rings=4)
        invalid = [MeshData(good.vertices, good.faces[:-1]),
                   MeshData(good.vertices, ((0, 0, 1),)+good.faces),
                   MeshData(((math.inf, 0, 0),)+good.vertices[1:], good.faces),
                   MeshData(good.vertices, (tuple(reversed(good.faces[0])),)+good.faces[1:]),
                   MeshData(good.vertices, tuple(tuple(reversed(face)) for face in good.faces))]
        for mesh in invalid:
            with self.assertRaises(ValueError):
                validate_mesh(mesh)


def _signed_area(points):
    return sum(points[i][0]*points[(i+1) % len(points)][1]-points[(i+1) % len(points)][0]*points[i][1]
               for i in range(len(points)))/2


def _pcb_parts(segments=24):
    outline = rounded_rect_outline(0.052, 0.042, 0.003)
    holes = [circle_outline(HOLE_RADIUS, segments, (x, -0.0165)) for x in HOLE_X]
    return outline, holes


# The brief gives radius 0.0035 at x = +-0.0225, which is tangent to the 0.026 board edge.
# Radius 0.003 keeps every hole fully inside the outline with a 0.5 mm margin.
HOLE_RADIUS = 0.003
HOLE_X = (-0.0225, -0.01125, 0.0, 0.01125, 0.0225)


class BoardShapeComponents(unittest.TestCase):
    def test_rounded_rect_and_circle_outlines(self):
        outline = rounded_rect_outline(0.052, 0.042, 0.003, segments=6, center=(0.1, -0.2))
        self.assertEqual(len(outline), 28)
        self.assertGreater(_signed_area(outline), 0)
        self.assertAlmostEqual(min(p[0] for p in outline), 0.1-0.026)
        self.assertAlmostEqual(max(p[1] for p in outline), -0.2+0.021)
        expected = 0.052*0.042-(4-math.pi)*0.003**2
        self.assertAlmostEqual(_signed_area(outline)/expected, 1, delta=2e-3)
        sharp = rounded_rect_outline(2, 1, 0)
        self.assertEqual(sharp, [(1.0, 0.5), (-1.0, 0.5), (-1.0, -0.5), (1.0, -0.5)])
        stadium = rounded_rect_outline(0.02, 0.01, 0.005, segments=4)
        self.assertEqual(len(set(stadium)), len(stadium))
        circle = circle_outline(0.01, 16, (1, 2))
        self.assertEqual(len(circle), 16)
        self.assertGreater(_signed_area(circle), 0)
        for x, y in circle:
            self.assertAlmostEqual(math.hypot(x-1, y-2), 0.01)

    def test_pcb_with_five_holes_is_closed_exterior_and_budgeted(self):
        outline, holes = _pcb_parts()
        thickness = 0.0016
        mesh = extruded_outline(outline, holes, thickness=thickness, z0=0.002)
        metrics = validate_mesh(mesh)
        self.assertEqual(metrics['boundary_edges'], 0)
        self.assertGreater(metrics['signed_volume'], 0)
        self.assertEqual(len(set(mesh.vertices)), len(mesh.vertices))
        expected = (0.052*0.042-(4-math.pi)*0.003**2-5*math.pi*HOLE_RADIUS**2)*thickness
        self.assertAlmostEqual(metrics['signed_volume']/expected, 1, delta=0.01)
        self.assertLess(mesh.triangles, 3000)
        self.assertAlmostEqual(min(v[2] for v in mesh.vertices), 0.002)
        self.assertAlmostEqual(max(v[2] for v in mesh.vertices), 0.002+thickness)
        # Exact against the polygons actually extruded.
        exact = (_signed_area(outline)+sum(_signed_area(h) for h in holes)*-1)*thickness
        self.assertAlmostEqual(metrics['signed_volume']/exact, 1, delta=1e-9)

    def test_input_winding_is_normalised(self):
        outline, holes = _pcb_parts(12)
        reference = validate_mesh(extruded_outline(outline, holes))['signed_volume']
        flipped = validate_mesh(extruded_outline(outline[::-1], [h[::-1] for h in holes]))
        self.assertAlmostEqual(flipped['signed_volume']/reference, 1, delta=1e-9)
        self.assertEqual(flipped['boundary_edges'], 0)

    def test_hole_crossing_outline_or_other_hole_raises(self):
        outline = rounded_rect_outline(0.052, 0.042, 0.003)
        bad = {
            'crosses outline': [circle_outline(0.0035, 24, (0.0225, -0.0165))],
            'outside outline': [circle_outline(0.003, 24, (0.1, 0))],
            'touches outline': [circle_outline(0.003, 24, (0.023, 0))],
            'overlaps hole': [circle_outline(0.004, 24, (0, 0)), circle_outline(0.004, 24, (0.006, 0))],
            'nested hole': [circle_outline(0.01, 24, (0, 0)), circle_outline(0.002, 24, (0, 0))],
            'self intersecting hole': [[(0, 0), (0.01, 0.01), (0.01, 0), (0, 0.01)]],
        }
        for name, holes in bad.items():
            with self.subTest(name):
                with self.assertRaises(ValueError):
                    extruded_outline(outline, holes)

    def test_concave_outline_with_holes_matches_polygon_volume(self):
        l_shape = [(0, 0), (0.04, 0), (0.04, 0.01), (0.01, 0.01), (0.01, 0.03), (0, 0.03)]
        mesh = extruded_outline(l_shape, thickness=0.002)
        metrics = validate_mesh(mesh)
        self.assertEqual(mesh.triangles, 2*(len(l_shape)-2)+2*len(l_shape))
        self.assertAlmostEqual(metrics['signed_volume'], _signed_area(l_shape)*0.002, places=15)
        holed = extruded_outline(l_shape, [circle_outline(0.002, 12, (0.005, 0.02)),
                                           circle_outline(0.002, 12, (0.005, 0.005)),
                                           circle_outline(0.002, 12, (0.03, 0.005))])
        validate_mesh(holed)

    def test_star_outlines_with_holes_fuzz(self):
        rng = random.Random(7)
        for case in range(25):
            count = rng.randint(8, 40)
            star = [(r*math.cos(math.tau*i/count), r*math.sin(math.tau*i/count))
                    for i in range(count) for r in (rng.uniform(0.6, 1.0),)]
            centers = [(0.35*math.cos(a), 0.35*math.sin(a)) for a in (0.3+case*0.2, 2.4+case*0.2, 4.5+case*0.2)][:rng.randint(0, 3)]
            holes = [circle_outline(0.12, rng.randint(3, 10), c) for c in centers]
            with self.subTest(case=case):
                mesh = extruded_outline(star, holes, thickness=0.1)
                metrics = validate_mesh(mesh)
                area = _signed_area(star)-sum(_signed_area(h) for h in holes)
                self.assertAlmostEqual(metrics['signed_volume']/(area*0.1), 1, delta=1e-9)

    def test_rounded_box_volume_closed_and_bounds(self):
        size, radius = (0.02, 0.014, 0.01), 0.002
        a, b, c = size
        core = (a-2*radius)*(b-2*radius)*(c-2*radius)
        slabs = 2*radius*((a-2*radius)*(b-2*radius)+(b-2*radius)*(c-2*radius)+(a-2*radius)*(c-2*radius))
        edges = math.pi*radius**2*((a-2*radius)+(b-2*radius)+(c-2*radius))
        corners = 4/3*math.pi*radius**3
        analytic = core+slabs+edges+corners  # box with all edges rounded by a quarter-cylinder, corners by spheres
        mesh = rounded_box(size, radius, center=(1, -2, 0.5))
        metrics = validate_mesh(mesh)
        self.assertEqual(metrics['boundary_edges'], 0)
        self.assertAlmostEqual(metrics['signed_volume']/analytic, 1, delta=0.02)
        for k, centre in enumerate((1, -2, 0.5)):
            self.assertAlmostEqual(min(v[k] for v in mesh.vertices), centre-size[k]/2)
            self.assertAlmostEqual(max(v[k] for v in mesh.vertices), centre+size[k]/2)
        plain = rounded_box(size, 0)
        self.assertEqual(plain.triangles, 12)
        self.assertAlmostEqual(validate_mesh(plain)['signed_volume'], a*b*c, places=15)
        coarse = validate_mesh(rounded_box(size, radius, segments=1))
        self.assertGreater(coarse['signed_volume'], 0)

    def test_cylinder_triangle_count_volume_and_position(self):
        for segments in (3, 8, 24):
            mesh = cylinder(0.004, 0.01, center=(1, 2, 3), segments=segments)
            metrics = validate_mesh(mesh)
            self.assertEqual(mesh.triangles, 4*segments)
            self.assertEqual(len(mesh.vertices), 2*segments+2)
            expected = 0.5*segments*math.sin(math.tau/segments)*0.004**2*0.01
            self.assertAlmostEqual(metrics['signed_volume']/expected, 1, delta=1e-9)
            self.assertAlmostEqual(min(v[2] for v in mesh.vertices), 3-0.005)
            self.assertAlmostEqual(max(v[2] for v in mesh.vertices), 3+0.005)
            self.assertAlmostEqual(sum(v[0] for v in mesh.vertices)/len(mesh.vertices), 1)

    def test_invalid_shape_arguments(self):
        square = [(0, 0), (1, 0), (1, 1), (0, 1)]
        operations = [
            lambda: rounded_rect_outline(0, 1, 0), lambda: rounded_rect_outline(1, math.nan, 0),
            lambda: rounded_rect_outline(1, 1, -0.1), lambda: rounded_rect_outline(1, 0.5, 0.26),
            lambda: rounded_rect_outline(1, 1, math.inf), lambda: rounded_rect_outline(1, 1, 0.1, segments=0),
            lambda: rounded_rect_outline(1, 1, 0.1, segments=2.5), lambda: rounded_rect_outline(1, 1, 0.1, center=(0,)),
            lambda: rounded_rect_outline(1, 1, 0.1, center=(0, math.nan)),
            lambda: circle_outline(0), lambda: circle_outline(-1), lambda: circle_outline(math.nan),
            lambda: circle_outline(1, segments=2), lambda: circle_outline(1, center=(math.inf, 0)),
            lambda: extruded_outline([(0, 0), (1, 0)]), lambda: extruded_outline([]),
            lambda: extruded_outline([(0, 0), (1, 0), (math.nan, 1)]),
            lambda: extruded_outline([(0, 0), (1, 0), (1,)]),
            lambda: extruded_outline([(0, 0), (1, 0), (2, 0)]),
            lambda: extruded_outline([(0, 0), (1, 0), (1, 0), (0, 1)]),
            lambda: extruded_outline([(0, 0), (1, 1), (1, 0), (0, 1)]),
            lambda: extruded_outline(square, thickness=0), lambda: extruded_outline(square, thickness=math.inf),
            lambda: extruded_outline(square, z0=math.nan), lambda: extruded_outline(square, holes=[[(0.4, 0.4), (0.6, 0.4)]]),
            lambda: extruded_outline(square, holes=[[(0.4, 0.4), (0.6, 0.4), (0.6, math.nan)]]),
            lambda: rounded_box((1, 1), 0.1), lambda: rounded_box((1, 0, 1), 0.1),
            lambda: rounded_box((1, 1, 1), -0.1), lambda: rounded_box((1, 1, 1), 0.5),
            lambda: rounded_box((1, 1, 1), math.nan), lambda: rounded_box((1, 1, 1), 0.1, segments=0),
            lambda: rounded_box((1, 1, 1), 0.1, center=(0, 0)),
            lambda: cylinder(0, 1), lambda: cylinder(1, -1), lambda: cylinder(1, math.nan),
            lambda: cylinder(1, 1, segments=2), lambda: cylinder(1, 1, center=(0, 0, math.inf)),
        ]
        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises(ValueError):
                    operation()


def _cap_triangles(mesh, z):
    """Top-cap triangles (all three vertices at height z) as 2D point triples."""
    return [[mesh.vertices[i][:2] for i in face] for face in mesh.faces
            if all(abs(mesh.vertices[i][2]-z) < 1e-12 for i in face)]


def _min_angle(triangles):
    worst = 180.0
    for tri in triangles:
        for k in range(3):
            a, b, c = tri[k], tri[(k+1) % 3], tri[(k+2) % 3]
            u, v = (b[0]-a[0], b[1]-a[1]), (c[0]-a[0], c[1]-a[1])
            cosine = (u[0]*v[0]+u[1]*v[1])/(math.hypot(*u)*math.hypot(*v))
            worst = min(worst, math.degrees(math.acos(max(-1.0, min(1.0, cosine)))))
    return worst


def _microbit_pcb():
    """Brief values: 52 x 42 mm, r = 3 mm, five holes r = 3.4 mm at y = -16.5 mm."""
    outline = rounded_rect_outline(0.052, 0.042, 0.003)
    holes = [circle_outline(0.0034, 24, (x, -0.0165)) for x in (-0.0225, -0.01125, 0.0, 0.01125, 0.0225)]
    return outline, holes


def _blockout_pcb():
    """The approved blockout's PCB (generator_blockout.board_outline and holes), for the oracle numbers."""
    r, hx, hy = 0.0035, 0.0258, 0.021
    outline = [(-hx, -hy), (hx, -hy)]
    for cx, start in ((hx-r, 0.0), (-hx+r, 90.0)):
        for k in range(7):
            angle = math.radians(start+90.0*k/6)
            outline.append((cx+r*math.cos(angle), hy-r+r*math.sin(angle)))
    holes = [circle_outline(0.0024, 24, (x, -0.0143)) for x in (-0.022, -0.011, 0.0, 0.011, 0.022)]
    return outline, holes


class RefinedPlate(unittest.TestCase):
    def test_microbit_pcb_closed_same_volume_and_well_shaped(self):
        outline, holes = _microbit_pcb()
        mesh = refined_plate(outline, holes, thickness=0.0016, z0=-0.0008, spacing=0.0026)
        metrics = validate_mesh(mesh)
        self.assertEqual(metrics['boundary_edges'], 0)
        reference = validate_mesh(extruded_outline(outline, holes, thickness=0.0016, z0=-0.0008))
        self.assertAlmostEqual(metrics['signed_volume']/reference['signed_volume'], 1, delta=1e-9)
        self.assertLess(mesh.triangles, 3000)
        self.assertGreaterEqual(_min_angle(_cap_triangles(mesh, 0.0008)), 5.0)
        self.assertGreaterEqual(_min_angle(_cap_triangles(mesh, -0.0008)), 5.0)
        # The ear-clipped reference really is the sliver case this function exists for.
        self.assertLess(_min_angle(_cap_triangles(extruded_outline(outline, holes, thickness=0.0016, z0=-0.0008), 0.0008)), 1.0)
        self.assertAlmostEqual(min(v[2] for v in mesh.vertices), -0.0008)
        self.assertAlmostEqual(max(v[2] for v in mesh.vertices), 0.0008)

    def test_holes_stay_open(self):
        outline, holes = _microbit_pcb()
        mesh = refined_plate(outline, holes, thickness=0.0016, spacing=0.0026)
        caps = _cap_triangles(mesh, 0.0016)

        def inside(p, tri):
            (ax, ay), (bx, by), (cx, cy) = tri
            d = [(bx-ax)*(p[1]-ay)-(by-ay)*(p[0]-ax), (cx-bx)*(p[1]-by)-(cy-by)*(p[0]-bx), (ax-cx)*(p[1]-cy)-(ay-cy)*(p[0]-cx)]
            return min(d) >= 0 or max(d) <= 0
        for x in (-0.0225, -0.01125, 0.0, 0.01125, 0.0225):
            for dx, dy in ((0, 0), (0.002, 0), (0, -0.002), (-0.0015, 0.0015)):
                point = (x+dx, -0.0165+dy)
                self.assertFalse(any(inside(point, tri) for tri in caps), point)
        # Every hole point is still a wall vertex: the hole outlines are unchanged.
        tops = {v[:2] for v in mesh.vertices if abs(v[2]-0.0016) < 1e-12}
        for hole in holes:
            for point in hole:
                self.assertIn(point, tops)
        # The top cap area equals the outline minus the holes.
        area = sum(abs(_signed_area(t)) for t in caps)
        self.assertAlmostEqual(area/(_signed_area(outline)-sum(_signed_area(h) for h in holes)), 1, delta=1e-9)

    def test_blockout_pcb_matches_reviewer_oracle(self):
        outline, holes = _blockout_pcb()
        mesh = refined_plate(outline, holes, thickness=0.0016, z0=-0.0008, spacing=0.0026)
        metrics = validate_mesh(mesh)
        self.assertAlmostEqual(metrics['signed_volume']/3.315641e-06, 1, delta=1e-6)
        area = sum(abs(_signed_area(t)) for t in _cap_triangles(mesh, 0.0008))
        self.assertAlmostEqual(area/2.072275e-03, 1, delta=1e-6)
        self.assertGreaterEqual(_min_angle(_cap_triangles(mesh, 0.0008)), 5.0)

    def test_without_spacing_keeps_points_and_volume(self):
        outline, holes = _pcb_parts(12)
        mesh = refined_plate(outline, holes, thickness=0.002)
        reference = extruded_outline(outline, holes, thickness=0.002)
        self.assertEqual(sorted(mesh.vertices), sorted(reference.vertices))
        self.assertEqual(mesh.triangles, reference.triangles)
        metrics = validate_mesh(mesh)
        self.assertAlmostEqual(metrics['signed_volume']/validate_mesh(reference)['signed_volume'], 1, delta=1e-9)
        self.assertGreaterEqual(_min_angle(_cap_triangles(mesh, 0.002)), _min_angle(_cap_triangles(reference, 0.002)))

    def test_small_plates_and_concave_outline(self):
        l_shape = [(0, 0), (0.04, 0), (0.04, 0.01), (0.01, 0.01), (0.01, 0.03), (0, 0.03)]
        for spacing in (None, 0.004):
            mesh = refined_plate(l_shape, thickness=0.002, spacing=spacing)
            self.assertAlmostEqual(validate_mesh(mesh)['signed_volume'], _signed_area(l_shape)*0.002, places=15)
        ring = refined_plate(circle_outline(0.0026, 32), [circle_outline(0.0021, 32)], thickness=0.00006, spacing=0.0005)
        validate_mesh(ring)

    def test_bad_input_raises(self):
        outline = rounded_rect_outline(0.052, 0.042, 0.003)
        bad = [
            dict(holes=[circle_outline(0.0035, 24, (0.0225, -0.0165))]),          # crosses the outline
            dict(holes=[circle_outline(0.004, 24, (0, 0)), circle_outline(0.004, 24, (0.006, 0))]),
            dict(holes=[circle_outline(0.003, 24, (0.1, 0))]),
            dict(spacing=0), dict(spacing=-0.001), dict(spacing=math.nan), dict(thickness=0),
        ]
        for kwargs in bad:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    refined_plate(outline, **kwargs)


@unittest.skipUnless(os.environ.get('CREATION_TEST_BLENDER'), 'Set CREATION_TEST_BLENDER for real bpy adapter checks')
class BlenderComponents(unittest.TestCase):
    def test_real_adapter(self):
        result = subprocess.run([os.environ['CREATION_TEST_BLENDER'], '--background', '--factory-startup',
                                 '--disable-autoexec', '--threads', '2', '--python',
                                 str(LAB/'tests/component_probe.py')], capture_output=True, text=True,
                                timeout=120, env={**os.environ, 'CUDA_VISIBLE_DEVICES': ''})
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn('COMPONENT_ADAPTER=PASS', result.stdout)


if __name__ == '__main__':
    unittest.main()
