"""Condición D: maqueta original de célula animal abierta. No ejecuta E/S."""
import bpy
import math
import random
from mathutils import Vector


def build():
    rng = random.Random(20261022)
    pi = math.pi
    mats = {}
    built_meshes = []

    def material(key, color, roughness=0.46):
        m = bpy.data.materials.new(key)
        m.diffuse_color = (*color, 1)
        m.use_nodes = True
        p = m.node_tree.nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value = (*color, 1)
        p.inputs['Roughness'].default_value = roughness
        p.inputs['Metallic'].default_value = 0
        mats[key] = m
        return m

    membrane = material('Membrana • verde petróleo', (0.055, 0.32, 0.33))
    cytosol = material('Citosol • porcelana agua', (0.65, 0.83, 0.76), 0.62)
    nuclear = material('Envoltura nuclear • ciruela', (0.32, 0.16, 0.44))
    nucleoplasm = material('Nucleoplasma • lavanda', (0.66, 0.48, 0.72), 0.6)
    nucleolar = material('Nucléolo • frambuesa', (0.66, 0.13, 0.35))
    chromatin = material('Cromatina • violeta', (0.43, 0.25, 0.53))
    rough_er = material('RER • azul profundo', (0.11, 0.39, 0.63))
    smooth_er = material('REL • azul celeste', (0.25, 0.67, 0.76))
    ribosome = material('Ribosomas • tinta', (0.085, 0.12, 0.23), 0.6)
    golgi_mat = material('Golgi • ocre dorado', (0.95, 0.61, 0.17))
    mito_outer = material('Mitocondria • terracota', (0.78, 0.22, 0.12))
    mito_inner = material('Matriz mitocondrial • melocotón', (0.98, 0.57, 0.30))
    crista_mat = material('Crestas • coral', (0.87, 0.28, 0.18))
    lyso = material('Lisosomas • lima', (0.53, 0.68, 0.15))
    lyso_grain = material('Contenido lisosomal', (0.76, 0.84, 0.33))
    vesicle_mat = material('Vesículas • ámbar claro', (0.97, 0.79, 0.40))
    centriole_mat = material('Centríolos • rosa cobre', (0.73, 0.33, 0.42))
    filament_mat = material('Citoesqueleto • verde salvia', (0.22, 0.49, 0.40))

    def mesh(name, part, verts, faces, mat, extra=None, indices=None):
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        me.update()
        ob = bpy.data.objects.new(part + '__' + name, me)
        bpy.context.collection.objects.link(ob)
        ob['part_id'] = part
        me.materials.append(mat)
        if extra:
            me.materials.append(extra)
        for i, p in enumerate(me.polygons):
            p.use_smooth = True
            if indices:
                p.material_index = indices[i]
        built_meshes.append(me)
        return ob

    def sphere(name, part, center, radius, mat, seg=20, rings=12):
        if isinstance(radius, (float, int)):
            radius = (radius, radius, radius)
        c = Vector(center)
        verts = [tuple(c + Vector((0, 0, radius[2])))]
        for j in range(1, rings):
            t = pi * j / rings
            for i in range(seg):
                a = 2*pi*i/seg
                verts.append(tuple(c + Vector((radius[0]*math.sin(t)*math.cos(a), radius[1]*math.sin(t)*math.sin(a), radius[2]*math.cos(t)))))
        bottom = len(verts)
        verts.append(tuple(c + Vector((0, 0, -radius[2]))))
        faces = []
        for i in range(seg):
            faces.append((0, 1+i, 1+(i+1)%seg))
        for j in range(rings-2):
            a = 1+j*seg
            b = a+seg
            for i in range(seg):
                ni = (i+1)%seg
                faces.append((a+i, b+i, b+ni, a+ni))
        a = 1+(rings-2)*seg
        for i in range(seg):
            faces.append((a+i, bottom, a+(i+1)%seg))
        return mesh(name, part, verts, faces, mat)

    def tube(name, part, points, radius, mat, sides=8, caps=True):
        pts = [Vector(p) for p in points]
        verts = []
        prev_u = None
        for j, p in enumerate(pts):
            t = (pts[min(j+1, len(pts)-1)]-pts[max(j-1, 0)]).normalized()
            if prev_u is None:
                ref = Vector((0, 0, 1)) if abs(t.z)<0.9 else Vector((0, 1, 0))
                u = t.cross(ref).normalized()
            else:
                u = (prev_u-t*prev_u.dot(t)).normalized()
            v = t.cross(u).normalized()
            prev_u = u
            for k in range(sides):
                a = 2*pi*k/sides
                verts.append(tuple(p+radius*(math.cos(a)*u+math.sin(a)*v)))
        faces = []
        for j in range(len(pts)-1):
            for k in range(sides):
                nk=(k+1)%sides
                faces.append((j*sides+k, j*sides+nk, (j+1)*sides+nk, (j+1)*sides+k))
        if caps:
            first_center = len(verts)
            verts.extend((tuple(pts[0]), tuple(pts[-1])))
            last_ring = (len(pts)-1)*sides
            for k in range(sides):
                nk = (k+1)%sides
                faces.append((first_center, nk, k))
                faces.append((first_center+1, last_ring+k, last_ring+nk))
        return mesh(name, part, verts, faces, mat)

    def bowl(name, part, center, radii, thickness, mat, inner_mat=None,
             axis=(0, 0, 1), opening=1.35, seg=64, rows=20):
        # Closed thin shell: outer surface, inner surface, and an actual cut rim.
        n = Vector(axis).normalized()
        ref = Vector((1, 0, 0)) if abs(n.x)<0.9 else Vector((0, 1, 0))
        u = (ref-n*ref.dot(n)).normalized()
        v = n.cross(u)
        verts=[]
        # One shared pole per layer replaces the collapsed final latitude ring.
        count=rows*seg+1
        for layer in range(2):
            rr=[r-thickness*layer for r in radii]
            for j in range(rows):
                for i in range(seg):
                    a=2*pi*i/seg
                    start=opening(a) if callable(opening) else opening
                    t=start+(pi-start)*j/rows
                    q=math.sin(t)*(math.cos(a)*u+math.sin(a)*v)+math.cos(t)*n
                    verts.append(tuple(Vector(center)+Vector((q.x*rr[0], q.y*rr[1], q.z*rr[2]))))
            verts.append(tuple(Vector(center)-Vector((n.x*rr[0], n.y*rr[1], n.z*rr[2]))))
        faces=[]
        ids=[]
        for layer in range(2):
            off=layer*count
            for j in range(rows-1):
                for i in range(seg):
                    a=off+j*seg+i; b=off+j*seg+(i+1)%seg
                    f=(a, a+seg, b+seg, b)
                    faces.append(f if layer==0 else tuple(reversed(f)))
                    ids.append(layer if inner_mat else 0)
            pole=off+rows*seg
            last_ring=off+(rows-1)*seg
            for i in range(seg):
                f=(last_ring+i, pole, last_ring+(i+1)%seg)
                faces.append(f if layer==0 else tuple(reversed(f)))
                ids.append(layer if inner_mat else 0)
        for i in range(seg):
            k=(i+1)%seg
            faces.append((i, k, count+k, count+i)); ids.append(0)
        return mesh(name, part, verts, faces, mat, inner_mat, ids)

    # The front lip sits lower than the back lip; all organelles can be seen above it.
    rim = lambda a: 1.42 - 0.48*math.sin(a)
    bowl('envoltura_abierta', 'membrana', (0, 0, -0.012), (0.150, 0.122, 0.072), 0.0024, membrane, opening=rim, rows=22)
    bowl('citosol_corte', 'citoplasma', (0, 0, -0.012), (0.1473, 0.1193, 0.0693), 0.0014, cytosol, opening=rim, rows=22)

    nc=(-0.037, 0.024, 0.008)
    bowl('envoltura_con_corte', 'nucleo', nc, (0.043, 0.040, 0.039), 0.0018,
         nuclear, nucleoplasm, axis=(0.15, -0.72, 0.70), opening=1.40, seg=56, rows=18)
    sphere('cuerpo_intranuclear', 'nucleolo', (-0.038, 0.015, 0.011), (0.0124, 0.011, 0.012), nucleolar, 28, 16)
    # Chromatin is represented as loose threads, never condensed X chromosomes.
    for k in range(4):
        pts=[]
        for j in range(15):
            a=2*pi*j/14
            pts.append((nc[0]+0.023*math.cos(a+k*0.6), nc[1]+0.019*math.sin(a), nc[2]-0.017+k*0.004+0.002*math.sin(3*a)))
        tube('cromatina_%02d'%k, 'nucleo', pts, 0.00065, chromatin, 6)
    # Pores on the retained back hemisphere of the nuclear envelope.
    for k in range(8):
        a=0.2+2.6*k/7
        center=Vector((nc[0]+0.039*math.cos(a), nc[1]+0.036*math.sin(a), nc[2]+0.008))
        normal=Vector((math.cos(a), math.sin(a), 0.25)).normalized()
        u=normal.cross(Vector((0,0,1))).normalized(); v=normal.cross(u)
        pts=[tuple(center+0.0021*(math.cos(2*pi*j/12)*u+math.sin(2*pi*j/12)*v)) for j in range(13)]
        tube('poro_%02d'%k, 'nucleo', pts, 0.0006, nucleoplasm, 6)

    def cisterna(name, part, center, length, width, height, bend, mat, n=32):
        # Flattened sealed sack with a curved long axis and rounded transverse profile.
        verts=[]
        for i in range(n+1):
            t=-1+2*i/n
            x=length*t/2
            y=bend*t*t
            taper=0.30+0.70*math.sin(pi*i/n)**0.35
            for j in range(8):
                a=2*pi*j/8
                verts.append((center[0]+x, center[1]+y+width*taper*math.cos(a)/2, center[2]+height*taper*math.sin(a)/2))
        faces=[]
        for i in range(n):
            for j in range(8):
                faces.append((i*8+j, i*8+(j+1)%8, (i+1)*8+(j+1)%8, (i+1)*8+j))
        cap_start = len(verts)
        verts.append((center[0]-length/2, center[1]+bend, center[2]))
        verts.append((center[0]+length/2, center[1]+bend, center[2]))
        for j in range(8):
            nj=(j+1)%8
            faces.append((cap_start, nj, j))
            faces.append((cap_start+1, n*8+j, n*8+nj))
        return mesh(name,part,verts,faces,mat)

    # RER: blue curved cisternae hug the right side of the nucleus.
    for k in range(4):
        z=0.001+k*0.008
        center=(0.008, 0.045+k*0.002, z)
        cisterna('cisterna_rugosa_%02d'%k, 'rer', center, 0.060, 0.009, 0.0037, 0.024, rough_er)
        for j in range(9):
            t=-0.87+1.74*j/8
            pos=(center[0]+0.030*t, center[1]+0.024*t*t-0.0015, z+0.0028)
            sphere('adherido_%02d_%02d'%(k,j), 'ribosomas', pos, 0.00165, ribosome, 10, 6)

    # REL: an interconnected, uncoated tubular network, spatially distinct from RER.
    for k in range(4):
        pts=[]
        for j in range(20):
            t=j/19
            pts.append((0.050+0.036*t, 0.040+0.010*k+0.004*math.sin(t*2*pi), -0.010+0.005*math.sin(t*pi+k)))
        tube('tubulo_liso_%02d'%k, 'rel', pts, 0.0025, smooth_er)
    for k in range(3):
        x=0.056+k*0.011
        tube('conexion_lisa_%02d'%k, 'rel', [(x,0.039,-0.007),(x+0.003,0.052,-0.005),(x-0.002,0.065,-0.011),(x+0.001,0.071,-0.014)],0.0024,smooth_er)

    # Golgi: five golden flattened crescents, gradually narrowing towards the top.
    for k in range(5):
        cisterna('cisterna_golgi_%02d'%k, 'golgi', (0.023,-0.066,-0.025+0.006*k), 0.061-0.004*k, 0.009, 0.0035, 0.014, golgi_mat)
    for k, pos in enumerate([(0.060,-0.062,-0.003),(0.058,-0.079,-0.022),(-0.013,-0.069,-0.012),(0.043,-0.087,-0.032),(0.067,-0.070,-0.017)]):
        sphere('transporte_%02d'%k,'vesiculas',pos,0.0040+(k%2)*0.001,vesicle_mat,16,10)

    # Open mitochondria: the folds stand inside the exposed matrix of each shell.
    for k,(cx,cy,cz,angle) in enumerate([(-0.080,-0.041,-0.014,-0.38),(0.086,-0.004,-0.011,0.85)]):
        ca,sa=math.cos(angle),math.sin(angle)
        def world(p):
            return (cx+ca*p[0]-sa*p[1],cy+sa*p[0]+ca*p[1],cz+p[2])
        ob=bowl('mitocondria_abierta_%02d'%k,'mitocondrias',(0,0,0),(0.031,0.014,0.014),0.0016,mito_outer,mito_inner,opening=1.35,seg=40,rows=12)
        for vertex in ob.data.vertices:
            vertex.co=world(vertex.co)
        for j in range(7):
            x=-0.022+j*0.007
            halfwidth=0.0095*math.sqrt(max(0.1,1-(x/0.030)**2))
            pts=[]
            for q in range(13):
                t=-1+2*q/12
                pts.append(world((x+0.0018*math.sin(t*pi),t*halfwidth,-0.008+0.0085*(1-t*t))))
            tube('cresta_%02d_%02d'%(k,j),'mitocondrias',pts,0.0015,crista_mat,8)

    # Lysosomes include small surface nodules suggesting granular enzyme contents.
    for k,pos in enumerate([(-0.015,-0.037,-0.028),(0.064,0.029,-0.023),(-0.093,0.029,-0.026)]):
        sphere('compartimento_%02d'%k,'lisosomas',pos,0.0080,lyso,20,12)
        for j in range(5):
            a=2*pi*j/5
            sphere('granulo_%02d_%02d'%(k,j),'lisosomas',(pos[0]+0.004*math.cos(a),pos[1]+0.004*math.sin(a),pos[2]+0.0065),0.0013,lyso_grain,8,6)
    for k,pos in enumerate([(-0.110,-0.008,-0.030),(-0.048,-0.075,-0.037),(0.102,0.036,-0.029)]):
        sphere('vesicula_periferica_%02d'%k,'vesiculas',pos,0.0046,vesicle_mat,16,10)
    for k in range(18):
        a=rng.uniform(0,2*pi); r=rng.uniform(0.055,0.107)
        x=r*math.cos(a); y=0.78*r*math.sin(a)
        # Distributed free ribosomes sit on the lower cytosol shelf.
        z=-0.012-0.0693*math.sqrt(max(0.01,1-(x/0.1473)**2-(y/0.1193)**2))+0.004
        sphere('libre_%02d'%k,'ribosomas',(x,y,z),0.00165,ribosome,10,6)

    # Two open barrels of nine microtubule triplets, at right angles.
    def centriole(k, center, axis):
        n=Vector(axis).normalized()
        u=n.cross(Vector((0,1,0))).normalized()
        v=n.cross(u)
        c=Vector(center)
        for j in range(9):
            a=2*pi*j/9
            radial=math.cos(a)*u+math.sin(a)*v
            tangent=-math.sin(a)*u+math.cos(a)*v
            for s in range(3):
                offset=0.0043*radial+(s-1)*0.00115*tangent
                tube('centriolo_%d_triplete_%02d_%d'%(k,j,s),'centrosoma',[tuple(c+offset-0.008*n),tuple(c+offset+0.008*n)],0.00070,centriole_mat,6)
    centriole(0,(0.013,0.002,-0.006),(1,0,0))
    centriole(1,(0.025,0.014,-0.002),(0,0,1))

    # Sparse peripheral arcs and three short microtubules preserve the open view.
    for k in range(4):
        pts=[]
        for j in range(30):
            a=-2.8+3.8*j/29+0.22*k
            rx=0.115-0.010*k; ry=0.085-0.006*k
            pts.append((rx*math.cos(a),ry*math.sin(a),-0.042-0.004*k+0.006*math.cos(2*a+k)))
        tube('filamento_curvo_%02d'%k,'citoesqueleto',pts,0.0009,filament_mat,6)
    for k,end in enumerate([(0.074,0.019,-0.028),(0.053,-0.032,-0.035),(-0.009,-0.028,-0.031)]):
        start=Vector((0.020,0.008,-0.016)); finish=Vector(end)
        pts=[tuple(start.lerp(finish,j/12)+Vector((0,0,0.002*math.sin(pi*j/12)))) for j in range(13)]
        tube('microtubulo_%02d'%k,'citoesqueleto',pts,0.0010,filament_mat,7)

    # Freeze the actual tessellation and its corner shading before glTF export.
    # This also runs after the mitochondrial vertex rotations/translations.
    for me in built_meshes:
        me.update()
        me.calc_loop_triangles()
        vertices = [tuple(vertex.co) for vertex in me.vertices]
        triangles = [tuple(tri.vertices) for tri in me.loop_triangles]
        material_ids = [tri.material_index for tri in me.loop_triangles]
        corner_normals = [tuple(me.corner_normals[loop_id].vector)
                          for tri in me.loop_triangles for loop_id in tri.loops]
        me.clear_geometry()
        me.from_pydata(vertices, [], triangles)
        for polygon, mat_id in zip(me.polygons, material_ids):
            polygon.use_smooth = True
            polygon.material_index = mat_id
        me.update()
        me.normals_split_custom_set(corner_normals)
        me.update()

    return {
        'title':'Célula animal · interior a la vista',
        'design_notes':[
            'Maqueta de 30 cm con borde frontal bajo y corte geométrico de la envoltura; citosol pálido y membrana verde petróleo.',
            'Núcleo abierto orientado hacia la cámara, nucléolo frambuesa visible, poros y cromatina filamentosa sin cromosomas condensados.',
            'RER azul con ribosomas oscuros; REL celeste tubular; Golgi dorado de cinco cisternas con vesículas cercanas.',
            'Dos mitocondrias abiertas con matriz melocotón y crestas internas coral; centríolos de nueve tripletes aproximadamente perpendiculares.',
            'Filamentos periféricos escasos y microtúbulos cortos; colores y proporciones convencionales para legibilidad escolar.'
        ],
        'parts':{
            'membrana':{'label_position':[0.114,-0.068,-0.039]},
            'citoplasma':{'label_position':[-0.018,-0.090,-0.055]},
            'nucleo':{'label_position':[-0.072,0.004,0.011]},
            'nucleolo':{'label_position':[-0.035,0.008,0.020]},
            'ribosomas':{'label_position':[0.008,0.0435,0.0278]},
            'rer':{'label_position':[0.008,0.046,0.0268]},
            'rel':{'label_position':[0.072,0.051,-0.002]},
            'golgi':{'label_position':[0.023,-0.066,0.0008]},
            'mitocondrias':{'label_position':[-0.080,-0.041,-0.012]},
            'lisosomas':{'label_position':[-0.015,-0.037,-0.020]},
            'centrosoma':{'label_position':[0.025,0.0097,0.005]},
            'vesiculas':{'label_position':[0.060,-0.062,0.001]},
            'citoesqueleto':{'label_position':[0.101,-0.040,-0.038]}
        }
    }

