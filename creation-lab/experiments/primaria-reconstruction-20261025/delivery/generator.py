"""R2 authoritative silhouette blockout. build only, no I/O or scene settings."""
import bpy
import math
from components import material, mesh_object, sphere


def prism(name,part,poly,yfront,yback,mat):
    # poly is counterclockwise in XZ: front normal is -Y.
    if sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1] for i in range(len(poly))) < 0:
        poly=list(reversed(poly))
    n=len(poly)
    verts=[(x,yfront,z) for x,z in poly]+[(x,yback,z) for x,z in poly]
    faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]
    for i in range(n):
        j=(i+1)%n
        faces.append((i,n+i,n+j,j))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    ob=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(ob)
    ob['part_id']=part
    ob.data.materials.append(mat)
    return ob


def box(name,part,c,size,mat,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=c)
    ob=bpy.context.object
    ob.name=name
    ob.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    ob['part_id']=part
    ob.data.materials.append(mat)
    if bevel:
        mod=ob.modifiers.new('Papercraft cut corners','BEVEL')
        mod.width=bevel;mod.segments=1
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return ob


def ringmesh(name,part,rings,mat,top=None):
    n=len(rings[0]); verts=[v for ring in rings for v in ring]
    faces=[tuple(reversed(range(n)))]
    for k in range(len(rings)-1):
        for i in range(n):
            j=(i+1)%n
            faces.append((k*n+i,k*n+j,(k+1)*n+j,(k+1)*n+i))
    start=(len(rings)-1)*n
    if top is None:faces.append(tuple(range(start,start+n)))
    else:
        ti=len(verts);verts.append(top)
        for i in range(n):faces.append((start+i,start+(i+1)%n,ti))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
    ob['part_id']=part;ob.data.materials.append(mat)
    return ob


def octring(x,yf,yb,z,ch=.25):
    return [(-x*(1-ch),-yf,z),(x*(1-ch),-yf,z),(x,-yf*(1-ch),z),(x,yb*(1-ch),z),(x*(1-ch),yb,z),(-x*(1-ch),yb,z),(-x,yb*(1-ch),z),(-x,-yf*(1-ch),z)]


