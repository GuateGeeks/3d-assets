"""Board-shape building blocks in metres, right-handed XYZ with Z up.

Flat plates with holes and small boxes/cylinders as ``MeshData``. Pure Python:
no Blender, random state or file access. Every mesh is closed, manifold and
wound outward so it passes ``validate_mesh``.
"""
import math

from .geometry import MeshData, _count, _positive, _vector


def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


def _nonnegative(value, name):
    if _finite(value, name) < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return float(value)


def _point2(value, name):
    try:
        result = tuple(value)
    except TypeError as exc:
        raise ValueError(f"{name} must have two numbers") from exc
    if len(result) != 2:
        raise ValueError(f"{name} must have two numbers")
    return (_finite(result[0], name), _finite(result[1], name))


def _signed_area(points):
    n = len(points)
    return sum(points[i][0]*points[(i+1) % n][1]-points[(i+1) % n][0]*points[i][1] for i in range(n))/2


def _dedupe(points):
    """Drop consecutive coincident points (including the wrap-around)."""
    result = []
    for point in points:
        if not result or math.dist(point, result[-1]) > 1e-12:
            result.append(point)
    while len(result) > 1 and math.dist(result[0], result[-1]) <= 1e-12:
        result.pop()
    return result


def rounded_rect_outline(width, height, radius, segments=6, center=(0, 0)):
    """Counter-clockwise rectangle outline with rounded corners.

    radius may be 0 (four sharp corners) up to min(width, height)/2; each
    corner arc has ``segments`` subdivisions (segments + 1 points).
    """
    width, height = _positive(width, "width"), _positive(height, "height")
    radius = _nonnegative(radius, "radius")
    if radius > min(width, height)/2*(1+1e-12):
        raise ValueError("radius must be <= min(width, height)/2")
    _count(segments, 1, "segments")
    cx, cy = _point2(center, "center")
    hx, hy = width/2, height/2
    if radius == 0:
        return [(cx+hx, cy+hy), (cx-hx, cy+hy), (cx-hx, cy-hy), (cx+hx, cy-hy)]
    ix, iy = hx-radius, hy-radius
    points = []
    for sx, sy, start in ((1, 1, 0.0), (-1, 1, 90.0), (-1, -1, 180.0), (1, -1, 270.0)):
        for k in range(segments+1):
            angle = math.radians(start+90.0*k/segments)
            points.append((cx+sx*ix+radius*math.cos(angle), cy+sy*iy+radius*math.sin(angle)))
    return _dedupe(points)


def circle_outline(radius, segments=24, center=(0, 0)):
    """Counter-clockwise regular polygon inscribed in a circle, first point at angle 0."""
    radius = _positive(radius, "radius")
    _count(segments, 3, "segments")
    cx, cy = _point2(center, "center")
    return [(cx+radius*math.cos(math.tau*i/segments), cy+radius*math.sin(math.tau*i/segments))
            for i in range(segments)]


# --- 2D predicates ---------------------------------------------------------

def _orient(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def _on_segment(a, b, p):
    return min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])


def _segments_touch(a, b, c, d, eps):
    """True if closed segments ab and cd share any point (within eps)."""
    def sign(value):
        return 0 if abs(value) <= eps else (1 if value > 0 else -1)
    s1, s2, s3, s4 = sign(_orient(a, b, c)), sign(_orient(a, b, d)), sign(_orient(c, d, a)), sign(_orient(c, d, b))
    if s1*s2 < 0 and s3*s4 < 0:
        return True
    return ((s1 == 0 and _on_segment(a, b, c)) or (s2 == 0 and _on_segment(a, b, d))
            or (s3 == 0 and _on_segment(c, d, a)) or (s4 == 0 and _on_segment(c, d, b)))


def _inside(polygon, p):
    """Crossing-number point-in-polygon; callers rule out boundary contact first."""
    inside = False
    n = len(polygon)
    for i in range(n):
        a, b = polygon[i], polygon[(i+1) % n]
        if (a[1] > p[1]) != (b[1] > p[1]) and p[0] < a[0]+(p[1]-a[1])*(b[0]-a[0])/(b[1]-a[1]):
            inside = not inside
    return inside


