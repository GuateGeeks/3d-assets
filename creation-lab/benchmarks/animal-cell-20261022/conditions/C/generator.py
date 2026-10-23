"""Célula animal abierta: geometría procedural original para el benchmark.

El runner común llama build(); este módulo no guarda ni exporta archivos.
"""

import math
import random

import bpy
from mathutils import Vector


SEED = 20261022
TAU = 2.0 * math.pi


def build():
    rng = random.Random(SEED)
    materials = {}

    def material(key, color, roughness=0.42):
        mat = bpy.data.materials.new(key)
        mat.use_nodes = True
        mat.diffuse_color = (*color, 1.0)
        shader = mat.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (*color, 1.0)
        shader.inputs['Roughness'].default_value = roughness
        shader.inputs['Metallic'].default_value = 0.0
        materials[key] = mat
        return mat

    membrane = material('Membrana | azul petróleo', (0.055, 0.32, 0.36))
    membrane_inner = material('Membrana | canto agua', (0.18, 0.58, 0.57))
    cytosol = material('Citosol | marfil frío', (0.73, 0.84, 0.79), 0.61)
    nuclear_outer = material('Envoltura nuclear | ciruela', (0.32, 0.17, 0.48))
    nuclear_inner = material('Envoltura nuclear | lavanda', (0.63, 0.45, 0.76))
    nucleoplasm = material('Nucleoplasma | lila pálido', (0.74, 0.62, 0.82), 0.58)
    nucleolus_mat = material('Nucléolo | frambuesa', (0.63, 0.12, 0.33), 0.39)
    ribosome_mat = material('Ribosomas | tinta', (0.095, 0.07, 0.19))
    rer_mat = material('Retículo rugoso | violeta', (0.48, 0.30, 0.66))
    rel_mat = material('Retículo liso | turquesa', (0.035, 0.52, 0.54))
    golgi_mat = material('Golgi | ocre dorado', (0.94, 0.51, 0.105))
    golgi_light = material('Golgi | borde miel', (1.0, 0.65, 0.20))
    mito_outer = material('Mitocondria | terracota', (0.76, 0.22, 0.135))
    mito_inner = material('Mitocondria | interior salmón', (1.0, 0.57, 0.34))
    mito_matrix = material('Matriz mitocondrial | melocotón', (0.98, 0.72, 0.46), 0.55)
    crista_mat = material('Crestas | rojo coral', (0.76, 0.13, 0.095))
    lysosome_mat = material('Lisosomas | verde oliva', (0.39, 0.58, 0.14))
    lysosome_core = material('Carga lisosomal | lima', (0.67, 0.77, 0.30))
    centriole_mat = material('Centríolos | azul profundo', (0.11, 0.39, 0.66))
    vesicle_mat = material('Vesículas | ámbar claro', (0.98, 0.72, 0.34))
    filament_mat = material('Citoesqueleto | salvia', (0.27, 0.45, 0.38), 0.6)

    def mesh_object(name, part, vertices, faces, mats, face_materials=None):
        mesh = bpy.data.meshes.new(name + '__mesh')
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(part + '__' + name, mesh)
        bpy.context.collection.objects.link(obj)
        obj['part_id'] = part
        for mat in mats:
            mesh.materials.append(mat)
        for index, polygon in enumerate(mesh.polygons):
            polygon.use_smooth = True
            if face_materials is not None:
                polygon.material_index = face_materials[index]
        return obj

    def ellipsoid(name, part, center, radius, mat, segments=24, rings=12):
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=segments, ring_count=rings, radius=1.0, location=center)
        obj = bpy.context.object
        obj.name = part + '__' + name
        # Bake scale into the mesh so every exported object has unit scale.
        for vertex in obj.data.vertices:
            vertex.co.x *= radius[0]
            vertex.co.y *= radius[1]
            vertex.co.z *= radius[2]
        obj.data.materials.append(mat)
        obj['part_id'] = part
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        return obj

    def bead(name, part, position, radius, mat, subdivision=1):
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=subdivision, radius=radius, location=position)
        obj = bpy.context.object
        obj.name = part + '__' + name
        obj['part_id'] = part
        obj.data.materials.append(mat)
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        return obj

    def smooth_points(points, steps=5):
        p = [Vector(v) for v in points]
        result = []
        for i in range(len(p) - 1):
            a, b = p[max(0, i - 1)], p[i]
            c, d = p[i + 1], p[min(len(p) - 1, i + 2)]
            for j in range(steps):
                t = j / steps
                result.append(0.5 * ((2 * b) + (-a + c) * t
                    + (2 * a - 5 * b + 4 * c - d) * t * t
                    + (-a + 3 * b - 3 * c + d) * t * t * t))
        result.append(p[-1])
        return result

    def tube(name, part, points, radius, mat, sides=8, smooth=True):
        path = smooth_points(points) if smooth else [Vector(p) for p in points]
        vertices, faces = [], []
        previous = None
        for i, p in enumerate(path):
            tangent = (path[min(i + 1, len(path) - 1)]
                       - path[max(0, i - 1)]).normalized()
            reference = Vector((0, 0, 1))
            if abs(tangent.dot(reference)) > 0.94:
                reference = Vector((0, 1, 0))
            normal = tangent.cross(reference).normalized()
            if previous is not None and normal.dot(previous) < 0:
                normal = -normal
            previous = normal
            binormal = tangent.cross(normal).normalized()
            for j in range(sides):
                angle = TAU * j / sides
                vertices.append(p + radius * (math.cos(angle) * normal
                                               + math.sin(angle) * binormal))
        for i in range(len(path) - 1):
            for j in range(sides):
                k = (j + 1) % sides
                faces.append((i * sides + j, i * sides + k,
                              (i + 1) * sides + k, (i + 1) * sides + j))
        faces.append(tuple(reversed(range(sides))))
        faces.append(tuple((len(path) - 1) * sides + j for j in range(sides)))
        return mesh_object(name, part, vertices, faces, [mat])

    def shell(name, part, center, radius, thickness, cutoff, outer, inner,
              segments=64, rings=20, holes=(), rotate=0.0):
        """Double surface with an actual open rim, and optional actual pores."""
        vertices, faces, indices = [], [], []
        ca, sa = math.cos(rotate), math.sin(rotate)
        def world(x, y, z):
            return (center[0] + ca*x - sa*y,
                    center[1] + sa*x + ca*y, center[2] + z)
        for layer in range(2):
            radii = [r - layer * thickness for r in radius]
            for i in range(rings + 1):
                for j in range(segments):
                    phi = TAU * j / segments
                    theta = 0.001 + (cutoff(phi) - 0.001) * i / rings
                    vertices.append(world(radii[0] * math.sin(theta) * math.cos(phi),
                                          radii[1] * math.sin(theta) * math.sin(phi),
                                          -radii[2] * math.cos(theta)))
        stride = (rings + 1) * segments
        edge_counts = {}
        for i in range(rings):
            for j in range(segments):
                if any(i in (hi, hi + 1) and j in (hj, hj + 1)
                       for hi, hj in holes):
                    continue
                k = (j + 1) % segments
                face = (i * segments + j, i * segments + k,
                        (i + 1) * segments + k, (i + 1) * segments + j)
                faces.append(face)
                indices.append(0)
                faces.append(tuple(v + stride for v in reversed(face)))
                indices.append(1)
                for a, b in zip(face, face[1:] + face[:1]):
                    key = tuple(sorted((a, b)))
                    if key in edge_counts:
                        edge_counts[key] = None
                    else:
                        edge_counts[key] = (a, b)
        for edge in edge_counts.values():
            if edge is not None:
                a, b = edge
                faces.append((b, a, a + stride, b + stride))
                indices.append(1)
        return mesh_object(name, part, vertices, faces, [outer, inner], indices)

    def flattened_sac(name, part, path, width, height, mat, sides=10):
        """A closed, flattened cisterna; tapered rounded termini."""
        vertices, faces = [], []
        path = [Vector(p) for p in path]
        for i, p in enumerate(path):
            tangent = (path[min(i+1, len(path)-1)] - path[max(0, i-1)]).normalized()
            normal = Vector((-tangent.y, tangent.x, 0)).normalized()
            taper = 0.16 + 0.84 * math.sin(math.pi * i / (len(path)-1)) ** 0.30
            for j in range(sides):
                a = TAU * j / sides
                vertices.append(p + normal * (width * math.cos(a) * taper)
                                + Vector((0, 0, height * math.sin(a) * taper)))
        for i in range(len(path)-1):
            for j in range(sides):
                k = (j+1) % sides
                faces.append((i*sides+j, i*sides+k, (i+1)*sides+k, (i+1)*sides+j))
        faces.append(tuple(reversed(range(sides))))
        faces.append(tuple((len(path)-1)*sides+j for j in range(sides)))
        return mesh_object(name, part, vertices, faces, [mat])

    # A thin, visibly cut envelope; the lip is low at -Y and tall at +Y.
    shell('envoltura_abierta', 'membrana', (0, 0, 0.010),
          (0.150, 0.115, 0.085), 0.0020,
          lambda phi: 1.52 + 0.48 * math.sin(phi), membrane, membrane_inner)
    ellipsoid('citosol_palido', 'citoplasma', (0, 0, -0.052),
              (0.141, 0.105, 0.021), cytosol, 64, 20)

    # Nuclear envelope retains its lower and posterior portions. Pores are holes,
    # not painted dots. Nucleolus is an unwrapped body inside the opening.
    nc = (-0.031, 0.009, -0.003)
    shell('envoltura_con_poros', 'nucleo', nc, (0.044, 0.039, 0.040), 0.0012,
          lambda phi: 1.67 + 0.45 * math.sin(phi), nuclear_outer, nuclear_inner,
          segments=56, rings=18,
          holes=((11, 4), (13, 12), (11, 21), (10, 29), (12, 42), (11, 49)))
    ellipsoid('nucleoplasma_expuesto', 'nucleo', (-0.031, 0.009, -0.028),
              (0.0385, 0.0335, 0.010), nucleoplasm, 32, 14)
    ellipsoid('cuerpo_sin_membrana', 'nucleolo', (-0.031, 0.003, -0.001),
              (0.0128, 0.0117, 0.0121), nucleolus_mat, 28, 16)

    # Three broad RER cisternae lie around the posterior half of the nucleus.
    for level in range(3):
        z = 0.003 + level * 0.010
        rad = 0.053 + 0.002 * level
        points = []
        for j in range(33):
            angle = 0.56 + 2.64 * j/32
            points.append((nc[0] + rad*math.cos(angle),
                           nc[1] + rad*0.87*math.sin(angle),
                           z + 0.0015*math.sin(angle*2)))
        flattened_sac('cisterna_%02d' % (level+1), 'rer', points,
                      0.0064, 0.0018, rer_mat)
        for j in range(13):
            angle = 0.69 + 2.34*j/12
            for row in range(2):
                r = rad + (row - 0.5)*0.006
                pos = (nc[0]+r*math.cos(angle), nc[1]+rad*0.87*math.sin(angle)
                       +(row-0.5)*0.006*math.sin(angle),
                       z+0.0015*math.sin(angle*2)+0.0030)
                bead('adherido_%02d_%02d_%d' % (level, j, row),
                     'ribosomas', pos, 0.00125, ribosome_mat)

    # A connected smooth ER network with no ribosomal granules.
    rel_paths = [
        [(0.027,0.023,0.008),(0.040,0.009,0.014),(0.058,0.015,0.018),
         (0.073,0.005,0.019),(0.093,0.014,0.015)],
        [(0.036,0.031,0.013),(0.049,0.027,0.021),(0.066,0.034,0.023),
         (0.083,0.025,0.021),(0.103,0.032,0.015)],
        [(0.058,0.015,0.018),(0.058,0.025,0.025),(0.066,0.034,0.023)],
        [(0.073,0.005,0.019),(0.085,-0.007,0.016),(0.103,0.001,0.009),
         (0.110,0.017,0.010),(0.103,0.032,0.015)],
        [(0.040,0.009,0.014),(0.048,-0.006,0.009),(0.061,-0.009,0.013),
         (0.073,0.005,0.019)],
        [(0.083,0.025,0.021),(0.085,0.015,0.023),(0.093,0.014,0.015)],
    ]
    for i, path in enumerate(rel_paths):
        tube('tubulo_%02d' % i, 'rel', path, 0.0022, rel_mat, sides=10)

    # A compact Golgi stack in the foreground: each cisterna is a shallow curve.
    for level in range(5):
        half_length = 0.026 - abs(level-2)*0.002
        points = []
        for j in range(25):
            t = -1 + 2*j/24
            points.append((0.059 + half_length*t,
                           -0.049 + 0.009*t*t + level*0.0012,
                           -0.018 + level*0.0060 + 0.002*t*t))
        flattened_sac('cisterna_apilada_%02d' % level, 'golgi', points,
                      0.0052, 0.00155, golgi_mat if level%2 == 0 else golgi_light)
    for i, (position, radius) in enumerate([
            ((0.091,-0.035,-0.006),0.0044), ((0.093,-0.051,-0.014),0.0039),
            ((0.078,-0.067,-0.022),0.0034), ((0.027,-0.049,-0.013),0.0040),
            ((0.103,-0.025,-0.014),0.0032)]):
        ellipsoid('transporte_%02d' % i, 'vesiculas', position,
                  (radius,radius,radius), vesicle_mat, 16, 8)

    def mitochondrion(index, center, angle, length):
        ca, sa = math.cos(angle), math.sin(angle)
        def to_world(p):
            return (center[0]+ca*p[0]-sa*p[1],
                    center[1]+sa*p[0]+ca*p[1], center[2]+p[2])
        shell('envoltura_abierta_%02d' % index, 'mitocondrias', center,
              (length,0.014,0.013), 0.0013,
              lambda phi: math.pi/2 + 0.12*math.sin(phi),
              mito_outer, mito_inner, segments=40, rings=12, rotate=angle)
        obj = ellipsoid('matriz_%02d' % index, 'mitocondrias',
                        to_world((0,0,-0.0075)), (length*0.86,0.0113,0.003),
                        mito_matrix,24,10)
        obj.rotation_euler.z = angle
        # Broad internal folded membrane plates rise from the exposed matrix.
        for crease in range(5):
            xbase = (crease-2)*length*0.29
            extent = 0.0102*math.sqrt(max(0.1,1-(xbase/length)**2))
            vertices, faces = [], []
            n = 14
            for side in (-1,1):
                for j in range(n+1):
                    t = -1+2*j/n
                    x = xbase + 0.0014*math.sin(math.pi*t) + side*0.00065
                    y = extent*t
                    top = -0.0045 + 0.0085*(1-t*t)
                    vertices.append(to_world((x,y,-0.0080)))
                    vertices.append(to_world((x,y,top)))
            offset = 2*(n+1)
            for j in range(n):
                a, b = 2*j, 2*(j+1)
                faces.extend([(a,b,b+1,a+1),
                              (a+offset+1,b+offset+1,b+offset,a+offset),
                              (a+1,b+1,b+offset+1,a+offset+1),
                              (a+offset,b+offset,b,a)])
            faces.extend([(0,1,offset+1,offset),
                          (2*n+1,2*n,offset+2*n,offset+2*n+1)])
            mesh_object('cresta_%02d_%02d' % (index,crease), 'mitocondrias',
                        vertices,[tuple(reversed(face)) for face in faces],[crista_mat])
    mitochondrion(1,(-0.079,-0.052,-0.018),-0.38,0.028)
    mitochondrion(2,(0.064,0.067,-0.005),0.39,0.025)

    # Lysosomes are discrete olive bodies; one is opened to expose granular cargo.
    ellipsoid('cuerpo_01','lisosomas',(-0.112,0.006,-0.020),
              (0.0080,0.0075,0.0084),lysosome_mat,20,12)
    shell('cuerpo_abierto_02','lisosomas',(0.007,-0.079,-0.024),
          (0.0082,0.0078,0.0082),0.0010,lambda phi: 1.7,
          lysosome_mat,lysosome_core,segments=24,rings=8)
    for i, offset in enumerate([(-0.003,0,-0.001),(0.002,-0.002,-0.002),
                                 (0.002,0.003,-0.001),(0,-0.001,0.002)]):
        bead('contenido_%02d'%i,'lisosomas',
             (0.007+offset[0],-0.079+offset[1],-0.024+offset[2]),
             0.0020,lysosome_core,2)

    # One orthogonal pair of centrioles, each drawn as nine microtubule triplets.
    # The open ends retain a visible lumen; there is no solid central cylinder.
    centriole_centers = [Vector((-0.004,-0.041,-0.014)),
                        Vector((0.012,-0.034,-0.019))]
    for ci in range(2):
        axis = Vector((0,0,1)) if ci == 0 else Vector((1,0,0))
        u = Vector((1,0,0)) if ci == 0 else Vector((0,1,0))
        v = axis.cross(u)
        for group in range(9):
            angle = TAU*group/9
            radial = math.cos(angle)*u + math.sin(angle)*v
            tangential = -math.sin(angle)*u + math.cos(angle)*v
            for sub in range(3):
                offset = radial*0.0041 + tangential*(sub-1)*0.00105
                midpoint = centriole_centers[ci]+offset
                tube('centríolo_%d_triplete_%d_tubo_%d'%(ci+1,group+1,sub+1),
                     'centrosoma',[midpoint-axis*0.0095,midpoint+axis*0.0095],
                     0.00068,centriole_mat,sides=6,smooth=False)

    # Sparse tracks pass below and between organelles, with distinct orientations.
    tracks = [
        [(-0.125,-0.015,-0.036),(-0.112,-0.040,-0.033),(-0.100,-0.071,-0.034),
         (-0.069,-0.085,-0.034),(-0.038,-0.082,-0.033)],
        [(-0.108,0.039,-0.033),(-0.093,0.065,-0.026),(-0.068,0.086,-0.023),
         (-0.031,0.094,-0.024),(0.006,0.093,-0.028)],
        [(-0.049,-0.084,-0.032),(-0.030,-0.062,-0.029),(-0.015,-0.049,-0.027),
         (0.010,-0.018,-0.029),(0.032,0.002,-0.028),(0.045,0.032,-0.028)],
        [(0.038,-0.078,-0.032),(0.061,-0.075,-0.033),(0.096,-0.061,-0.033),
         (0.115,-0.034,-0.031),(0.127,-0.008,-0.031)],
        [(0.016,0.078,-0.027),(0.031,0.063,-0.025),(0.048,0.047,-0.025),
         (0.075,0.043,-0.025),(0.103,0.050,-0.027)],
    ]
    for i,path in enumerate(tracks):
        tube('filamento_%02d'%i,'citoesqueleto',path,0.0007,filament_mat,sides=6)

    # Free ribosomes form small local groups; all use the same material as RER beads.
    ribosome_anchor = None
    for group,(cx,cy,cz) in enumerate([(-0.045,-0.054,-0.026),
                                      (0.027,-0.006,-0.024),
                                      (-0.110,-0.024,-0.030)]):
        for i in range(7):
            angle = rng.uniform(0,TAU)
            radius = rng.uniform(0.002,0.008)
            position = (cx+radius*math.cos(angle),cy+radius*math.sin(angle),
                        cz+rng.uniform(0,0.0025))
            bead('libre_%d_%02d'%(group,i),'ribosomas',position,0.00135,ribosome_mat)
            if ribosome_anchor is None:
                ribosome_anchor = [position[0],position[1],position[2]+0.0012]

    return {
        'title': 'Célula animal · interior abierto',
        'design_notes': (
            'Maqueta original con membrana fina en cuenco, baja hacia el frente −Y y '
            'abierta por arriba. El citosol marfil da contraste al interior. El núcleo '
            'tiene envoltura parcial con poros geométricos, nucleoplasma y un nucléolo '
            'sin membrana. El RER violeta lleva ribosomas oscuros sobre tres cisternas '
            'próximas al núcleo; el REL turquesa forma tubos conectados. El Golgi ocre '
            'apila cinco cisternas curvas con vesículas próximas. Dos mitocondrias '
            'terracota abiertas muestran matriz y crestas como láminas internas. Un '
            'par perpendicular de centríolos presenta nueve tripletes por cilindro; '
            'filamentos escasos recorren el citosol en direcciones diversas. Colores, '
            'cantidades y tamaños son convenciones didácticas para secundaria; '
            'maqueta ampliada, no escala microscópica exacta.'),
        'parts': {
            'membrana': {'label_position': [0.102, -0.072, -0.021]},
            'citoplasma': {'label_position': [0.107, -0.006, -0.0384]},
            'nucleo': {'label_position': [-0.0724, -0.0040, -0.0051]},
            'nucleolo': {'label_position': [-0.027, -0.002, 0.0093]},
            'ribosomas': {'label_position': ribosome_anchor},
            'rer': {'label_position': [-0.059, 0.050, 0.024]},
            'rel': {'label_position': [0.073, 0.005, 0.0212]},
            'golgi': {'label_position': [0.059, -0.0442, 0.00755]},
            'mitocondrias': {'label_position': [-0.079, -0.052, -0.014]},
            'lisosomas': {'label_position': [0.007, -0.079, -0.020]},
            'centrosoma': {'label_position': [-0.0006, -0.043, -0.0045]},
            'vesiculas': {'label_position': [0.091, -0.037, -0.0021]},
            'citoesqueleto': {'label_position': [-0.069, -0.085, -0.0333]},
        },
    }
