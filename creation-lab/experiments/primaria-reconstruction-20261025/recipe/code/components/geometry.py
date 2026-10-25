"""Pure geometry in metres, right-handed XYZ with Z up; triangular faces.

Geometric building blocks, not claims about biological accuracy. No Blender,
random state, file access or implicit scene is needed.
"""
from collections import Counter
from dataclasses import dataclass
import math


def _positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return float(value)


def _count(value, minimum, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def _vector(value, name, positive=False):
    try:
        result = tuple(value)
    except TypeError as exc:
        raise ValueError(f"{name} must have three numbers") from exc
    if len(result) != 3:
        raise ValueError(f"{name} must have three numbers")
    for number in result:
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number):
            raise ValueError(f"{name} must contain finite numbers")
        if positive:
            _positive(number, name)
    return result


def _sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


@dataclass(frozen=True)
class MeshData:
    vertices: tuple
    faces: tuple

    @property
    def triangles(self):
        return len(self.faces)


def validate_mesh(mesh, *, closed=True, max_triangles=None):
    """Check finiteness, area, usage, manifold edges and consistent winding.

    A closed mesh must have positive signed volume. Returns measured counts.
    Does not assert absence of arbitrary self-intersections.
    """
    if max_triangles is not None:
        _count(max_triangles, 1, "max_triangles")
        if mesh.triangles > max_triangles:
            raise ValueError(f"Triangle budget exceeded: {mesh.triangles} > {max_triangles}")
    if not mesh.vertices or not mesh.faces:
        raise ValueError("Mesh must contain vertices and triangles")
    vertices = [_vector(v, "vertex") for v in mesh.vertices]
    size = max(max(v[k] for v in vertices)-min(v[k] for v in vertices) for k in range(3))
    threshold = max(size*size*1e-14, 1e-300)
    edges, directions, used = Counter(), Counter(), set()
    volume = 0.0
    origin = vertices[0]  # Local origin avoids cancellation after translation.
    for face in mesh.faces:
        if len(face) != 3 or any(isinstance(i, bool) or not isinstance(i, int) or i < 0 or i >= len(vertices) for i in face):
            raise ValueError("Faces must contain three valid vertex indices")
        a, b, c = [vertices[i] for i in face]
        cross = _cross(_sub(b, a), _sub(c, a))
        if math.sqrt(sum(x*x for x in cross)) <= threshold:
            raise ValueError("Degenerate triangle")
        volume += sum(x*y for x, y in zip(_sub(a, origin), _cross(_sub(b, origin), _sub(c, origin))))/6
        used.update(face)
        for u, v in zip(face, (face[1], face[2], face[0])):
            edge = (min(u, v), max(u, v))
            edges[edge] += 1
            directions[edge] += 1 if u < v else -1
    if len(used) != len(vertices):
        raise ValueError("Unused vertices")
    if any(n > 2 for n in edges.values()):
        raise ValueError("Nonmanifold edge")
    if any(edges[e] == 2 and direction != 0 for e, direction in directions.items()):
        raise ValueError("Inconsistent winding")
    boundary = sum(n == 1 for n in edges.values())
    if closed and boundary:
        raise ValueError("Open boundary in a closed mesh")
    if closed and volume <= 0:
        raise ValueError("Closed mesh must have positive outward volume")
    return {"vertices": len(vertices), "triangles": mesh.triangles,
            "boundary_edges": boundary, "signed_volume": volume}