def _loop(points, name):
    try:
        loop = [_point2(p, name) for p in points]
    except TypeError as exc:
        raise ValueError(f"{name} must be a list of (x, y) points") from exc
    if len(loop) < 3:
        raise ValueError(f"{name} needs at least 3 points")
    n = len(loop)
    scale = max(max(p[k] for p in loop)-min(p[k] for p in loop) for k in range(2))
    if scale <= 0:
        raise ValueError(f"{name} is degenerate")
    for i in range(n):
        if math.dist(loop[i], loop[(i+1) % n]) <= scale*1e-9:
            raise ValueError(f"{name} has repeated consecutive points")
    area = _signed_area(loop)
    if abs(area) <= scale*scale*1e-9:
        raise ValueError(f"{name} has no area")
    eps = scale*scale*1e-12
    for i in range(n):
        for j in range(i+1, n):
            if j == i+1 or (i == 0 and j == n-1):
                continue
            if _segments_touch(loop[i], loop[(i+1) % n], loop[j], loop[(j+1) % n], eps):
                raise ValueError(f"{name} intersects itself")
    return loop, area


def _check_holes(outline, holes, eps):
    def edges(loop):
        return [(loop[i], loop[(i+1) % len(loop)]) for i in range(len(loop))]
    loops = [("outline", outline)]+[(f"hole {i}", h) for i, h in enumerate(holes)]
    for a in range(len(loops)):
        for b in range(a+1, len(loops)):
            for p, q in edges(loops[a][1]):
                for r, s in edges(loops[b][1]):
                    if _segments_touch(p, q, r, s, eps):
                        raise ValueError(f"{loops[b][0]} touches or crosses {loops[a][0]}")
    for i, hole in enumerate(holes):
        if not _inside(outline, hole[0]):
            raise ValueError(f"hole {i} must lie inside the outline")
        for j, other in enumerate(holes):
            if i != j and _inside(other, hole[0]):
                raise ValueError(f"hole {i} lies inside hole {j}")


# --- triangulation ---------------------------------------------------------

def _bridge_holes(points, outline_ids, hole_ids, eps):
    """Merge each hole into the outline polygon through a visible bridge.

    Returns a vertex-index ring (counter-clockwise, holes clockwise) in which
    each bridge's endpoints appear twice. Candidate bridges are tried by
    increasing length; one is valid if it crosses no loop edge or earlier
    bridge and lies in the material.
    """
    polygon = list(outline_ids)
    loop_edges = []
    for ids in [outline_ids]+list(hole_ids):
        loop_edges.extend((ids[i], ids[(i+1) % len(ids)]) for i in range(len(ids)))
    outline_pts = [points[i] for i in outline_ids]
    hole_pts = [[points[i] for i in ids] for ids in hole_ids]
    used = set()
    bridges = []
    for ids in sorted(hole_ids, key=lambda ids: -max(points[i][0] for i in ids)):
        candidates = sorted(((math.dist(points[h], points[p]), h, p) for h in ids for p in polygon
                             if h not in used and p not in used), key=lambda item: item[0])
        chosen = None
        for _, h, p in candidates:
            a, b = points[h], points[p]
            mid = ((a[0]+b[0])/2, (a[1]+b[1])/2)
            if not _inside(outline_pts, mid) or any(_inside(hp, mid) for hp in hole_pts):
                continue
            if any(_segments_touch(a, b, points[u], points[v], eps) for u, v in loop_edges+bridges
                   if h not in (u, v) and p not in (u, v)):
                continue
            chosen = (h, p)
            break
        if chosen is None:
            raise ValueError("Could not connect a hole to the outline")
        h, p = chosen
        used.update(chosen)
        bridges.append((h, p))
        at = polygon.index(p)
        start = ids.index(h)
        ring = ids[start:]+ids[:start]
        polygon = polygon[:at+1]+ring+[h, p]+polygon[at+1:]
    return polygon


def _ear_clip(points, ring, eps):
    """Triangulate a counter-clockwise ring of vertex indices (may repeat indices)."""
    ring = list(ring)
    triangles = []
    strict = False
    while len(ring) > 3:
        n = len(ring)
        for k in range(n):
            ia, ib, ic = ring[k-1], ring[k], ring[(k+1) % n]
            a, b, c = points[ia], points[ib], points[ic]
            if _orient(a, b, c) <= eps:
                continue
            blocked = False
            for other in ring:
                if other in (ia, ib, ic):
                    continue
                p = points[other]
                low = eps if strict else -eps
                if _orient(a, b, p) > low and _orient(b, c, p) > low and _orient(c, a, p) > low:
                    blocked = True
                    break
            if blocked:
                continue
            triangles.append((ia, ib, ic))
            del ring[k]
            strict = False
            break
        else:
            if strict:
                raise ValueError("Could not triangulate the outline")
            strict = True
    a, b, c = (points[i] for i in ring)
    if _orient(a, b, c) <= eps:
        raise ValueError("Could not triangulate the outline")
    triangles.append(tuple(ring))
    return triangles


