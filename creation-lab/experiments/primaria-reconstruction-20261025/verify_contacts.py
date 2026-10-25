"""Verify actual hem-to-shoe contact in Blender source and clean GLB import."""
import argparse,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def inspect():
    bpy.context.view_layer.update()
    legs=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('part_id')=='trousers' and o.dimensions.z>.2]
    shoes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('part_id')=='shoes']
    checks=[]
    for leg in legs:
        verts=[leg.matrix_world@v.co for v in leg.data.vertices]
        # GLB splits positions at normals/materials; sample distinct geometry locations.
        verts=list({tuple(round(c,6) for c in v):v for v in verts}.values())
        midx=sum(v.x for v in verts)/len(verts)
        shoe=min(shoes,key=lambda s:abs(sum((s.matrix_world@v.co).x for v in s.data.vertices)/len(s.data.vertices)-midx))
        sv=[shoe.matrix_world@v.co for v in shoe.data.vertices]
        shoe.data.calc_loop_triangles()
        tree=BVHTree.FromPolygons(sv,[tuple(t.vertices) for t in shoe.data.loop_triangles],all_triangles=True)
        for side,y in [('front',min(v.y for v in verts)),('back',max(v.y for v in verts))]:
            hem=sorted([v for v in verts if abs(v.y-y)<1e-5],key=lambda v:v.z)[:2]
            hem=sorted(hem,key=lambda v:v.x)
            for t in [.2,.5,.8]:
                point=hem[0].lerp(hem[1],t)
                hit,normal,index,distance=tree.ray_cast(point+Vector((0,0,.2)),Vector((0,0,-1)),.5)
                gap=None if hit is None else point.z-hit.z
                checks.append({'leg':leg.name,'shoe':shoe.name,'side':side,'fraction':t,
                    'hem':list(point),'shoeTop':None if hit is None else list(hit),
                    'gapMeters':gap,'pass':gap is not None and -.04<gap<=.0002})
    return {'status':'PASS' if len(checks)==12 and all(x['pass'] for x in checks) else 'FAIL','checks':checks}
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--glb',required=True);p.add_argument('--output',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
out=Path(a.output)
if out.exists():raise SystemExit('Refusing to overwrite evidence')
bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()),load_ui=False,use_scripts=False)
source=inspect()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(Path(a.glb).resolve()))
gltf=inspect()
result={'status':'PASS' if source['status']==gltf['status']=='PASS' else 'FAIL',
    'method':'Downward BVH ray from 3 hem samples per front/back face on each actual mesh; tolerance 0.2mm; penetration at most40mm at conventional1m.',
    'source':source,'glb':gltf,'blender':bpy.app.version_string}
out.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'status':result['status'],'samplesPerArtifact':len(source['checks'])}))
if result['status']!='PASS':sys.exit(1)