def _surface_mesh(point, segments, rings, start=0.0):
    """Sphere or south cap. Single poles instead of collapsed pole rings."""
    _count(segments, 3, "segments")
    _count(rings, 2, "rings")
    vertices, faces = [], []
    if start == 0:
        vertices.append(point(0, 0))
        first_theta = 1
    else:
        first_theta = 0
    for j in range(first_theta, rings):
        theta = start+(math.pi-start)*j/rings
        for i in range(segments):
            vertices.append(point(theta, math.tau*i/segments))
    ring_start = 1 if start == 0 else 0
    if start == 0:
        for i in range(segments):
            faces.append((0, 1+i, 1+(i+1)%segments))
    number_of_rings = rings-first_theta
    for j in range(number_of_rings-1):
        a, b = ring_start+j*segments, ring_start+(j+1)*segments
        for i in range(segments):
            nxt = (i+1)%segments
            faces.extend(((a+i, b+i, b+nxt), (a+i, b+nxt, a+nxt)))
    bottom = len(vertices)
    vertices.append(point(math.pi, 0))
    last = ring_start+(number_of_rings-1)*segments
    for i in range(segments):
        faces.append((last+i, bottom, last+(i+1)%segments))
    return vertices, faces


def sphere(radii=(1.0, 1.0, 1.0), *, center=(0, 0, 0), segments=24, rings=12):
    """Closed ellipsoid with single poles and outward winding."""
    radii, center = _vector(radii, "radii", True), _vector(center, "center")
    def point(theta, phi):
        if theta == 0 or theta == math.pi:
            return (center[0], center[1], center[2]+(radii[2] if theta == 0 else -radii[2]))
        return (center[0]+radii[0]*math.sin(theta)*math.cos(phi),
                center[1]+radii[1]*math.sin(theta)*math.sin(phi), center[2]+radii[2]*math.cos(theta))
    vertices, faces = _surface_mesh(point, segments, rings)
    return MeshData(tuple(vertices), tuple(faces))


@dataclass(frozen=True)
class CutawayProfile:
    """Shared ellipsoid drives an open shell and a contained fill.

    cut_fraction is Z/radius_z. wall_fraction scales all three inner radii;
    this is proportional thickness, not a constant normal-distance offset.
    An exposed continuous annular lip closes the shell material at the cut.
    """
    radii: tuple = (1.0, 0.85, 0.65)
    cut_fraction: float = 0.15
    wall_fraction: float = 0.08
    center: tuple = (0, 0, 0)

    def __post_init__(self):
        object.__setattr__(self, "radii", _vector(self.radii, "radii", True))
        object.__setattr__(self, "center", _vector(self.center, "center"))
        _positive(self.wall_fraction, "wall_fraction")
        if self.wall_fraction >= 1:
            raise ValueError("wall_fraction must be < 1")
        if not isinstance(self.cut_fraction, (int, float)) or isinstance(self.cut_fraction, bool) or not math.isfinite(self.cut_fraction) or abs(self.cut_fraction) >= 1-self.wall_fraction:
            raise ValueError("Cut must cross both profiles, away from poles")

    @property
    def inner_radii(self):
        return tuple(r*(1-self.wall_fraction) for r in self.radii)

    @property
    def cut_z(self):
        return self.center[2]+self.radii[2]*self.cut_fraction

    def _cap(self, radii, z, segments, rings):
        theta = math.acos((z-self.center[2])/radii[2])
        def point(t, phi):
            if t == math.pi:
                return (self.center[0], self.center[1], self.center[2]-radii[2])
            return (self.center[0]+radii[0]*math.sin(t)*math.cos(phi),
                    self.center[1]+radii[1]*math.sin(t)*math.sin(phi), self.center[2]+radii[2]*math.cos(t))
        return _surface_mesh(point, segments, rings, theta)

    def shell(self, *, segments=32, rings=12):
        outer, faces = self._cap(self.radii, self.cut_z, segments, rings)
        inner, inner_faces = self._cap(self.inner_radii, self.cut_z, segments, rings)
        offset = len(outer)
        faces.extend(tuple(offset+i for i in reversed(face)) for face in inner_faces)
        for i in range(segments):
            nxt = (i+1)%segments
            faces.extend(((i, nxt, offset+nxt), (i, offset+nxt, offset+i)))
        return MeshData(tuple(outer+inner), tuple(faces))

    def fill(self, *, clearance=0.02, inset=0.03, segments=32, rings=12):
        """Contract the same inner mesh, including its planar top, into itself.

        clearance is bottom gap/cavity height; inset is top gap/outer radius_z.
        Use identical segments/rings for shell and fill to preserve containment
        in the actual faceted cavity, not only in an ideal smooth ellipsoid.
        """
        _positive(clearance, "clearance")
        _positive(inset, "inset")
        bottom = self.center[2]-self.inner_radii[2]
        height = self.cut_z-bottom
        top_gap, bottom_gap = inset*self.radii[2], clearance*height
        contraction = (top_gap+bottom_gap)/height
        if contraction >= 1:
            raise ValueError("Fill top and bottom gaps consume the cavity height")
        pivot = (self.center[0], self.center[1], bottom+bottom_gap/contraction)
        vertices, faces = self._cap(self.inner_radii, self.cut_z, segments, rings)
        vertices = [tuple(p+(1-contraction)*(v-p) for v, p in zip(vertex, pivot)) for vertex in vertices]
        z = self.cut_z-top_gap
        top = len(vertices)
        vertices.append((self.center[0], self.center[1], z))
        for i in range(segments):
            faces.append((top, i, (i+1)%segments))
        return MeshData(tuple(vertices), tuple(faces))