def extruded_outline(outline, holes=(), thickness=0.001, z0=0.0):
    """Prism of a planar outline with optional holes, from z0 to z0 + thickness.

    outline is a list of (x, y) points (a clockwise outline is normalised to
    counter-clockwise); holes are lists of points strictly inside the outline
    that neither touch nor overlap each other (either winding is accepted).
    Violations raise ValueError. Caps are ear-clipped after bridging each hole
    into the outline; wall quads are two triangles with outward normals (hole
    walls face into the hole). The mesh is closed, manifold and shares vertices
    between caps and walls: 2 * N vertices for N outline+hole points.
    """
    thickness = _positive(thickness, "thickness")
    z0 = _finite(z0, "z0")
    outline, area = _loop(outline, "outline")
    if area < 0:
        outline.reverse()
    try:
        hole_list = list(holes)
    except TypeError as exc:
        raise ValueError("holes must be a list of point lists") from exc
    loops = []
    for i, hole in enumerate(hole_list):
        loop, hole_area = _loop(hole, f"hole {i}")
        if hole_area > 0:
            loop.reverse()
        loops.append(loop)
    scale = max(max(p[k] for p in outline)-min(p[k] for p in outline) for k in range(2))
    eps = scale*scale*1e-12
    _check_holes(outline, loops, eps)

    points = list(outline)
    outline_ids = list(range(len(outline)))
    hole_ids = []
    for loop in loops:
        hole_ids.append(list(range(len(points), len(points)+len(loop))))
        points.extend(loop)
    count = len(points)
    ring = _bridge_holes(points, outline_ids, hole_ids, eps) if loops else outline_ids
    cap = _ear_clip(points, ring, scale*scale*1e-10)

    vertices = [(x, y, z0) for x, y in points]+[(x, y, z0+thickness) for x, y in points]
    faces = [(a+count, b+count, c+count) for a, b, c in cap]
    faces.extend((c, b, a) for a, b, c in cap)
    for ids in [outline_ids]+hole_ids:
        for k, i in enumerate(ids):
            j = ids[(k+1) % len(ids)]
            faces.append((i, j, j+count))
            faces.append((i, j+count, i+count))
    return MeshData(tuple(vertices), tuple(faces))


def _point_segment(p, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    t = max(0.0, min(1.0, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy)))
    return math.hypot(p[0]-a[0]-t*dx, p[1]-a[1]-t*dy)


def _subdivided(loop, spacing, holes=()):
    """Insert collinear points so no edge of the closed loop is longer than spacing.

    Each edge is first cut into equal pieces of at most ``spacing``; a piece is then
    halved while it is longer than three times its distance to the nearest hole edge,
    so a hole close to the outline meets short outline edges (no thin slivers there).
    """
    hole_edges = [(h[i], h[(i+1) % len(h)]) for h in holes for i in range(len(h))]

    def gap(a, b):
        return min((min(_point_segment(a, c, d), _point_segment(b, c, d), _point_segment(c, a, b), _point_segment(d, a, b))
                    for c, d in hole_edges), default=math.inf)

    def split(a, b, out, depth=0):
        if depth < 12 and math.dist(a, b) > 3*gap(a, b):
            m = ((a[0]+b[0])/2, (a[1]+b[1])/2)
            split(a, m, out, depth+1)
            split(m, b, out, depth+1)
        else:
            out.append(a)

    result = []
    for i, (x0, y0) in enumerate(loop):
        x1, y1 = loop[(i+1) % len(loop)]
        pieces = max(1, math.ceil(math.hypot(x1-x0, y1-y0)/spacing-1e-9))
        points = [(x0+(x1-x0)*k/pieces, y0+(y1-y0)*k/pieces) for k in range(pieces)]+[(x1, y1)]
        for a, b in zip(points, points[1:]):
            split(a, b, result)
    return result


