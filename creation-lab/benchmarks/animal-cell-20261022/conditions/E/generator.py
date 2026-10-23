import bpy
import math
import random
from mathutils import Vector


SEED = 20261022


def build():
    """Build an open, classroom-friendly animal cell in Blender's empty scene."""
    random.seed(SEED)

    C = {
        "membrana": (0.13, 0.56, 0.67, 1),
        "citoplasma": (0.78, 0.86, 0.73, 1),
        "nucleo": (0.36, 0.44, 0.76, 1),
        "nucleolo": (0.94, 0.42, 0.24, 1),
        "ribosomas": (0.27, 0.17, 0.13, 1),
        "rer": (0.30, 0.66, 0.69, 1),
        "rel": (0.27, 0.70, 0.56, 1),
        "golgi": (0.89, 0.59, 0.23, 1),
        "mitocondrias": (0.80, 0.34, 0.28, 1),
        "lisosomas": (0.81, 0.60, 0.72, 1),
        "centrosoma": (0.37, 0.44, 0.53, 1),
        "vesiculas": (0.94, 0.74, 0.39, 1),
        "citoesqueleto": (0.48, 0.60, 0.44, 1),
    }
    mats = {}
    for key, rgba in C.items():
        mat = bpy.data.materials.new("Cell • " + key)
        mat.diffuse_color = rgba
        mat.use_nodes = True
        bs = mat.node_tree.nodes.get("Principled BSDF")
        bs.inputs["Base Color"].default_value = rgba
        bs.inputs["Roughness"].default_value = 0.43
        bs.inputs["Metallic"].default_value = 0.0
        mats[key] = mat

    def mesh_obj(name, part, verts, faces, material, smooth=True):
        # Create explicit non-degenerate triangles before handing geometry to Blender/exporters.
        points = [Vector(v) for v in verts]
        triangles = []
        for face in faces:
            for i in range(1, len(face)-1):
                tri = (face[0], face[i], face[i+1])
                a, b, c = (points[k] for k in tri)
                if (b-a).cross(c-a).length_squared > 1e-20:
                    triangles.append(tri)
        me = bpy.data.meshes.new(name + " Mesh")
        me.from_pydata(verts, [], triangles)
        me.update()
        ob = bpy.data.objects.new(name, me)
        bpy.context.collection.objects.link(ob)
        ob["part_id"] = part
        ob.data.materials.append(mats[part])
        if smooth:
            for p in me.polygons:
                p.use_smooth = True
        return ob

    def uv(name, part, loc, scale, seg=24, rings=16):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=1, location=loc)
        ob = bpy.context.object
        ob.name = name
        ob.scale = scale
        ob["part_id"] = part
        ob.data.materials.append(mats[part])
        for p in ob.data.polygons:
            p.use_smooth = True
        return ob

    def tube(name, part, points, radius, material=None, sides=8, flatten=1.0):
        """Smooth round mesh tube through a sequence of world-space points."""
        pts = [Vector(p) for p in points]
        verts, faces = [], []
        for i, p in enumerate(pts):
            tangent = (pts[min(i + 1, len(pts)-1)] - pts[max(i - 1, 0)]).normalized()
            ref = Vector((0, 0, 1)) if abs(tangent.z) < 0.88 else Vector((0, 1, 0))
            a = tangent.cross(ref).normalized()
            b = tangent.cross(a).normalized()
            for j in range(sides):
                ang = 2 * math.pi * j / sides
                v = p + radius * (math.cos(ang) * a + flatten * math.sin(ang) * b)
                verts.append(tuple(v))
        for i in range(len(pts)-1):
            for j in range(sides):
                a = i*sides+j
                b = i*sides+(j+1)%sides
                faces.append((a, b, b+sides, a+sides))
        faces.append(tuple(range(sides-1, -1, -1)))
        end = (len(pts)-1)*sides
        faces.append(tuple(end+j for j in range(sides)))
        return mesh_obj(name, part, verts, faces, material or mats[part])

    def path_arc(center, rx, ry, z, start, end, n=40, wave=0.0):
        pts=[]
        for i in range(n):
            t=start+(end-start)*i/(n-1)
            pts.append((center[0]+(rx+wave*math.sin(5*t))*math.cos(t),
                        center[1]+(ry+wave*math.sin(5*t))*math.sin(t),
                        z+0.002*math.sin(3*t)))
        return pts

    def ellipsoid_shell(name, part, center, radii, view_dir, cutoff, zcut=-1.0, seg=64, rings=32, thickness=0.002):
        """A thin, genuinely open ellipsoid shell with a broad front/top viewing window."""
        c=Vector(center); vd=Vector(view_dir).normalized()
        verts=[]
        for inner in (False, True):
            s=1.0-(thickness/max(radii)) if inner else 1.0
            verts.append(tuple(c+Vector((0,0,-radii[2]*s))))
            for j in range(1,rings):
                lat=-math.pi/2+math.pi*j/rings
                for i in range(seg):
                    lon=2*math.pi*i/seg
                    q=Vector((math.cos(lat)*math.cos(lon), math.cos(lat)*math.sin(lon), math.sin(lat)))
                    p=c+Vector((q.x*radii[0]*s,q.y*radii[1]*s,q.z*radii[2]*s))
                    verts.append(tuple(p))
            verts.append(tuple(c+Vector((0,0,radii[2]*s))))
        faces=[]
        outer_faces=[]
        per_layer=(rings-1)*seg+2
        inner_offset=per_layer
        south=0
        north=per_layer-1
        def allowed(q):
            return not (q.dot(vd)>cutoff and q.z>zcut)
        # South-pole fan.
        for i in range(seg):
            ni=(i+1)%seg
            tri=(south,1+ni,1+i)
            q=Vector((0,0,-1))+Vector((math.cos(2*math.pi*(i+.5)/seg),math.sin(2*math.pi*(i+.5)/seg),0))
            if allowed(q.normalized()): outer_faces.append(tri)
        # Interior latitude bands.
        for j in range(rings-2):
            row0=1+j*seg
            row1=row0+seg
            for i in range(seg):
                ni=(i+1)%seg
                a=row0+i; b=row0+ni; d=row1+i; e=row1+ni
                for tri in ((a,b,e),(a,e,d)):
                    q=Vector((0,0,0))
                    for ix in tri:
                        p=Vector(verts[ix])-c
                        q += Vector((p.x/radii[0],p.y/radii[1],p.z/radii[2]))
                    if allowed(q.normalized()): outer_faces.append(tri)
        # North-pole fan.
        row=1+(rings-2)*seg
        for i in range(seg):
            ni=(i+1)%seg
            tri=(row+i,row+ni,north)
            q=Vector((0,0,1))+Vector((math.cos(2*math.pi*(i+.5)/seg),math.sin(2*math.pi*(i+.5)/seg),0))
            if allowed(q.normalized()): outer_faces.append(tri)
        faces.extend(outer_faces)
        faces.extend(tuple(inner_offset+ix for ix in reversed(face)) for face in outer_faces)
        # Join the two shell skins along each exposed cut edge.
        edge_count={}
        for f in outer_faces:
            for k in range(3):
                a,b=f[k],f[(k+1)%3]
                key=tuple(sorted((a,b)))
                edge_count[key]=edge_count.get(key,0)+1
        for (a,b),count in edge_count.items():
            if count==1:
                faces.append((a,b,inner_offset+b,inner_offset+a))
        return mesh_obj(name,part,verts,faces,mats[part])

    # Cell body: the upper/front opening faces the shared camera at (0.45,-0.60,0.55).
    camera_dir=(0.49,-0.65,0.58)
    ellipsoid_shell("Membrana plasmática • borde abierto", "membrana", (0,0,0), (.150,.132,.112), camera_dir, .48, -.42, 72, 36, .0025)

    # A shallow, pale cytosol basin grounds the interior while leaving the organelles exposed.
    verts=[]; faces=[]
    rings=9; seg=64
    verts.append((0,0,-.087))
    for j in range(1,rings+1):
        r=j/rings
        for i in range(seg):
            a=2*math.pi*i/seg
            z=-.087+.020*r*r+.002*math.sin(4*a)*r
            verts.append((.132*r*math.cos(a),.115*r*math.sin(a),z))
    for i in range(seg):
        faces.append((0,1+i,1+(i+1)%seg))
    for j in range(rings-1):
        row0=1+j*seg
        row1=row0+seg
        for i in range(seg):
            a=row0+i; b=row0+(i+1)%seg
            d=row1+i; e=row1+(i+1)%seg
            faces.extend(((a,b,e),(a,e,d)))
    mesh_obj("Citoplasma • plano basal", "citoplasma", verts, faces, mats["citoplasma"])

    # Nucleus occupies the rear-left half; its open cap reveals the nucleoplasm and nucleolus.
    nc=(-.030,.019,.015); nr=(.065,.057,.066)
    ellipsoid_shell("Envoltura nuclear • sección abierta", "nucleo", nc, nr, camera_dir, .31, -.35, 64, 32, .002)
    uv("Nucleoplasma visible", "nucleo", (-.025,-.010,.015), (.047,.021,.047), 32, 20)
    uv("Nucléolo", "nucleolo", (-.019,-.029,.024), (.017,.012,.019), 28, 18)

    # RER: three folded cisternae close around the nucleus, all facing the opening.
    rer_paths=[path_arc((-.031,.016),.076,.057,z,-2.78,1.95,42,.003) for z in (-.020,.001,.022)]
    for idx,pts in enumerate(rer_paths,1):
        # Nudge the front segment into view and keep the cisternae as distinct ribbons.
        pts=[(x,y-.007,z) for x,y,z in pts]
        tube("RER • cisterna %02d"%idx,"rer",pts,.0042,sides=8,flatten=.54)

    # REL is a smooth branching tubular network on the right-rear side, without ribosomes.
    rel_lines=[
        [(.022,.020,.012),(.049,.016,.018),(.072,.022,.016),(.090,.035,.009),(.104,.049,.006)],
        [(.050,.017,.017),(.061,-.001,.022),(.079,-.009,.025),(.099,-.006,.030)],
        [(.071,.022,.016),(.071,.043,.003),(.078,.062,-.003),(.095,.072,-.006)],
        [(.082,-.007,.025),(.091,-.024,.028),(.109,-.031,.023),(.119,-.022,.016)],
    ]
    for i,line in enumerate(rel_lines,1):
        tube("REL • túbulo %02d"%i,"rel",line,.0038,sides=8,flatten=.75)

    # Golgi: five curved, flattened cisternae with a clear stack and nearby budding vesicles.
    gc=(.025,-.042,.002)
    for i in range(5):
        z=-.019+i*.010
        pts=path_arc(gc,.033-i*.0015,.015,z,-.20,3.32,32,.001)
        tube("Golgi • cisterna %02d"%(i+1),"golgi",pts,.0042,sides=8,flatten=.45)

    # Mitochondria: two oval bodies; one has an open cutaway with a folded inner membrane.
    uv("Mitocondria • cuerpo 01", "mitocondrias", (.083,-.070,-.010), (.034,.016,.019), 32, 20)
    # Cutaway shell as a visible lower/back outline and internal folded cristae.
    mc=(-.091,-.066,-.022); mr=(.034,.018,.020)
    ellipsoid_shell("Mitocondria • pared abierta", "mitocondrias", mc, mr, camera_dir, -.12, -.15, 48, 24, .002)
    for i in range(4):
        x=mc[0]-.022+i*.014
        pts=[(x,-.064,-.010),(x-.005,-.055,-.014),(x+.003,-.051,-.020),(x-.004,-.055,-.027),(x+.003,-.063,-.032)]
        tube("Mitocondria • cresta %02d"%(i+1),"mitocondrias",pts,.0023,sides=7,flatten=.75)

    # Discrete lysosomes and vesicles keep the two small-compartment types distinct.
    for i,(p,s) in enumerate([
        ((.105,-.020,.048),.009),((-.112,-.010,.049),.008),((.017,.075,.046),.007)
    ],1):
        uv("Lisosoma %02d"%i,"lisosomas",p,(s,s*.88,s),20,12)
    for i,(p,s) in enumerate([
        ((.071,-.048,.043),.006),((.052,-.079,.025),.005),((-.105,-.039,.047),.005),
        ((.051,-.080,-.030),.0055),((.112,.004,-.020),.0045)
    ],1):
        uv("Vesícula %02d"%i,"vesiculas",p,(s,s,s),18,10)

    # Centrosome: two perpendicular short cylinders, modeled as meshes and placed near the nucleus.
    def cylinder_between(name, part, a, b, radius, vertices=16):
        a=Vector(a); b=Vector(b); vec=b-a
        bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=vec.length, location=(a+b)/2)
        ob=bpy.context.object; ob.name=name; ob["part_id"]=part
        ob.rotation_mode="QUATERNION"; ob.rotation_quaternion=vec.to_track_quat('Z','Y')
        ob.data.materials.append(mats[part])
        for p in ob.data.polygons: p.use_smooth=True
        return ob
    cen=(.043,.029,-.045)
    cylinder_between("Centríolo A","centrosoma",(cen[0]-.014,cen[1],cen[2]),(cen[0]+.014,cen[1],cen[2]),.0042)
    cylinder_between("Centríolo B","centrosoma",(cen[0],cen[1]-.014,cen[2]),(cen[0],cen[1]+.014,cen[2]),.0042)

    # A restrained set of cytoskeletal filaments, routed as independent curved strands.
    filaments=[
        [(-.128,-.017,-.045),(-.105,-.029,-.020),(-.084,-.041,.004),(-.064,-.063,.031)],
        [(.006,-.104,-.048),(.026,-.082,-.025),(.045,-.058,-.004),(.062,-.036,.018)],
        [(.115,-.052,-.052),(.097,-.043,-.029),(.085,-.032,-.006),(.071,-.015,.015)],
        [(-.034,.092,-.054),(-.025,.072,-.033),(-.014,.057,-.012),(.001,.045,.009)],
        [(-.111,.012,.056),(-.088,.008,.046),(-.072,.005,.032),(-.061,-.006,.019)],
        [(.033,.094,.004),(.042,.074,.014),(.048,.055,.023),(.053,.034,.034)],
    ]
    for i,line in enumerate(filaments,1):
        tube("Citoesqueleto • filamento %02d"%i,"citoesqueleto",line,.0017,sides=6,flatten=.8)

    labels={
        "membrana": (.129,-.046,.064),
        "citoplasma": (.008,-.102,-.075),
        "nucleo": (-.080,-.030,.046),
        "nucleolo": (-.019,-.040,.036),
        "ribosomas": (-.078,-.067,.017),
        "rer": (-.104,-.020,.007),
        "rel": (.099,.022,.020),
        "golgi": (.028,-.069,.022),
        "mitocondrias": (-.112,-.080,-.011),
        "lisosomas": (.105,-.020,.057),
        "centrosoma": (.057,.034,-.043),
        "vesiculas": (.071,-.048,.050),
        "citoesqueleto": (-.100,-.038,-.027),
    }
    # Small ribosomes are added last for visibility, free and attached along the RER.
    # Their geometry is part of the same educational category and stays within the mesh budget.
    for i in range(31):
        x=random.uniform(-.105,-.016)
        y=random.uniform(-.077,-.034)
        z=random.uniform(-.006,.031)
        # Avoid burying dots in the nucleus and keep a visibly scattered free population.
        if ((x-nc[0])/.067)**2+((y-nc[1])/.059)**2+((z-nc[2])/.068)**2 < 1.05:
            y-=.025
        uv("Ribosoma libre %02d"%(i+1),"ribosomas",(x,y,z),(.0026,.0026,.0026),12,8)
    # Adhered beads sit along the exposed front face of the rough cisternae.
    for i in range(20):
        t=i/19
        x=-.100+.076*t
        y=-.064-.006*math.sin(t*math.pi*2)
        z=-.019+.041*t
        uv("Ribosoma RER %02d"%(i+1),"ribosomas",(x,y,z),(.0027,.0027,.0027),12,8)

    return {
        "title": "Célula animal en corte abierto",
        "design_notes": "Maqueta ampliada de célula animal en interfase, abierta hacia el frente y arriba para que se distingan sus orgánulos. La envoltura nuclear y la membrana celular son cáscaras finas; el corte mitocondrial deja ver crestas internas. Las formas y cantidades son esquemáticas para secundaria.",
        "parts": {pid: {"label_position": list(pos)} for pid,pos in labels.items()},
    }
