"""Célula animal: geometría original, unidades en metros."""
import bpy
import math
import random
from mathutils import Vector


def build():
    rng = random.Random(20261022)
    materials = {}
    def mat(name, color, rough=.4):
        m = bpy.data.materials.new(name)
        m.diffuse_color = (*color, 1)
        m.use_nodes = True
        p = m.node_tree.nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value = (*color, 1)
        p.inputs['Roughness'].default_value = rough
        p.inputs['Metallic'].default_value = 0
        materials[name] = m
        return m
    membrane = mat('Membrana · azul petróleo', (.055,.31,.36))
    edge = mat('Borde del corte · turquesa', (.20,.64,.64))
    cyto = mat('Citosol · marfil frío', (.69,.82,.77), .62)
    nuclear = mat('Envoltura nuclear · ciruela', (.31,.17,.44))
    nuclear_edge = mat('Corte nuclear · malva', (.64,.40,.68))
    plasma = mat('Nucleoplasma', (.65,.52,.72), .55)
    nucleolus = mat('Nucléolo · mora', (.46,.065,.26))
    rer_mat = mat('RER · azul', (.13,.38,.65))
    ribo = mat('Ribosomas · tinta', (.075,.12,.25))
    rel_mat = mat('REL · celeste', (.25,.64,.77))
    golgi_mat = mat('Golgi · ocre', (.92,.52,.12))
    golgi_edge = mat('Golgi · borde dorado', (1,.73,.30))
    mito_mat = mat('Mitocondria · terracota', (.75,.22,.13))
    mito_inner = mat('Matriz mitocondrial', (1,.65,.37))
    cresta_mat = mat('Crestas · coral', (.87,.32,.20))
    lyso = mat('Lisosomas · verde oliva', (.44,.59,.16))
    ves = mat('Vesículas · ámbar claro', (1,.76,.34))
    centr = mat('Centríolos · rosa', (.75,.24,.45))
    filament = mat('Filamentos · verde', (.13,.47,.38))

    def mesh(name, part, verts, faces, material, smooth=True):
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        me.update()
        ob = bpy.data.objects.new(part+'__'+name, me)
        bpy.context.collection.objects.link(ob)
        ob['part_id'] = part
        ob.data.materials.append(material)
        for p in me.polygons:
            p.use_smooth = smooth
        return ob

    def ball(name, part, center, radii, material, seg=20, rings=12):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=1, location=center)
        ob = bpy.context.object
        ob.name = part+'__'+name
        for v in ob.data.vertices:
            v.co.x *= radii[0]
            v.co.y *= radii[1]
            v.co.z *= radii[2]
        ob['part_id'] = part
        ob.data.materials.append(material)
        for p in ob.data.polygons:
            p.use_smooth = True
        return ob

    def tube(name, part, points, radius, material, sides=7, closed=False):
        pts = [Vector(p) for p in points]
        verts, faces = [], []
        for i,p in enumerate(pts):
            tangent = (pts[(i+1)%len(pts)]-pts[(i-1)%len(pts)]) if closed else (pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)])
            tangent.normalize()
            ref = Vector((0,0,1)) if abs(tangent.z)<.92 else Vector((0,1,0))
            u = tangent.cross(ref).normalized()
            v = tangent.cross(u).normalized()
            for k in range(sides):
                a = 2*math.pi*k/sides
                verts.append(tuple(p + radius*(math.cos(a)*u+math.sin(a)*v)))
        for i in range(len(pts) if closed else len(pts)-1):
            j = (i+1)%len(pts)
            for k in range(sides):
                faces.append((i*sides+k,i*sides+(k+1)%sides,j*sides+(k+1)%sides,j*sides+k))
        if not closed:
            faces.extend([tuple(reversed(range(sides))), tuple((len(pts)-1)*sides+k for k in range(sides))])
        return mesh(name,part,verts,faces,material)

    def shell(name,part,center,radii,lip,thickness,material,cutmat,n=64,rows=14):
        # A closed thin ellipsoidal shell with a real, curved cut edge.
        verts, faces = [], []
        for inner in (False, True):
            r = [a-(thickness if inner else 0) for a in radii]
            for j in range(rows+1):
                for i in range(n):
                    a=2*math.pi*i/n
                    polar=.012+(lip(a)-.012)*j/rows
                    verts.append((center[0]+r[0]*math.sin(polar)*math.cos(a),center[1]+r[1]*math.sin(polar)*math.sin(a),center[2]-r[2]*math.cos(polar)))
        layer=(rows+1)*n
        for side in range(2):
            for j in range(rows):
                for i in range(n):
                    a=side*layer+j*n+i; b=side*layer+j*n+(i+1)%n
                    f=(a,b,b+n,a+n)
                    faces.append(f if side==0 else tuple(reversed(f)))
        for i in range(n):
            a=rows*n+i; b=rows*n+(i+1)%n
            faces.append((a,b,b+layer,a+layer))
            faces.append((i,(i+1)%n,(i+1)%n+layer,i+layer))
        ob=mesh(name,part,verts,faces,material)
        ob.data.materials.append(cutmat)
        for p in list(ob.data.polygons)[2*rows*n:]: p.material_index=1
        return ob

    shell('envoltura_abierta','membrana',(0,0,0),(.15,.119,.075),lambda a:1.72+.63*math.sin(a),.0022,membrane,edge)
    # Flattened citosol cushion fills the base, leaving the organelles exposed.
    ball('volumen_citosol','citoplasma',(0,0,-.045),(.134,.102,.022),cyto,64,20)
    nc=(-.033,.024,.003)
    shell('envoltura_cortada','nucleo',nc,(.044,.039,.044),lambda a:1.52+.48*math.sin(a),.0015,nuclear,nuclear_edge,48,12)
    ball('nucleoplasma_visible','nucleo',(-.033,.024,-.010),(.038,.033,.019),plasma,40,16)
    ball('cuerpo_sin_membrana','nucleolo',(-.025,.017,.009),(.012,.011,.0105),nucleolus,28,16)
    # Poros: anillos sobre la cara posterior de la envoltura.
    for j,a in enumerate([.40,.85,1.30,1.75,2.20,2.65]):
        theta=1.65
        p=Vector((nc[0]+.044*math.sin(theta)*math.cos(a),nc[1]+.039*math.sin(theta)*math.sin(a),nc[2]-.044*math.cos(theta)))
        normal=Vector((math.cos(a),math.sin(a),.1)).normalized()
        u=normal.cross(Vector((0,0,1))).normalized(); v=normal.cross(u)
        tube('poro_%02d'%j,'nucleo',[p+.0022*(math.cos(t)*u+math.sin(t)*v) for t in [2*math.pi*k/16 for k in range(16)]],.00065,nuclear_edge,6,True)

    def sheet(name,part,center,length,width,bend,thick,material,rotation=0):
        verts=[]; n=24
        c,s=math.cos(rotation),math.sin(rotation)
        def point(t,q,z):
            x=t*length/2; y=bend*(t*t-.5)+q*width/2*(.75+.25*math.cos(t*math.pi/2))
            return (center[0]+c*x-s*y,center[1]+s*x+c*y,center[2]+z+.0015*math.cos(t*math.pi))
        for z in (-thick/2,thick/2):
            for i in range(n+1):
                for q in (-1,1): verts.append(point(2*i/n-1,q,z))
        faces=[]; m=2*(n+1)
        for i in range(n):
            a=2*i
            faces.extend([(a,a+2,a+3,a+1),(m+a+1,m+a+3,m+a+2,m+a),(a,m+a,m+a+2,a+2),(a+1,a+3,m+a+3,m+a+1)])
        faces.extend([(0,1,m+1,m),(2*n,m+2*n,m+2*n+1,2*n+1)])
        mesh(name,part,verts,faces,material)
        return point

    for j in range(4):
        p=sheet('cisterna_%02d'%j,'rer',(-.080,.027,-.011+j*.010),.060,.013,.014,.0023,rer_mat,1.15)
        for k in range(9):
            t=-.85+1.7*k/8
            q= .55 if k%2 else -.55
            xyz=p(t,q,.0026)
            ball('adherido_%02d_%02d'%(j,k),'ribosomas',xyz,(.00175,)*3,ribo,10,6)
    # El retículo liso es una red de tubos bifurcados, sin puntos adheridos.
    for j in range(4):
        points=[]
        for k in range(25):
            t=k/24
            points.append((-.093+.060*t,-.046+j*.007+.004*math.sin(t*math.pi*3),-.012+.003*math.sin(t*math.pi*2+j)))
        tube('tubulo_%02d'%j,'rel',points,.0025,rel_mat,8)
    for j in range(3):
        x=-.082+j*.018
        tube('anastomosis_%02d'%j,'rel',[(x,-.045,-.012),(x+.003,-.035,-.009),(x,-.023,-.013)],.0023,rel_mat,8)
    for j in range(5):
        p=sheet('cisterna_aplanada_%02d'%j,'golgi',(.044,.020,-.016+j*.0075),.057-j*.003,.012,.015,.0025,golgi_mat,-.22)
        tube('borde_cisterna_%02d'%j,'golgi',[p(2*k/24-1,-1,.0002) for k in range(25)],.0015,golgi_edge,6)
    for j,(x,y,z,r) in enumerate([(.073,.004,.012,.005),(.079,.023,-.009,.004),(.063,-.003,-.012,.0035),(.044,-.003,.019,.004),(.014,-.067,-.011,.006),(-.100,.046,-.010,.0045)]):
        ball('transporte_%02d'%j,'vesiculas',(x,y,z),(r,r,r),ves,18,10)

    def mitochondrion(index, center, angle, size=1):
        cx,cy,cz=center
        c,s=math.cos(angle),math.sin(angle)
        def world(p): return (cx+size*(c*p[0]-s*p[1]),cy+size*(s*p[0]+c*p[1]),cz+size*p[2])
        # Open organelle, with a continuous inner floor and internal folded membrane.
        ob=shell('corte_%02d'%index,'mitocondrias',(0,0,0),(.029,.013,.013),lambda a:1.7+.18*math.sin(a),.0014,mito_mat,mito_inner,40,10)
        for v in ob.data.vertices: v.co=world(v.co)
        floor=ball('matriz_%02d'%index,'mitocondrias',center,(.026*size,.010*size,.004*size),mito_inner,28,10)
        floor.rotation_euler.z=angle
        for j in range(6):
            x=-.019+j*.0074
            pts=[]
            extent=.0085*math.sqrt(max(.2,1-(x/.027)**2))
            for k in range(13):
                t=k/12
                pts.append(world((x+.0014*math.sin(t*math.pi*2),-extent+2*extent*t,.002+.005*math.sin(t*math.pi))))
            tube('cresta_interna_%02d_%02d'%(index,j),'mitocondrias',pts,.0014*size,cresta_mat,7)
    mitochondrion(1,(.055,-.062,-.012),-.30)
    mitochondrion(2,(.079,.061,-.002),.80,.83)
    for j,(p,r) in enumerate([((-.009,-.065,-.010),.009),((.103,-.017,-.016),.0075),((-.066,.074,-.005),.007)]):
        ball('compartimento_%02d'%j,'lisosomas',p,(r,r,r),lyso,22,14)
        for k in range(4):
            a=k*math.pi/2
            ball('relieve_%02d_%02d'%(j,k),'lisosomas',(p[0]+r*.42*math.cos(a),p[1]+r*.42*math.sin(a),p[2]+r*.85),(r*.13,)*3,lyso,8,6)
    # Two hollow nine-fold barrels, approximately perpendicular.
    for j,(center,axis) in enumerate([((.011,.061,.002),(1,0,0)),((.026,.060,.016),(0,0,1))]):
        ax=Vector(axis); u=ax.cross(Vector((0,1,0))).normalized(); v=ax.cross(u)
        cp=Vector(center)
        for k in range(9):
            a=2*math.pi*k/9
            d=.005*(math.cos(a)*u+math.sin(a)*v)
            for t in (-1,0,1):
                shift=t*.00085*(-math.sin(a)*u+math.cos(a)*v)
                tube('centríolo_%d_triplete_%d_%d'%(j,k,t),'centrosoma',[cp+d+shift-ax*.009,cp+d+shift+ax*.009],.0007,centr,6)
    # A sparse peripheral network; only two short microtubules approach the centrosome.
    paths=[[( -.115,-.037,-.024),(-.099,-.068,-.023),(-.064,-.085,-.022),(-.024,-.091,-.023),(.016,-.088,-.024)],
           [(.011,-.094,-.024),(.053,-.087,-.024),(.092,-.064,-.023),(.116,-.028,-.024),(.122,.012,-.024)],
           [(-.108,.053,-.025),(-.081,.081,-.023),(-.043,.091,-.023),(-.002,.094,-.024),(.036,.086,-.023)],
           [(-.115,-.015,-.026),(-.096,-.003,-.024),(-.083,.015,-.021)],
           [(.020,.056,-.016),(.041,.070,-.022),(.062,.084,-.025)],
           [(.017,.057,-.018),(.008,.079,-.022),(-.009,.092,-.023)]]
    for j,pts in enumerate(paths): tube('filamento_%02d'%j,'citoesqueleto',pts,.001,filament,7)
    for j in range(22):
        a=rng.uniform(0,2*math.pi); r=rng.uniform(.047,.105)
        x=r*math.cos(a); y=.82*r*math.sin(a)
        if x<-.025 and y>-.05: continue
        ball('libre_%02d'%j,'ribosomas',(x,y,-.020),(.0018,)*3,ribo,10,6)

    labels={
        'membrana':[.133,.017,.017], 'citoplasma':[.001,-.038,-.024],
        'nucleo':[-.056,.047,.028], 'nucleolo':[-.025,.017,.0195],
        'ribosomas':[-.079,.031,.023], 'rer':[-.084,.042,.020],
        'rel':[-.064,-.040,-.009], 'golgi':[.044,.015,.016],
        'mitocondrias':[.055,-.062,-.005], 'lisosomas':[-.009,-.065,-.001],
        'centrosoma':[.031,.060,.020], 'vesiculas':[.073,.004,.017],
        'citoesqueleto':[.092,-.064,-.022]}
    return {'title':'Célula animal · interior en capas',
            'design_notes':'Maqueta abierta con envoltura fina azul petróleo y citosol pálido. Núcleo ciruela con corte real, poros sugeridos y nucléolo expuesto; cisternas azules del RER con ribosomas oscuros y red tubular celeste del REL. Golgi ocre en cinco cisternas curvas, mitocondrias terracota abiertas con crestas interiores, centríolos huecos perpendiculares de nueve tripletes. Citoesqueleto periférico escaso. Colores y proporciones didácticos, sin escala microscópica exacta.',
            'parts':{key:{'label_position':value} for key,value in labels.items()}}