def refined_plate(outline, holes=(), thickness=0.001, z0=0.0, spacing=None):
    """``extruded_outline`` with well-shaped caps (same inputs, walls and volume).

    The ear-clipped caps of ``extruded_outline`` can hold long sliver triangles
    (0.007 degrees on a 52 x 42 mm board). Here the caps are re-triangulated by
    Lawson edge flips (constrained Delaunay: boundary edges never flip). With
    ``spacing`` (metres) the outline (not the holes) is also subdivided to that
    edge length, and further near a hole (an outline edge is at most three times
    its distance to the nearest hole edge), and interior Steiner points are added
    on a hex grid, keeping 0.6 * spacing away from every loop, so the caps become
    near-equilateral instead of long fans. Hole outlines are kept exactly.
    Validation and errors are those of ``extruded_outline``; spacing must be
    finite and positive. Steiner insertion is O(points x triangles): meant for
    hundreds of points.
    """
    if spacing is not None:
        spacing = _positive(spacing, "spacing")
    outline, holes = list(outline), [list(h) for h in holes]
    extruded_outline(outline, holes, thickness=thickness, z0=z0)   # validate the inputs as given
    if spacing:
        outline = _subdivided([_point2(p, "outline point") for p in outline], spacing,
                              [[_point2(p, "hole point") for p in h] for h in holes])
    mesh = extruded_outline(outline, holes, thickness=thickness, z0=z0)
    n = len(mesh.vertices)//2
    bottom_z, top_z = mesh.vertices[0][2], mesh.vertices[n][2]
    tris = [tuple(i-n for i in f) for f in mesh.faces if min(f) >= n]
    walls = [f for f in mesh.faces if min(f) < n <= max(f)]
    pts = [v[:2] for v in mesh.vertices[:n]]
    loops = [list(outline)]+holes
    scale = max(max(p[k] for p in pts)-min(p[k] for p in pts) for k in (0, 1))

    def orient(a, b, c):
        return (pts[b][0]-pts[a][0])*(pts[c][1]-pts[a][1])-(pts[b][1]-pts[a][1])*(pts[c][0]-pts[a][0])

    def incircle(a, b, c, d):
        rows = []
        for q in (a, b, c):
            dx, dy = pts[q][0]-pts[d][0], pts[q][1]-pts[d][1]
            rows.append((dx, dy, dx*dx+dy*dy))
        (a1, a2, a3), (b1, b2, b3), (c1, c2, c3) = rows
        return a1*(b2*c3-b3*c2)-a2*(b1*c3-b3*c1)+a3*(b1*c2-b2*c1)

    if spacing:
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        rows = int((max(ys)-min(ys))/(spacing*0.866))+1
        for r in range(rows):
            y = min(ys)+spacing*0.866*(r+0.5)
            k = 0
            while True:
                # Tiny deterministic jitter keeps grid points off exact cocircular configurations.
                x = min(xs)+spacing*(k+0.5*(r % 2)+0.25)+1.37e-5*((7*r+3*k) % 11)
                k += 1
                if x > max(xs):
                    break
                p = (x, y+0.91e-5*((5*r+k) % 13))
                if any(_point_segment(p, lp[i], lp[(i+1) % len(lp)]) < 0.6*spacing for lp in loops for i in range(len(lp))):
                    continue
                for t, (ia, ib, ic) in enumerate(tris):
                    pts.append(p)
                    s = len(pts)-1
                    o = (orient(ia, ib, s), orient(ib, ic, s), orient(ic, ia, s))
                    if min(o) > scale**2*1e-12:
                        tris[t:t+1] = [(ia, ib, s), (ib, ic, s), (ic, ia, s)]
                        break
                    pts.pop()

    eps_o, eps_c = scale**2*1e-9, scale**4*1e-12
    for _ in range(200):
        edges = {}
        for t, tri in enumerate(tris):
            for k in range(3):
                edges[(tri[k], tri[(k+1) % 3])] = t
        flipped = False
        for (u, v), t1 in list(edges.items()):
            t2 = edges.get((v, u))
            if t2 is None:
                continue   # boundary edge: constrained
            tri1, tri2 = tris[t1], tris[t2]
            if not any((tri1[k], tri1[(k+1) % 3]) == (u, v) for k in range(3)) or not any((tri2[k], tri2[(k+1) % 3]) == (v, u) for k in range(3)):
                continue   # stale after an earlier flip in this pass
            p = next(i for i in tri1 if i not in (u, v))
            q = next(i for i in tri2 if i not in (u, v))
            ou, ov = orient(p, q, u), orient(p, q, v)
            if ou*ov >= 0 or abs(ou) < eps_o or abs(ov) < eps_o:
                continue   # quad not strictly convex: the diagonal cannot flip
            if incircle(u, v, p, q) > eps_c:
                tris[t1], tris[t2] = (u, q, p), (q, v, p)
                flipped = True
        if not flipped:
            break
    # Vertex layout: bottom (n loop points + Steiner points), then top (the same again).
    total = len(pts)
    vertices = [(x, y, bottom_z) for x, y in pts]+[(x, y, top_z) for x, y in pts]
    remap = lambda i: i if i < n else i-n+total
    faces = [tuple(remap(i) for i in f) for f in walls]
    faces += [tuple(i+total for i in t) for t in tris]+[(c, b, a) for a, b, c in tris]
    return MeshData(tuple(vertices), tuple(faces))


