"""Identical build/reopen/reimport and CPU presentation for every condition."""
import argparse, copy, hashlib, importlib.util, json, math, random, sys, traceback
from pathlib import Path
import bpy
from mathutils import Vector

def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_module(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def point_at(obj, target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def presentation():
    scene=bpy.context.scene
    world=bpy.data.worlds.new('Benchmark studio');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(0.82,0.84,0.86,1)
    world.node_tree.nodes['Background'].inputs[1].default_value=0.7;scene.world=world
    for name,loc,power in [('Key',(-.45,-.55,.70),16),('Fill',(.50,-.10,.30),7),('Rim',(.10,.45,.55),10)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=.55
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=loc;point_at(obj,(0,0,0))
    data=bpy.data.cameras.new('Benchmark camera');obj=bpy.data.objects.new('Benchmark camera',data)
    scene.collection.objects.link(obj);scene.camera=obj;data.type='ORTHO';data.ortho_scale=.39
    data.clip_start=.0001;data.clip_end=100
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
    scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.render.resolution_x=scene.render.resolution_y=768;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    scene.render.film_transparent=False
    obj.location=(.45,-.60,.55);point_at(obj,(0,0,0))

VIEWS={'front':(0,-.7,.10),'side':(.7,0,.10),'back':(0,.7,.10),'three-quarter':(.45,-.60,.55),'wireframe':(.45,-.60,.55)}

def render(run, view, reimport=False):
    scene=bpy.context.scene;scene.camera.location=VIEWS[view];point_at(scene.camera,(0,0,0))
    modifiers=[]
    if view=='wireframe':
        for obj in list(scene.objects):
            if obj.type=='MESH':
                modifier=obj.modifiers.new('QA wires','WIREFRAME');modifier.thickness=.00018;modifier.use_replace=False
                modifiers.append((obj,modifier))
    name='reimport-three-quarter' if reimport else view
    scene.render.filepath=str(run/'renders'/(name+'.png'));bpy.ops.render.render(write_still=True)
    for obj,modifier in modifiers:obj.modifiers.remove(modifier)

def part_inventory(brief):
    expected={p['id'] for p in brief['parts']};inventory={key:[] for key in expected}
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH':
            key=obj.get('part_id')
            if key not in inventory:raise ValueError('Mesh lacks valid part_id: '+obj.name)
            inventory[key].append(obj.name)
    return inventory

def surface_quality(metrics):
    # Record authored degeneracy without deleting, welding, retriangulating or
    # changing source shading. It is evidence for a permitted technical repair.
    degenerate=sum((Vector(corners[1][0])-Vector(corners[0][0])).cross(
        Vector(corners[2][0])-Vector(corners[0][0])).length < 1e-14 for _,corners in metrics['surfaces'])
    return {'triangles':metrics['triangles'],'degenerateTriangles':degenerate,
            'doubleAreaThresholdM2':1e-14,'geometryRepair':'NOT_RUN'}

def roundtrip_diagnostics(geometry, before, after):
    full=geometry.compare_surfaces(before,after)
    result={'fullComparison':{'pass':full[0],'detail':full[1]},
            'sourceQuality':surface_quality(before),'importedQuality':surface_quality(after)}
    if not full[0]:
        left,right=copy.deepcopy(before),copy.deepcopy(after)
        for snapshot in (left,right):
            for _,corners in snapshot['surfaces']:
                for corner in corners:corner[2]=[0,0,1]
        diagnostic=geometry.compare_surfaces(left,right)
        result['positionsWindingMaterialsUVs']={'pass':diagnostic[0],'detail':diagnostic[1]}
        result['failureComponent']='shadingNormals' if diagnostic[0] else 'surfaceMaterialUVOrWinding'
        result['diagnosticOnly']=True
        result['approvalComparison']='full oriented surfaces including original shading normals; unchanged'
    return result

def main():
    args=sys.argv[sys.argv.index('--')+1:];stage=args[0];run=Path(args[1]).resolve()
    brief=json.loads((run/'brief.json').read_text(encoding='utf-8'))
    geometry=load_module('geometry_qa',run/'code/geometry_qa.py')
    if stage=='build':
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
        random.seed(brief['seed'])
        generator=load_module('condition_generator',run/'generator.py')
        result=generator.build();bpy.context.view_layer.update()
        if not isinstance(result,dict) or not isinstance(result.get('parts'),dict):raise ValueError('build must return metadata and parts')
        disallowed=[obj.name for obj in bpy.context.scene.objects if obj.type!='MESH']
        if disallowed:raise ValueError('Only final mesh geometry allowed: '+str(disallowed[:10]))
        inventory=part_inventory(brief)
        metrics=geometry.measure()
        write(run/'source-quality.json',surface_quality(metrics))
        # Persist evidence even when a generated artifact exceeds the budget.
        parts=[]
        for spec in brief['parts']:
            key=spec['id'];entry=result['parts'].get(key,{})
            point=entry.get('label_position')
            if not isinstance(point,(list,tuple)) or len(point)!=3 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in point):
                raise ValueError('Missing finite label_position for '+key)
            parts.append({**spec,'objects':inventory[key],'positionBlender':list(point),'positionGltf':[point[0],point[2],-point[1]]})
        write(run/'parts.json',{'title':result.get('title','Célula animal'),'designNotes':result.get('design_notes',''),'parts':parts})
        write(run/'source-surfaces.json',metrics)
        checks=[{'name':'all-parts','pass':all(inventory.values()),'actual':{k:len(v) for k,v in inventory.items()}},
                {'name':'triangle-budget','pass':metrics['triangles']<=brief['budgets']['triangles'],'actual':metrics['triangles']},
                {'name':'material-budget','pass':len(metrics['materials'])<=brief['budgets']['materials'],'actual':len(metrics['materials'])},
                {'name':'object-budget','pass':metrics['meshes']<=brief['budgets']['meshObjects'],'actual':metrics['meshes']},
                {'name':'display-size','pass':abs(max(metrics['dimensionsM'])-.30)<=.006,'actual':metrics['dimensionsM']},
                {'name':'static-meshes','pass':not bpy.data.actions,'actual':len(bpy.data.actions)},
                {'name':'no-pending-modifiers','pass':not any(obj.modifiers for obj in bpy.context.scene.objects),'actual':sum(len(obj.modifiers) for obj in bpy.context.scene.objects)}]
        write(run/'build-checks.json',{'checks':checks,'metrics':geometry.summary(metrics),'version':bpy.app.version_string})
        presentation();bpy.ops.wm.save_as_mainfile(filepath=str(run/'source.blend'),check_existing=False)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.context.scene.objects:
            if obj.type=='MESH':obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(run/'asset.glb'),export_format='GLB',use_selection=True,export_yup=True,
                                  export_animations=False,export_extras=True,export_cameras=False,export_lights=False)
        geometry.glb_document(run/'asset.glb')
        write(run/'build-result.json',{'status':'PASS' if all(x['pass'] for x in checks) else 'FAIL','blendSha256':digest(run/'source.blend'),'glbSha256':digest(run/'asset.glb')})
    elif stage=='reopen':
        bpy.ops.wm.open_mainfile(filepath=str(run/'source.blend'),load_ui=False,use_scripts=False)
        before=json.loads((run/'source-surfaces.json').read_text());after=geometry.measure();checks=[]
        geometry.compare(checks,'reopen',before,after)
        inventory=part_inventory(brief)
        if not all(inventory.values()):raise ValueError('Parts missing on reopen')
        (run/'renders').mkdir()
        for view in VIEWS:render(run,view)
        write(run/'reopen-result.json',{'status':'PASS' if all(c['status']=='passed' for c in checks) else 'FAIL','checks':checks,'metrics':geometry.summary(after),'blendSha256':digest(run/'source.blend'),'version':bpy.app.version_string})
    elif stage=='reimport':
        geometry.load(run/'asset.glb',static=True)
        before=json.loads((run/'source-surfaces.json').read_text());after=geometry.measure();checks=[]
        geometry.compare(checks,'reimport',before,after)
        diagnostics=roundtrip_diagnostics(geometry,before,after)
        inventory=part_inventory(brief)
        checks.append({'name':'all-parts-reimport','status':'passed' if all(inventory.values()) else 'failed','detail':inventory})
        presentation();render(run,'three-quarter',reimport=True)
        write(run/'reimport-result.json',{'status':'PASS' if all(c['status']=='passed' for c in checks) else 'FAIL','checks':checks,'diagnostics':diagnostics,'metrics':geometry.summary(after),'glbSha256':digest(run/'asset.glb'),'version':bpy.app.version_string})
    else:raise ValueError('Unknown stage')

if __name__=='__main__':
    try:main()
    except Exception:
        traceback.print_exc();sys.exit(1)
