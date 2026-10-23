"""Geometric regressions, runnable without bpy; optional real Blender probe."""
import math
import os
from pathlib import Path
import subprocess
import sys
import unittest

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from components import CutawayProfile, FlattenedCisterna, MeshData, sphere, validate_mesh


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