# --- boxes and cylinders ---------------------------------------------------

def rounded_box(size, radius, center=(0, 0, 0), segments=3):
    """Box with every edge and corner rounded by radius (0 gives a 12-triangle box).

    A subdivided cube surface whose vertices are clamped to the inner box and
    pushed out by radius along the offset direction, so vertices lie exactly on
    the rounded solid (inscribed; the volume is slightly below the analytic
    one). radius must be < min(size)/2; ``segments`` subdivides each quarter
    arc and is ignored when radius is 0.
    """
    size = _vector(size, "size", True)
    radius = _nonnegative(radius, "radius")
    if radius >= min(size)/2:
        raise ValueError("radius must be < min(size)/2")
    center = _vector(center, "center")
    _count(segments, 1, "segments")
    nodes = []
    for h in (s/2 for s in size):
        inner = h-radius
        if radius == 0:
            nodes.append([(-h, -h), (h, h)])
            continue
        low = [(-h+radius*k/segments, -inner) for k in range(segments+1)]
        high = [(inner+radius*k/segments, inner) for k in range(segments+1)]
        nodes.append(low+high)
    index, vertices = {}, []

    def vertex(i, j, k):
        key = (i, j, k)
        if key not in index:
            picks = [nodes[0][i], nodes[1][j], nodes[2][k]]
            if radius == 0:
                point = tuple(pick[0] for pick in picks)
            else:
                offset = [pick[0]-pick[1] for pick in picks]
                length = math.sqrt(sum(o*o for o in offset))
                point = tuple(pick[1]+radius*o/length for pick, o in zip(picks, offset))
            index[key] = len(vertices)
            vertices.append(tuple(c+p for c, p in zip(center, point)))
        return index[key]

    faces = []
    for axis in range(3):
        b_axis, c_axis = (axis+1) % 3, (axis+2) % 3
        for sign, end in ((1, len(nodes[axis])-1), (-1, 0)):
            for ib in range(len(nodes[b_axis])-1):
                for ic in range(len(nodes[c_axis])-1):
                    def at(db, dc):
                        ids = [0, 0, 0]
                        ids[axis], ids[b_axis], ids[c_axis] = end, ib+db, ic+dc
                        return vertex(*ids)
                    p00, p10, p11, p01 = at(0, 0), at(1, 0), at(1, 1), at(0, 1)
                    if sign > 0:
                        faces.extend(((p00, p10, p11), (p00, p11, p01)))
                    else:
                        faces.extend(((p00, p11, p10), (p00, p01, p11)))
    return MeshData(tuple(vertices), tuple(faces))


def cylinder(radius, height, center=(0, 0, 0), segments=24):
    """Closed cylinder along Z centred on center: 4 * segments triangles.

    Each cap is a fan around its centre vertex; sides are 2 * segments
    triangles. Vertices lie on the circumscribed circle of the regular polygon.
    """
    radius, height = _positive(radius, "radius"), _positive(height, "height")
    center = _vector(center, "center")
    _count(segments, 3, "segments")
    cx, cy, cz = center
    lo, hi = cz-height/2, cz+height/2
    ring = [(cx+radius*math.cos(math.tau*i/segments), cy+radius*math.sin(math.tau*i/segments))
            for i in range(segments)]
    vertices = [(x, y, lo) for x, y in ring]+[(x, y, hi) for x, y in ring]+[(cx, cy, lo), (cx, cy, hi)]
    bottom, top = 2*segments, 2*segments+1
    faces = []
    for i in range(segments):
        j = (i+1) % segments
        faces.append((bottom, j, i))
        faces.append((top, segments+i, segments+j))
        faces.append((i, j, segments+j))
        faces.append((i, segments+j, segments+i))
    return MeshData(tuple(vertices), tuple(faces))
