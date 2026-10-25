"""R2 authoritative silhouette blockout. build only, no I/O or scene settings."""
import bpy
import math
from components import material


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


def build():
    skin=material('Piel dorada R2',(0.93,.49,.17),roughness=.85)
    hair=material('Cabello berenjena',(.105,.038,.19),roughness=.9)
    purple=material('Chaleco violeta',(.235,.025,.47),roughness=.9)
    white=material('Camisa marfil',(.93,.89,.91),roughness=.9)
    blue=material('Pantalon indigo',(.035,.075,.25),roughness=.9)
    cyan=material('Mochila cian',(.005,.57,.70),roughness=.8)
    shoe=material('Zapatos ciruela',(.105,.047,.17),roughness=.9)
    # Broad face with clipped temple/chin corners; not spherical.
    prism('Cara octogonal','head',[(-.089,.693),(.089,.693),(.119,.714),(.137,.772),(.133,.867),(.097,.91),(-.102,.91),(-.137,.86),(-.137,.768),(-.118,.715)],-.082,.087,skin)
    box('Cuello','neck',(0,0,.681),(.068,.071,.069),skin,.009)
    for s in (-1,1):
        prism('Oreja '+str(s),'ears',[(s*x,z) for x,z in ([(.119,.742),(.147,.737),(.169,.758),(.169,.792),(.145,.807),(.124,.791)] if s==1 else list(reversed([(.119,.742),(.147,.737),(.169,.758),(.169,.792),(.145,.807),(.124,.791)])))],-.027,.035,skin)
    # Back cap with crown apex at exact 1m. Large diagonal frontal plane.
    prism('Casco poligonal posterior','hair',[(-.135,.782),(.135,.782),(.165,.867),(.170,.918),(.12,.966),(0,1),(-.105,.968),(-.17,.895)],-.019,.135,hair)
    prism('Gran flequillo diagonal','hair',[(-.17,.895),(-.142,.809),(-.115,.839),(-.035,.825),(.108,.888),(.126,.934),(.02,.974),(-.105,.968)],-.108,-.018,hair)
    prism('Patilla derecha','hair',[(.119,.791),(.143,.81),(.17,.918),(.126,.934),(.105,.892)],-.077,.078,hair)
    prism('Patilla izquierda','hair',[(-.17,.895),(-.147,.78),(-.12,.821),(-.114,.874)],-.077,.078,hair)
    # Vest expands slightly toward hem, matching wide boxy school uniform.
    prism('Chaleco','vest',[(-.118,.413),(.118,.413),(.109,.613),(.073,.676),(-.073,.676),(-.109,.613)],-.063,.066,purple)
    # White throat triangle and folded collar distinct from vest.
    prism('Abertura blanca V','collar',[(-.067,.678),(0,.571),(.067,.678)],-.073,-.064,white)
    prism('Cuello izquierdo','collar',[(-.073,.678),(-.014,.661),(-.049,.607),(-.083,.66)],-.086,-.073,white)
    prism('Cuello derecho','collar',[(.014,.661),(.073,.678),(.083,.66),(.049,.607)],-.086,-.073,white)
    for s in (-1,1):
        poly=[(.084,.665),(.126,.654),(.199,.535),(.119,.493),(.094,.573)]
        if s<0:poly=list(reversed(poly))
        prism('Manga ancha '+str(s),'shirt',[(s*x,z) for x,z in poly],-.069,.07,white)
        poly=[(.135,.512),(.178,.533),(.214,.416),(.189,.398),(.156,.409)]
        if s<0:poly=list(reversed(poly))
        prism('Antebrazo inclinado '+str(s),'arms',[(s*x,z) for x,z in poly],-.044,.036,skin)
        poly=[(.188,.417),(.216,.426),(.228,.375),(.209,.344),(.190,.328),(.165,.349),(.158,.381)]
        if s<0:poly=list(reversed(poly))
        prism('Mano poligonal '+str(s),'hands',[(s*x,z) for x,z in poly],-.055,.039,skin)
        poly=[(.008,.412),(.111,.412),(.142,.089),(.026,.082)]
        if s<0:poly=list(reversed(poly))
        prism('Pierna pantalon '+str(s),'trousers',[(s*x,z) for x,z in poly],-.052,.064,blue)
        box('Zapato ancho '+str(s),'shoes',(s*.104,-.027,.043),(.155,.208,.086),shoe,.016)
    box('Cadera pantalon','trousers',(0,.007,.395),(.224,.114,.069),blue,.004)
    # Broad flat backpack in rear view; protrudes in profile below shoulder.
    box('Mochila volumen','backpack',(0,.119,.526),(.214,.119,.242),cyan,.018)
    box('Bolsillo mochila','backpack',(0,.189,.493),(.190,.033,.161),cyan,.012)
    for s in (-1,1):
        prism('Tirante pecho '+str(s),'straps',[(s*x,z) for x,z in ([(.082,.485),(.105,.487),(.104,.671),(.075,.678)] if s==1 else list(reversed([(.082,.485),(.105,.487),(.104,.671),(.075,.678)])))],-.079,-.063,cyan)
        box('Tirante hombro '+str(s),'straps',(s*.089,.026,.67),(.031,.208,.026),cyan,.002)
    labels={'head':[0,-.09,.8],'ears':[.16,0,.77],'neck':[0,0,.68],'hair':[0,0,.95],'vest':[0,-.08,.52],'shirt':[.16,0,.57],'collar':[0,-.09,.65],'arms':[.18,0,.46],'hands':[.2,0,.37],'trousers':[.07,0,.25],'shoes':[.1,-.06,.05],'backpack':[0,.19,.53],'straps':[.09,-.08,.59]}
    # Common presentation cameras target origin; preserve 1m height and center it.
    for ob in bpy.context.scene.objects:
        if ob.type=='MESH':
            ob.location.z-=.5
    labels={key:[v[0],v[1],v[2]-.5] for key,v in labels.items()}
    return {'title':'Alumno primaria GuateGeeks R2 · blockout fiel','design_notes':['Autoridad: imagen completa R2, no JSON/R3.','Escala de trabajo convencional 1m. Rostro detallado pendiente.','Planos anchos, flequillo diagonal, brazos abiertos y mochila saliente.'], 'parts':{p:{'label_position':v} for p,v in labels.items()}}
