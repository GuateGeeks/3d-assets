"""Generador procedural original de una célula animal didáctica abierta."""
import bpy
import math
import random
from mathutils import Vector

random.seed(20261022)
MATS = {}


def mat(name, color, rough=.45, metal=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*color, 1)
    bs.inputs["Roughness"].default_value = rough
    bs.inputs["Metallic"].default_value = metal
    MATS[name] = m
    return m


C = {
    "mem": mat("Membrana · coral", (.78,.27,.29),.34),
    "cyto": mat("Citosol · marfil", (.88,.72,.48),.74),
    "nuc": mat("Núcleo · azul petróleo", (.16,.36,.49)),
    "lumen": mat("Lumen nuclear", (.27,.51,.60),.55),
    "nucl": mat("Nucléolo · ocre", (.92,.55,.22),.4),
    "rer": mat("RER · jade", (.20,.52,.43)), "rel": mat("REL · verde", (.39,.68,.49)),
    "rib": mat("Ribosomas · tinta", (.10,.17,.18),.35),
    "golgi": mat("Golgi · lavanda", (.55,.39,.67)), "ves": mat("Vesículas · lila", (.76,.59,.80),.35),
    "mito": mat("Mitocondria · ámbar", (.91,.47,.19),.38), "crest": mat("Crestas · crema", (1,.79,.43),.4),
    "lyso": mat("Lisosoma · granate", (.66,.25,.34)), "cent": mat("Centríolos · azul", (.23,.47,.72),.35),
    "skel": mat("Citoesqueleto · cobre", (.55,.30,.16),.42),
}


def mesh(name, verts, faces, part, material):
    me=bpy.data.meshes.new(name+"_mesh"); me.from_pydata(verts,[],faces); me.materials.append(material); me.update()
    ob=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(ob); ob["part_id"]=part
    for p in me.polygons: p.use_smooth=True
    return ob


def sphere(name, loc, scale, part, material, seg=18, rings=12):
    # Un vértice por polo evita los anillos de radio cero y sus triángulos
    # degenerados al triangular/exportar. Los anillos intermedios conservan
    # exactamente la misma parametrización y silueta esférica.
    v=[(loc[0],loc[1],loc[2]+scale[2])]; f=[]
    for j in range(1,rings):
        a=math.pi*j/rings
        for i in range(seg):
            b=2*math.pi*i/seg
            v.append((loc[0]+scale[0]*math.sin(a)*math.cos(b),loc[1]+scale[1]*math.sin(a)*math.sin(b),loc[2]+scale[2]*math.cos(a)))
    south=len(v); v.append((loc[0],loc[1],loc[2]-scale[2]))
    first=1
    for i in range(seg):
        n=(i+1)%seg
        f.append((0,first+n,first+i))
    for j in range(rings-2):
        for i in range(seg):
            n=(i+1)%seg; q=first+j*seg+i
            f.append((q,q+1 if i+1<seg else q+1-seg,q+1+seg if i+1<seg else q+1, q+seg))
    last=first+(rings-2)*seg
    for i in range(seg):
        n=(i+1)%seg
        f.append((last+i,last+n,south))
    return mesh(name,v,f,part,material)


def tube(name, points, radius, part, material, sides=8, closed=False):
    pts=[Vector(p) for p in points]; v=[]; f=[]
    for k,p in enumerate(pts):
        tangent=(pts[(k+1)%len(pts)]-pts[(k-1)%len(pts)]).normalized() if closed else (pts[min(k+1,len(pts)-1)]-pts[max(k-1,0)]).normalized()
        ref=Vector((0,0,1)) if abs(tangent.z)<.88 else Vector((0,1,0)); u=tangent.cross(ref).normalized(); w=tangent.cross(u).normalized()
        for s in range(sides): v.append(tuple(p+radius*(u*math.cos(2*math.pi*s/sides)+w*math.sin(2*math.pi*s/sides))))
    for k in range(len(pts) if closed else len(pts)-1):
        kn=(k+1)%len(pts)
        for s in range(sides):
            sn=(s+1)%sides; f.append((k*sides+s,k*sides+sn,kn*sides+sn,kn*sides+s))
    if not closed: f += [tuple(reversed(range(sides))),tuple((len(pts)-1)*sides+s for s in range(sides))]
    return mesh(name,v,f,part,material)