@dataclass(frozen=True)
class FlattenedCisterna:
    """Sealed flattened ellipsoid with a Z wave and a shared anchor surface.

    No lumen or biological scale is claimed. surface()/anchor() use mesh frame.
    """
    radii: tuple = (1.0, 0.65, 0.08)
    wave: float = 0.05
    center: tuple = (0, 0, 0)

    def __post_init__(self):
        object.__setattr__(self, "radii", _vector(self.radii, "radii", True))
        object.__setattr__(self, "center", _vector(self.center, "center"))
        if isinstance(self.wave, bool) or not isinstance(self.wave, (int, float)) or not math.isfinite(self.wave):
            raise ValueError("wave must be finite")
        if self.radii[2] >= min(self.radii[:2]):
            raise ValueError("Flattened cisterna requires radius_z < radius_x and radius_y")

    def surface(self, theta, phi):
        """Point and analytic outward normal; theta in [0,pi], phi any angle."""
        if not isinstance(theta, (int, float)) or not math.isfinite(theta) or not 0 <= theta <= math.pi:
            raise ValueError("theta must be finite and in [0, pi]")
        if not isinstance(phi, (int, float)) or not math.isfinite(phi):
            raise ValueError("phi must be finite")
        a, b, c = self.radii
        x, y, z = a*math.sin(theta)*math.cos(phi), b*math.sin(theta)*math.sin(phi), c*math.cos(theta)
        if theta == 0 or theta == math.pi:
            x = y = 0.0
        warp = self.wave*math.sin(math.pi*x/a)*math.cos(math.pi*y/b)
        gx = self.wave*math.pi/a*math.cos(math.pi*x/a)*math.cos(math.pi*y/b)
        gy = -self.wave*math.pi/b*math.sin(math.pi*x/a)*math.sin(math.pi*y/b)
        normal = (x/(a*a)-gx*z/(c*c), y/(b*b)-gy*z/(c*c), z/(c*c))
        length = math.sqrt(sum(v*v for v in normal))
        point = (self.center[0]+x, self.center[1]+y, self.center[2]+z+warp)
        return point, tuple(v/length for v in normal)

    def anchor(self, theta, phi, *, offset=0.0):
        """Normal offset, e.g. by ribosome radius. Use grid angles for contact.

        Between grid vertices this samples the analytic surface, not a triangle.
        """
        if isinstance(offset, bool) or not isinstance(offset, (int, float)) or not math.isfinite(offset) or offset < 0:
            raise ValueError("offset must be finite and nonnegative")
        point, normal = self.surface(theta, phi)
        return tuple(p+offset*n for p, n in zip(point, normal)), normal

    def mesh(self, *, segments=24, rings=12):
        vertices, faces = _surface_mesh(lambda theta, phi: self.surface(theta, phi)[0], segments, rings)
        return MeshData(tuple(vertices), tuple(faces))