def build():
    skin=material('Piel dorada R2',(1.0,.38,.05),roughness=.85)
    hair=material('Cabello berenjena',(.025,.006,.055),roughness=.9)
    purple=material('Chaleco violeta',(.115,.008,.29),roughness=.9)
    white=material('Camisa marfil',(.93,.89,.91),roughness=.9)
    blue=material('Pantalon indigo',(.015,.036,.14),roughness=.9)
    cyan=material('Mochila cian',(.003,.47,.64),roughness=.8)
    shoe=material('Zapatos ciruela',(.022,.007,.043),roughness=.9)
    navy=material('Ojos y sonrisa azul noche',(.004,.014,.038),roughness=.8)
    # Continuous cheek/chin volume: broad front with sloping clipped sides.
    ringmesh('Cabeza mejillas y menton','head',[
        octring(.074,.078,.063,.693,.22),
        octring(.118,.092,.083,.714,.22),
        octring(.137,.092,.098,.775,.20),
        octring(.132,.092,.105,.860,.20),
        octring(.103,.069,.088,.911,.25)],skin)
    box('Cuello','neck',(0,0,.681),(.068,.071,.069),skin,.009)
    for s in (-1,1):
        prism('Oreja '+str(s),'ears',[(s*x,z) for x,z in ([(.119,.742),(.147,.737),(.169,.758),(.169,.792),(.145,.807),(.124,.791)] if s==1 else list(reversed([(.119,.742),(.147,.737),(.169,.758),(.169,.792),(.145,.807),(.124,.791)])))],-.027,.035,skin)
    # One closed sculptural hair envelope. Varying X,Y,Z rings avoid extrusion terraces.
    lower=[(-.12,-.102,.85),(-.035,-.115,.825),(.108,-.10,.888),
           (.145,-.041,.796),(.140,.080,.761),(.082,.109,.727),
           (-.082,.109,.727),(-.140,.080,.761),(-.161,-.02,.785),(-.14,-.09,.817)]
    upper=[(-.103,-.083,.960),(-.025,-.102,.961),(.112,-.078,.945),
           (.166,-.017,.916),(.145,.089,.927),(.078,.134,.933),
           (-.078,.134,.933),(-.146,.089,.927),(-.170,-.017,.895),(-.151,-.076,.927)]
    ringmesh('Casco continuo y flequillo diagonal','hair',[lower,upper],hair,top=(0,.015,1.0))
    # Vest expands slightly toward hem, matching wide boxy school uniform.
    prism('Chaleco','vest',[(-.118,.413),(.118,.413),(.109,.613),(.073,.676),(-.073,.676),(-.109,.613)],-.063,.066,purple)
    # White throat triangle and folded collar distinct from vest.
    prism('Abertura blanca V','collar',[(-.067,.678),(0,.571),(.067,.678)],-.073,-.064,white)
    prism('Cuello izquierdo','collar',[(-.073,.678),(-.014,.661),(-.049,.607),(-.083,.66)],-.086,-.073,white)
    prism('Cuello derecho','collar',[(.014,.661),(.073,.678),(.083,.66),(.049,.607)],-.086,-.073,white)
    for s in (-1,1):
        poly=[(.084,.665),(.126,.654),(.199,.535),(.119,.493),(.094,.573)]
        if s<0:poly=list(reversed(poly))
        sleeve=prism('Manga ancha '+str(s),'shirt',[(s*x,z) for x,z in poly],-.069,.07,white)
        bpy.context.view_layer.objects.active=sleeve
        bevel=sleeve.modifiers.new('Doblez manga','BEVEL');bevel.width=.010;bevel.segments=1
        bpy.ops.object.modifier_apply(modifier=bevel.name)
        poly=[(.135,.512),(.178,.533),(.214,.416),(.189,.398),(.156,.409)]
        if s<0:poly=list(reversed(poly))
        prism('Antebrazo inclinado '+str(s),'arms',[(s*x,z) for x,z in poly],-.044,.036,skin)
        poly=[(.188,.417),(.216,.426),(.228,.375),(.209,.344),(.190,.328),(.165,.349),(.158,.381)]
        if s<0:poly=list(reversed(poly))
        prism('Mano poligonal '+str(s),'hands',[(s*x,z) for x,z in poly],-.055,.039,skin)
        poly=[(.008,.412),(.111,.412),(.142,.079),(.026,.075)]
        if s<0:poly=list(reversed(poly))
        prism('Pierna pantalon '+str(s),'trousers',[(s*x,z) for x,z in poly],-.052,.064,blue)
        # Toe slopes upward into ankle; octagonal footprint preserves broad R2 shoe.
        x=s*.104
        outline=[(-.062,-.131),(.062,-.131),(.0775,-.114),(.0775,.055),(.060,.077),(-.060,.077),(-.0775,.055),(-.0775,-.114)]
        low=[(x+dx,y,.0) for dx,y in outline]
        mid=[(x+dx,y,.012) for dx,y in outline]
        top=[(x+dx*.94,y+.003,.079 if y<-.05 else .095) for dx,y in outline]
        ringmesh('Zapato cuna '+str(s),'shoes',[low,mid,top],shoe)
    box('Cadera interior sin coplanares','trousers',(0,.006,.395),(.215,.106,.035),blue,.003)
    # Broad flat backpack in rear view; protrudes in profile below shoulder.
    box('Mochila volumen','backpack',(0,.119,.526),(.214,.119,.242),cyan,.018)
    box('Bolsillo mochila','backpack',(0,.189,.493),(.190,.033,.161),cyan,.012)
    for s in (-1,1):
        poly=[(.081,.426),(.104,.433),(.103,.641),(.081,.665)]
        if s<0:poly=list(reversed(poly))
        prism('Tirante pecho '+str(s),'straps',[(s*x,z) for x,z in poly],-.080,-.067,cyan)
        # Joined shoulder arc sampled along y, no horizontal frame behind the neck.
        rings=[]
        arc=[(-.073,.650),(-.045,.671),(.004,.679),(.050,.672),(.088,.650),(.111,.620)]
        for k,(y,z) in enumerate(arc):
            ya,za=arc[max(0,k-1)];yb,zb=arc[min(len(arc)-1,k+1)]
            dy=yb-ya;dz=zb-za;length=math.sqrt(dy*dy+dz*dz)
            ny=-dz/length*.005;nz=dy/length*.005;x=s*.091;w=.015
            rings.append([(x-w,y-ny,z-nz),(x-w,y+ny,z+nz),(x+w,y+ny,z+nz),(x+w,y-ny,z-nz)])
        ringmesh('Tirante curvo hombro '+str(s),'straps',rings,cyan)
    # Small faithful face: navy oval eyes and a constant-width U-shaped smile.
    for sign in (-1,1):
        mesh_object('Ojo ovalado '+str(sign),'head',sphere((.0125,.001,.016),center=(sign*.050,-.0928,.781),segments=16,rings=8),navy,smooth=True)
    curve=bpy.data.curves.new('Sonrisa curva constante','CURVE');curve.dimensions='3D'
    curve.resolution_u=1;curve.bevel_depth=.0026;curve.bevel_resolution=3;curve.use_fill_caps=True
    path=curve.splines.new('POLY');path.points.add(12)
    for k in range(13):
        x=-.0275+.055*k/12;z=.733+.009*(x/.0275)**2
        path.points[k].co=(x,-.095,z,1)
    smile=bpy.data.objects.new('Sonrisa amable',curve);bpy.context.collection.objects.link(smile)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active=smile;smile.select_set(True)
    bpy.ops.object.convert(target='MESH');smile=bpy.context.object;smile['part_id']='head';smile.data.materials.append(navy)
    for ob in bpy.context.scene.objects:
        if ob.type=='MESH' and ob['part_id'] in ('hands','ears'):
            bpy.context.view_layer.objects.active=ob
            mod=ob.modifiers.new('Pliegue papercraft','BEVEL');mod.width=.0035;mod.segments=1
            bpy.ops.object.modifier_apply(modifier=mod.name)
    # A narrow raised central vest fold; same pigment, no decorative added symbols.
    box('Pliegue central chaleco','vest',(0,-.0645,.499),(.0018,.002,.169),purple,.0003)
    labels={'head':[0,-.09,.8],'ears':[.16,0,.77],'neck':[0,0,.68],'hair':[0,0,.95],'vest':[0,-.08,.52],'shirt':[.16,0,.57],'collar':[0,-.09,.65],'arms':[.18,0,.46],'hands':[.2,0,.37],'trousers':[.07,0,.25],'shoes':[.1,-.06,.05],'backpack':[0,.19,.53],'straps':[.09,-.08,.59]}
    # Common presentation cameras target origin; preserve 1m height and center it.
    for ob in bpy.context.scene.objects:
        if ob.type=='MESH':
            ob.location.z-=.5
    labels={key:[v[0],v[1],v[2]-.5] for key,v in labels.items()}
    return {'title':'Alumno primaria GuateGeeks R2 - reconstruccion detallada','design_notes':['Autoridad: imagen completa R2, no JSON/R3.','Escala convencional 1m. Rostro ovalado y sonrisa curva; sin nariz inventada.','Planos anchos, flequillo diagonal, brazos abiertos y mochila saliente.'], 'parts':{p:{'label_position':v} for p,v in labels.items()}}