def shell():
    # Cáscara elipsoidal fina en paneles; una gran cuña frontal/alta queda abierta.
    v=[]; f=[]; na,nb=18,40; a0,a1=.40,2.80
    for start,end in ((.20,1.10),(2.05,5.95)):
        base=len(v)
        for layer in (1,.955):
            for j in range(na+1):
                a=a0+(a1-a0)*j/na
                for i in range(nb+1):
                    b=start+(end-start)*i/nb
                    v.append((.150*layer*math.sin(a)*math.cos(b),.124*layer*math.sin(a)*math.sin(b),.116*layer*math.cos(a)))
        grid=(na+1)*(nb+1)
        for layer in range(2):
            off=base+layer*grid
            for j in range(na):
                for i in range(nb):
                    q=off+j*(nb+1)+i; f.append((q,q+1,q+nb+2,q+nb+1) if layer==0 else (q,q+nb+1,q+nb+2,q+1))
        for j in (0,na):
            for i in range(nb):
                q=base+j*(nb+1)+i; f.append((q,q+1,q+grid+1,q+grid))
        for i in (0,nb):
            for j in range(na):
                q=base+j*(nb+1)+i; f.append((q,q+nb+1,q+grid+nb+1,q+grid))
    mesh("membrana__panel_abierto",v,f,"membrana",C["mem"])


