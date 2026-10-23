"""Original procedural teaching model. build() is called by the common runner."""
import math
import random
import bpy
from mathutils import Vector, Quaternion

SEED = 20261022
TAU = math.tau


def build():
    random.seed(SEED)
    materials = {}

    def material(name, color, roughness=0.47):
        m = bpy.data.materials.new(name)
        m.diffuse_color = (*color, 1.0)
        m.use_nodes = True
        p = m.node_tree.nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value = (*color, 1.0)
        p.inputs['Roughness'].default_value = roughness
        p.inputs['Metallic'].default_value = 0.0
        materials[name] = m
        return m

    membrane = material('Membrana · verde petróleo', (0.055, 0.40, 0.39))
    lip = material('Bordes de membrana · turquesa', (0.16, 0.67, 0.61))
    cytosol = material('Citosol · marfil acuoso', (0.81, 0.88, 0.79), 0.65)
    nuclear = material('Envoltura nuclear · violeta', (0.34, 0.20, 0.56))
    nucleoplasm = material('Nucleoplasma · lavanda', (0.67, 0.53, 0.79))
    nucleolus = material('Nucléolo · ciruela', (0.40, 0.075, 0.27))
    poremat = material('Poros nucleares · malva pálido', (0.82, 0.68, 0.89))
    rermat = material('RER · azul', (0.12, 0.43, 0.66))
    ribomat = material('Ribosomas · azul tinta', (0.035, 0.14, 0.24))
    relmat = material('REL · verde salvia', (0.24, 0.63, 0.43))
    gold = material('Golgi · ocre dorado', (0.95, 0.52, 0.12))
    goldlight = material('Golgi · ámbar claro', (1.0, 0.70, 0.25))
    mito = material('Mitocondria · terracota', (0.79, 0.22, 0.16))
    mitorim = material('Mitocondria · borde salmón', (0.98, 0.44, 0.29))
    matrix = material('Matriz mitocondrial · melocotón', (1.0, 0.74, 0.49))
    crestmat = material('Crestas · coral oscuro', (0.76, 0.27, 0.15))
    lysomat = material('Lisosomas · frambuesa', (0.71, 0.16, 0.36))
    enzyme = material('Contenido lisosomal · rosa', (0.96, 0.48, 0.56))
    centrmat = material('Centríolos · rosa cobre', (0.73, 0.36, 0.38))
    vesmat = material('Vesículas · amarillo mantequilla', (0.98, 0.83, 0.37))
    skelmat = material('Citoesqueleto · pizarra malva', (0.38, 0.42, 0.56))

    def mesh(name, part, vertices, faces, mat, smooth=True):
        data = bpy.data.meshes.new(name + '__mesh')
        data.from_pydata(vertices, [], faces)
        data.update()
        obj = bpy.data.objects.new(part + '__' + name, data)
        bpy.context.collection.objects.link(obj)
        obj['part_id'] = part
        data.materials.append(mat)
        for polygon in data.polygons:
            polygon.use_smooth = smooth
        return obj

    def transformed(p, center, rotation=None):
        v = Vector(p)
        if rotation is not None:
            v = rotation @ v
        return tuple(v + Vector(center))

    def ball(name, part, center, radii, mat, segments=16, rings=10, rotation=None):
        v = [transformed((0, 0, radii[2]), center, rotation)]
        for j in range(1, rings):
            theta = math.pi * j / rings
            for i in range(segments):
                a = TAU * i / segments
                v.append(transformed((radii[0]*math.sin(theta)*math.cos(a),
                                      radii[1]*math.sin(theta)*math.sin(a),
                                      radii[2]*math.cos(theta)), center, rotation))
        v.append(transformed((0, 0, -radii[2]), center, rotation))
        f = [(0, 1+i, 1+(i+1)%segments) for i in range(segments)]
        for j in range(rings-2):
            a = 1+j*segments
            b = a+segments
            f.extend((a+i, b+i, b+(i+1)%segments, a+(i+1)%segments) for i in range(segments))
        b = 1+(rings-2)*segments
        f.extend((b+i, len(v)-1, b+(i+1)%segments) for i in range(segments))
        return mesh(name, part, v, f, mat)

    def tube(name, part, points, radius, mat, sides=8, closed=False):
        pts = [Vector(p) for p in points]
        verts, faces = [], []
        for j, p in enumerate(pts):
            tangent = pts[(j+1)%len(pts)] - pts[(j-1)%len(pts)] if closed else pts[min(j+1,len(pts)-1)]-pts[max(j-1,0)]
            tangent.normalize()
            ref = Vector((0,0,1)) if abs(tangent.z) < 0.9 else Vector((0,1,0))
            u = tangent.cross(ref).normalized()
            w = tangent.cross(u).normalized()
            r = radius[j] if isinstance(radius, (tuple,list)) else radius
            for k in range(sides):
                a = TAU*k/sides
                verts.append(tuple(p+r*(math.cos(a)*u+math.sin(a)*w)))
        for j in range(len(pts) if closed else len(pts)-1):
            b = ((j+1)%len(pts))*sides
            faces.extend((j*sides+k, b+k, b+(k+1)%sides, j*sides+(k+1)%sides) for k in range(sides))
        if not closed:
            faces.append(tuple(reversed(range(sides))))
            faces.append(tuple((len(pts)-1)*sides+k for k in range(sides)))
        return mesh(name, part, verts, faces, mat)

    def truncated(name, part, center, radii, cut, mat, rotation=None, hollow=False, thickness=0.0015, segments=40, rings=16):
        # Remove the cap above local z=cut*radii[2]; build the actual cut edge.
        theta0 = math.acos(cut)
        verts, faces = [], []
        def surface(rr, reverse=False):
            offset = len(verts)
            for j in range(rings):
                theta = theta0+(math.pi-theta0)*j/rings
                for i in range(segments):
                    a = TAU*i/segments
                    p = (rr[0]*math.sin(theta)*math.cos(a),rr[1]*math.sin(theta)*math.sin(a),rr[2]*math.cos(theta))
                    verts.append(transformed(p, center, rotation))
            pole = len(verts)
            verts.append(transformed((0,0,-rr[2]),center,rotation))
            local = []
            for j in range(rings-1):
                a = offset+j*segments
                b = a+segments
                local.extend((a+i,b+i,b+(i+1)%segments,a+(i+1)%segments) for i in range(segments))
            a = offset+(rings-1)*segments
            local.extend((a+i,pole,a+(i+1)%segments) for i in range(segments))
            faces.extend(tuple(reversed(f)) if reverse else f for f in local)
            return offset
        surface(radii)
        if hollow:
            inner = surface(tuple(r-thickness for r in radii),True)
            faces.extend((i,(i+1)%segments,inner+(i+1)%segments,inner+i) for i in range(segments))
        else:
            centeridx = len(verts)
            verts.append(transformed((0,0,cut*radii[2]),center,rotation))
            faces.extend((centeridx,i,(i+1)%segments) for i in range(segments))
        return mesh(name,part,verts,faces,mat)

    # A wide, uneven bowl: its low front gives an unobstructed view into the cell.
    ns, nr = 72, 18
    def boundary(phi, inset=0):
        rimz = -0.006+0.026*math.sin(phi)
        theta = math.acos(-rimz/0.085)
        organic = 1+0.018*math.sin(3*phi+0.3)+0.010*math.cos(5*phi)
        return ((0.148-inset)*math.sin(theta)*math.cos(phi)*organic,
                (0.120-inset)*math.sin(theta)*math.sin(phi)*organic, rimz)
    verts, faces = [], []
    starts = []
    for layer in range(2):
        inset = layer*0.0021
        off = len(verts)
        starts.append(off)
        for j in range(1,nr+1):
            for i in range(ns):
                a=TAU*i/ns
                rimz=-0.006+0.026*math.sin(a)
                th=math.acos(-rimz/0.085)*j/nr
                organic=1+0.018*math.sin(3*a+0.3)+0.010*math.cos(5*a)
                verts.append(((0.148-inset)*math.sin(th)*math.cos(a)*organic,
                              (0.120-inset)*math.sin(th)*math.sin(a)*organic,
                              -(0.085-inset)*math.cos(th)))
        pole = len(verts)
        verts.append((0,0,-(0.085-inset)))
        local = [(pole,off+(i+1)%ns,off+i) for i in range(ns)]
        for j in range(nr-1):
            for i in range(ns):
                local.append((off+j*ns+i,off+j*ns+(i+1)%ns,off+(j+1)*ns+(i+1)%ns,off+(j+1)*ns+i))
        faces.extend(tuple(reversed(f)) if layer else f for f in local)
    for i in range(ns):
        a=starts[0]+(nr-1)*ns+i
        b=starts[0]+(nr-1)*ns+(i+1)%ns
        c=starts[1]+(nr-1)*ns+(i+1)%ns
        d=starts[1]+(nr-1)*ns+i
        faces.append((a,b,c,d))
    mesh('envoltura_abierta','membrana',verts,faces,membrane)
    tube('labio_del_corte','membrana',[boundary(TAU*i/ns,0.0006) for i in range(ns)],0.0010,lip,8,True)

    # Closed pale cytosol volume with a gently sloping exposed upper surface.
    verts=[(0,0,-0.023)]; faces=[]
    for j in range(1,13):
        rho=j/12
        for i in range(ns):
            x,y,z=boundary(TAU*i/ns,0.0032)
            verts.append((x*rho,y*rho,-0.023+rho*rho*(z+0.021)))
    for i in range(ns): faces.append((0,1+i,1+(i+1)%ns))
    for j in range(11):
        a=1+j*ns; b=a+ns
        faces.extend((a+i,b+i,b+(i+1)%ns,a+(i+1)%ns) for i in range(ns))
    bottom=len(verts); verts.append((0,0,-0.080))
    last=1+11*ns
    faces.extend((last+i,bottom,last+(i+1)%ns) for i in range(ns))
    mesh('volumen_citosol_expuesto','citoplasma',verts,faces,cytosol)

    # Nucleus opens toward the common three-quarter camera, revealing the nucleolus.
    nc=(-0.027,0.017,0.015)
    view=Vector((0.43,-0.57,0.70)).normalized()
    nq=Vector((0,0,1)).rotation_difference(view)
    truncated('envoltura_nuclear_cortada','nucleo',nc,(0.043,0.041,0.040),0.30,nuclear,nq,True,0.0015,48,18)
    truncated('nucleoplasma_expuesto','nucleo',nc,(0.0408,0.0388,0.0378),0.29,nucleoplasm,nq,False,segments=40,rings=14)
    ball('nucleolo_sin_membrana','nucleolo',tuple(Vector(nc)+view*0.011+Vector((-0.004,0.003,0.001))),
         (0.012,0.011,0.011),nucleolus,24,14)
    # Pore rims follow the curved envelope; their open dark centers remain visible.
    for k in range(9):
        a=TAU*k/9+0.2
        th=1.48+0.13*math.sin(k*1.7)
        local=Vector((0.043*math.sin(th)*math.cos(a),0.041*math.sin(th)*math.sin(a),0.040*math.cos(th)))
        normal=local.normalized()
        pq=Vector((0,0,1)).rotation_difference(nq@normal)
        pc=Vector(nc)+nq@local
        pts=[transformed((0.0022*math.cos(TAU*j/12),0.0022*math.sin(TAU*j/12),0),pc,pq) for j in range(12)]
        tube('poro_%02d'%k,'nucleo',pts,0.00065,poremat,6,True)

    def sack(name,part,path,width,height,mat):
        pts=[Vector(p) for p in path]
        v=[]; f=[]; sides=10
        for j,p in enumerate(pts):
            t=(pts[min(j+1,len(pts)-1)]-pts[max(j-1,0)]).normalized()
            side=Vector((-t.y,t.x,0)).normalized()
            taper=0.14+0.86*(math.sin(math.pi*j/(len(pts)-1))**0.35)
            for k in range(sides):
                a=TAU*k/sides
                v.append(tuple(p+side*(width*taper*math.cos(a))+Vector((0,0,height*taper*math.sin(a)))))
        for j in range(len(pts)-1):
            f.extend((j*sides+k,(j+1)*sides+k,(j+1)*sides+(k+1)%sides,j*sides+(k+1)%sides) for k in range(sides))
        f.append(tuple(reversed(range(sides))))
        f.append(tuple((len(pts)-1)*sides+k for k in range(sides)))
        return mesh(name,part,v,f,mat)

    # RER is a blue, folded perinuclear set of flattened sacs, with bound ribosomes.
    for layer in range(4):
        rad=0.052+layer*0.0031
        z=-0.004+layer*0.009
        path=[]
        for j in range(33):
            a=math.radians(62+145*j/32)
            path.append((nc[0]+rad*math.cos(a),nc[1]+rad*math.sin(a),z+0.0015*math.sin(a*3)))
        sack('cisterna_rugosa_%02d'%layer,'rer',path,0.0058,0.0017,rermat)
        for j in range(15):
            a=math.radians(68+132*j/14)
            rr=rad+(0.0022 if j%2 else -0.0022)
            p=(nc[0]+rr*math.cos(a),nc[1]+rr*math.sin(a),z+0.0033+0.0015*math.sin(a*3))
            ball('adherido_%02d_%02d'%(layer,j),'ribosomas',p,(0.0017,)*3,ribomat,7,4)

    # REL: branching smooth tubes at the posterior right of the nucleus.
    for branch in range(5):
        pts=[]
        for j in range(24):
            t=j/23
            pts.append((0.019+0.033*t+0.005*math.sin(TAU*t+branch),
                        0.062+0.008*branch+0.006*math.sin(math.pi*t),
                        -0.001+0.008*math.sin(math.pi*t)+0.002*math.cos(branch)))
        tube('tubulo_liso_%02d'%branch,'rel',pts,0.0021,relmat,8)
    for k in range(3):
        pts=[(0.029+0.008*k+0.003*math.sin(math.pi*j/17),0.062+0.033*j/17,0.002+0.003*math.sin(math.pi*j/17)) for j in range(18)]
        tube('anastomosis_%02d'%k,'rel',pts,0.0019,relmat,8)

    # Golgi's warm stack is separate from the blue perinuclear RER.
    for layer in range(5):
        path=[]
        for j in range(31):
            u=-1+2*j/30
            span=0.028-0.0017*layer
            path.append((0.075+span*u,0.027+0.011*u*u+0.0014*layer,-0.010+0.0075*layer+0.001*math.cos(math.pi*u)))
        sack('cisterna_golgi_%02d'%layer,'golgi',path,0.0050,0.0017,gold if layer%2 else goldlight)
    for k,p in enumerate([(0.111,0.044,0.001),(0.108,0.033,0.016),(0.044,0.041,0.014),
                          (0.101,0.052,0.024),(0.116,0.023,-0.003),(0.053,0.049,0.030)]):
        ball('vesicula_transporte_%02d'%k,'vesiculas',p,(0.0037,0.0034,0.0036),vesmat,12,8)

    # Open mitochondrial bowl with physical internal cristae rising from the matrix.
    mc=(0.073,-0.038,-0.003)
    mq=Quaternion((0,0,1),math.radians(-24))
    truncated('abierta_envoltura_doble','mitocondrias',mc,(0.035,0.018,0.018),0.47,mito,mq,True,0.0014,40,14)
    truncated('abierta_matriz','mitocondrias',mc,(0.0328,0.0158,0.0158),-0.12,matrix,mq,False,segments=32,rings=10)
    pts=[transformed((0.035*math.sqrt(1-0.47**2)*math.cos(TAU*j/48),0.018*math.sqrt(1-0.47**2)*math.sin(TAU*j/48),0.018*0.47),mc,mq) for j in range(48)]
    tube('abierta_borde_del_corte','mitocondrias',pts,0.00085,mitorim,6,True)
    # Solid folded fins sit inside the hollow organelle, below its exposed rim.
    for k in range(6):
        x=-0.022+0.0088*k
        ymax=0.0122*math.sqrt(max(0.1,1-(x/0.030)**2))
        v=[]; f=[]
        for j in range(17):
            t=-1+2*j/16
            y=ymax*t
            xx=x+0.0014*math.sin(t*math.pi*1.5+k)
            top=0.0038+0.0025*(1-t*t)
            for dx,z in [(-0.0006,-0.0027),(0.0006,-0.0027),(0.0006,top),(-0.0006,top)]:
                v.append(transformed((xx+dx,y,z),mc,mq))
        for j in range(16):
            for s in range(4): f.append((j*4+s,(j+1)*4+s,(j+1)*4+(s+1)%4,j*4+(s+1)%4))
        f.extend([(3,2,1,0),(64,65,66,67)])
        mesh('cresta_interna_%02d'%k,'mitocondrias',v,f,crestmat)
    # Second intact bean, with a subtly asymmetric profile rather than surface stripes.
    closedcenter=(-0.089,-0.036,-0.008)
    q2=Quaternion((0,0,1),math.radians(37))
    ball('cerrada_envoltura','mitocondrias',closedcenter,(0.030,0.015,0.014),mito,32,16,q2)

    # A compact perpendicular pair of nine microtubule triplets.
    for centr,(center,axis) in enumerate([((0.012,-0.053,-0.003),(1,0.12,0.10)),((0.022,-0.044,0.005),(-0.10,0.13,1))]):
        cq=Vector((0,0,1)).rotation_difference(Vector(axis).normalized())
        for k in range(9):
            a=TAU*k/9
            for strand in range(3):
                r=0.0045+0.0011*(strand-1)
                aa=a+0.10*(strand-1)
                pts=[transformed((r*math.cos(aa),r*math.sin(aa),z),center,cq) for z in (-0.009,0.009)]
                tube('centriolo_%d_triplete_%02d_%d'%(centr,k,strand),'centrosoma',pts,0.00068,centrmat,8)

    for k,(p,r) in enumerate([((-0.058,-0.068,-0.012),0.008),((0.043,-0.081,-0.015),0.0068)]):
        ball('compartimento_digestivo_%02d'%k,'lisosomas',p,(r,r*0.94,r),lysomat,20,12)
        # Small visible accents suggest granular content without creating a membrane on the nucleolus.
        for j in range(3):
            off=Vector((0.25*r*math.cos(TAU*j/3),-0.68*r,0.53*r+0.12*r*math.sin(j)))
            ball('granulo_%02d_%02d'%(k,j),'lisosomas',tuple(Vector(p)+off),(r*0.16,)*3,enzyme,8,5)

    # Free ribosomes are a sparse population on the exposed cytosol.
    free=[(-0.102,-0.003),(-0.110,0.025),(-0.093,0.052),(-0.065,-0.019),(-0.054,-0.040),
          (-0.026,-0.078),(-0.013,-0.067),(0.010,-0.084),(0.030,-0.019),(0.043,-0.009),
          (0.110,-0.020),(0.114,0.006),(0.068,-0.077),(-0.110,-0.058),(-0.086,-0.075),
          (-0.025,0.090),(0.008,0.083),(0.083,0.074)]
    for k,(x,y) in enumerate(free):
        z=-0.017+0.015*max(y,0)/0.12
        ball('libre_%02d'%k,'ribosomas',(x,y,z),(0.0018,)*3,ribomat,7,4)

    # Peripheral, curved filament tracks; no false centrosomal sunburst.
    skeleton_paths=[
        [(-0.114+0.099*t,-0.071+0.014*math.sin(math.pi*t),-0.026+0.004*math.sin(math.pi*t)) for t in [j/30 for j in range(31)]],
        [(-0.102+0.121*t,-0.085+0.010*math.sin(math.pi*t),-0.027+0.004*math.sin(math.pi*t)) for t in [j/30 for j in range(31)]],
        [(0.034+0.079*t,-0.072+0.075*t,-0.021+0.003*math.sin(TAU*t)) for t in [j/30 for j in range(31)]],
        [(-0.121+0.017*math.sin(math.pi*t),-0.029+0.078*t,-0.016+0.008*t) for t in [j/28 for j in range(29)]],
        [(0.061+0.039*t,0.074-0.020*t,-0.004+0.003*math.sin(math.pi*t)) for t in [j/20 for j in range(21)]]
    ]
    for k,path in enumerate(skeleton_paths):
        tube('filamento_curvo_%02d'%k,'citoesqueleto',path,0.00085,skelmat,6)

    def anchor(object_name, vertex_index):
        return list(bpy.data.objects[object_name].data.vertices[vertex_index].co)

    result = {
        'title': 'Célula animal · interior en color',
        'design_notes': 'Maqueta original de corte abierto con borde orgánico verde petróleo y citosol marfil. Núcleo violeta abierto hacia la cámara con nucléolo sin envoltura y poros sugeridos. RER azul con ribosomas oscuros, REL tubular verde y Golgi ámbar en pila independiente. Una mitocondria coral abierta muestra matriz y seis crestas volumétricas internas; otra conserva su envoltura. Dos centríolos de nueve tripletes casi perpendiculares y filamentos periféricos escasos. Colores y tamaños son convenciones didácticas; la selección no representa un inventario celular exhaustivo.',
        'parts': {
            'membrana': {'label_position': anchor('membrana__labio_del_corte', 63*8+6)},
            'citoplasma': {'label_position': anchor('citoplasma__volumen_citosol_expuesto', 1+7*72+54)},
            'nucleo': {'label_position': anchor('nucleo__nucleoplasma_expuesto', 0)},
            'nucleolo': {'label_position': anchor('nucleolo__nucleolo_sin_membrana', 0)},
            'ribosomas': {'label_position': anchor('ribosomas__libre_04', 0)},
            'rer': {'label_position': anchor('rer__cisterna_rugosa_03', 16*10+2)},
            'rel': {'label_position': anchor('rel__tubulo_liso_02', 12*8+6)},
            'golgi': {'label_position': anchor('golgi__cisterna_golgi_04', 15*10+2)},
            'mitocondrias': {'label_position': anchor('mitocondrias__cresta_interna_02', 8*4+3)},
            'lisosomas': {'label_position': anchor('lisosomas__compartimento_digestivo_00', 0)},
            'centrosoma': {'label_position': anchor('centrosoma__centriolo_1_triplete_04_1', 8)},
            'vesiculas': {'label_position': anchor('vesiculas__vesicula_transporte_01', 0)},
            'citoesqueleto': {'label_position': anchor('citoesqueleto__filamento_curvo_00', 15*6+4)},
        }
    }

    # Technical round-trip repair: establish final triangle topology first, then
    # freeze its split normals. Anchor coordinates above are captured before any
    # topology conversion, preserving the original label positions exactly.
    previous_active = bpy.context.view_layer.objects.active
    previous_selected = list(bpy.context.selected_objects)
    for obj in previous_selected:
        obj.select_set(False)
    final_meshes = [obj for obj in bpy.context.scene.objects
                    if obj.type == 'MESH' and obj.get('part_id') in result['parts']]
    for obj in final_meshes:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        triangulate = obj.modifiers.new('Final explicit triangles', 'TRIANGULATE')
        triangulate.quad_method = 'FIXED'
        triangulate.ngon_method = 'CLIP'
        triangulate.min_vertices = 4
        if hasattr(triangulate, 'keep_custom_normals'):
            triangulate.keep_custom_normals = True
        bpy.ops.object.modifier_apply(modifier=triangulate.name)
        data = obj.data
        data.update()
        final_normals = [tuple(corner.vector) for corner in data.corner_normals]
        data.normals_split_custom_set(final_normals)
        data.update()
        obj.select_set(False)
    for obj in previous_selected:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = previous_active
    return result