def build():
    sphere("citoplasma__volumen",(0,0,0),(.137,.112,.104),"citoplasma",C["cyto"],36,24)
    shell()
    nuc=(-.030,.021,.018)
    sphere("nucleo__cuerpo",nuc,(.060,.055,.052),"nucleo",C["nuc"],28,18)
    sphere("nucleo__lumen_visible",(-.025,-.026,.028),(.035,.018,.030),"nucleo",C["lumen"],22,14)
    sphere("nucleolo__sin_membrana",(-.035,-.032,.028),(.016,.014,.015),"nucleolo",C["nucl"],20,14)
    for i,a in enumerate((-.95,-.42,.18,.72,1.25,2.15)):
        sphere("nucleo__poro_%02d"%i,(nuc[0]+.058*math.cos(a),nuc[1]-.005,nuc[2]+.045*math.sin(a)),(.0032,)*3,"nucleo",C["lumen"],10,6)

    # Cisternas rugosas circundantes al núcleo; los ribosomas miran al citosol.
    for k in range(3):
        y=-.004-.012*k; pts=[(-.091+q*.022,y,.052+.004*math.sin(q*math.pi)) for q in range(5)]
        tube("rer__cisterna_%02d"%k,pts,.0048,"rer",C["rer"],10)
        for i in range(5): sphere("ribosomas__rer_%02d_%02d"%(k,i),(-.088+i*.018,y-.0045,.056),(.0025,)*3,"ribosomas",C["rib"],8,6)
    for k in range(3):
        pts=[(.035+.048*t,.010-.008*k+.008*math.sin(t*math.pi*2+k),.044-.018*t) for t in [i/8 for i in range(9)]]
        tube("rel__tubulo_%02d"%k,pts,.0034,"rel",C["rel"],8)

    # Aparato de Golgi como pila de cisternas curvas y aplanadas.
    for layer in range(5):
        z=-.018+layer*.009; pts=[]
        for i in range(17):
            t=i/16; pts.append((-.005+.055*t,-.044-.009*math.sin(math.pi*t)+layer*.001,z+.006*math.sin(math.pi*t)))
        tube("golgi__cisterna_%02d"%layer,pts,.0033,"golgi",C["golgi"],10)
    for i,p in enumerate(((.060,-.050,-.006),(.064,-.047,.004),(-.012,-.048,.025))): sphere("vesiculas__golgi_%02d"%i,p,(.007,.006,.007),"vesiculas",C["ves"],14,9)

    def mito(center,size,idx,open_cut):
        sphere("mitocondrias__cuerpo_%02d"%idx,center,size,"mitocondrias",C["mito"],24,14)
        for j in range(4 if open_cut else 2):
            z=center[2]+(j-1.5)*.006; pts=[]
            for i in range(9):
                t=i/8; pts.append((center[0]-size[0]*.68+size[0]*1.36*t,center[1]-size[1]*.79,z+.003*math.sin(t*math.pi*3+j*1.1)))
            tube("mitocondrias__cresta_%02d_%02d"%(idx,j),pts,.0017 if open_cut else .0014,"mitocondrias",C["crest"],7)
    mito((.065,-.004,.018),(.030,.014,.012),0,True)
    mito((-.080,-.047,-.028),(.023,.012,.010),1,False)
    mito((.012,.066,-.048),(.020,.011,.009),2,False)

    for i,p in enumerate(((-.076,-.078,.018),(.085,-.066,-.025),(.085,.027,.050))):
        sphere("lisosomas__vesicula_%02d"%i,p,(.010,.009,.010),"lisosomas",C["lyso"],16,10)
        sphere("lisosomas__enzima_%02d"%i,(p[0]-.002,p[1]-.007,p[2]+.002),(.003,.002,.003),"lisosomas",C["nucl"],10,6)

    # Centrosoma: pareja perpendicular de barriles estriados.
    origin=Vector((-.086,.025,-.004))
    sphere("centrosoma__matriz",origin,(.009,)*3,"centrosoma",C["cent"],16,10)
    def centriole(axis,idx):
        vaxis=Vector(axis).normalized(); start=origin-vaxis*.014; u=vaxis.cross(Vector((0,0,1))).normalized(); w=vaxis.cross(u).normalized()
        vv=[]; ff=[]; sides=12; length=.028; rad=.0042
        for end in (0,1):
            for i in range(sides):
                a=2*math.pi*i/sides; vv.append(tuple(start+vaxis*(length*end)+rad*(u*math.cos(a)+w*math.sin(a))))
        for i in range(sides):
            n=(i+1)%sides; ff.append((i,n,sides+n,sides+i))
        ff += [tuple(reversed(range(sides))),tuple(range(sides,2*sides))]
        mesh("centrosoma__centriolo_%02d"%idx,vv,ff,"centrosoma",C["cent"])
        for i in range(9):
            a=2*math.pi*i/9; p=start+rad*1.02*(u*math.cos(a)+w*math.sin(a))
            tube("centrosoma__microtubulo_%02d_%02d"%(idx,i),(p,p+vaxis*length),.00065,"centrosoma",C["crest"],5)
    centriole((1,0,.08),0); centriole((0,.15,1),1)

    for i,p in enumerate(((-.053,-.075,.043),(.013,-.084,.067),(.092,-.023,.026),(-.101,-.012,-.035),(.039,.038,.069),(-.023,.079,-.006))):
        sphere("ribosomas__libre_%02d"%i,p,(.0027,)*3,"ribosomas",C["rib"],9,6)
    for i,p in enumerate(((.098,-.035,.060),(.047,-.083,-.055),(-.012,-.095,.011),(.098,.023,-.004),(-.060,.065,.056))):
        sphere("vesiculas__libre_%02d"%i,p,(.006,)*3,"vesiculas",C["ves"],12,8)

    paths=[
      [(-.113,-.045,-.012),(-.080,-.055,.003),(-.040,-.066,.012),(.004,-.071,.021),(.046,-.066,.034)],
      [(-.100,.018,-.055),(-.065,.004,-.043),(-.022,-.006,-.050),(.022,-.004,-.060),(.064,.012,-.058)],
      [(-.045,.070,.054),(-.012,.055,.046),(.025,.047,.032),(.063,.045,.018),(.101,.042,.003)],
    ]
    for i,p in enumerate(paths): tube("citoesqueleto__filamento_%02d"%i,p,.00115,"citoesqueleto",C["skel"],6)

    return {"title":"Célula animal · corte didáctico",
      "design_notes":"Maqueta oval de 30 cm, con una cuña amplia abierta hacia el frente y el techo. Paleta cálida y contrastada; núcleo al fondo, RER y REL separados, Golgi apilado y mitocondrias con pliegues internos visibles. Cada malla conserva su part_id.",
      "parts":{
        "membrana":{"label_position":[.105,-.075,.084]}, "citoplasma":{"label_position":[.105,-.040,-.072]},
        "nucleo":{"label_position":[-.030,-.035,.045]}, "nucleolo":{"label_position":[-.035,-.046,.035]},
        "ribosomas":{"label_position":[.013,-.086,.067]}, "rer":{"label_position":[-.070,-.012,.056]},
        "rel":{"label_position":[.065,.008,.035]}, "golgi":{"label_position":[.024,-.052,.009]},
        "mitocondrias":{"label_position":[.065,-.015,.025]}, "lisosomas":{"label_position":[.085,-.073,-.021]},
        "centrosoma":{"label_position":[-.086,.025,.002]}, "vesiculas":{"label_position":[.098,-.039,.063]},
        "citoesqueleto":{"label_position":[.020,-.004,-.052]}}}
