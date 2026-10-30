#!/usr/bin/env python3
"""Create, inspect and validate local 3D Lab projects and immutable runs."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from studio import core, preview
from studio.adapters import providers, local


def _emit(data):
    print(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),flush=True)


def capabilities(args):
    return {'schemaVersion':1,'capabilities':[
        {'id':'procedural-web','implemented':True,'configured':(ROOT/'studio/web/dist/index.html').is_file(), 'verification':'See current test receipts; not a visual approval'},
        *providers.describe(args.settings),*local.describe(args.settings)],
        'paidExecution':'disabled unless an explicit bounded authorization is recorded', 'deployment':'manual and separate'}


def doctor(args):
    return {'status':'PASS','python':sys.version.split()[0],'root':str(ROOT),'workspace':str(args.workspace.resolve()),
        'previewBuilt':(ROOT/'studio/web/dist/index.html').is_file(),
        'capabilities':capabilities(args)['capabilities'],
        'scope':'configuration inspection; does not execute engines or verify provider accounts'}


def project_init(args):
    core._identifier(args.id)
    scene_path=args.scene or ROOT/'studio/examples/interactive.scene.json'
    scene=core.validate_record(core.read_json(scene_path))
    if scene['kind']!='scene': raise ValueError('scene record required')
    # Only built-ins can be initialized without a supplied source inventory.
    sources=[]
    for instance in scene['instances']:
        asset=instance['asset']
        if asset not in ('button','servo','character'):
            source=core.checked_path(scene_path.parent,asset)
            core.validate_glb(source)
            sources.append((asset,source))
    project=args.workspace.resolve()/'projects'/args.id
    if project.exists(): raise ValueError('project already exists; choose a new ID')
    project.mkdir(parents=True,exist_ok=False)
    core.write_json(project/'scene.json',scene)
    files=[{'path':'scene.json','sha256':core.sha256(project/'scene.json')}]
    copied={'scene.json'}
    for relative,source in sources:
        if relative in copied: continue
        target=core.checked_path(project,relative,False)
        target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,target)
        files.append({'path':relative,'sha256':core.sha256(target)}); copied.add(relative)
    manifest={'schemaVersion':1,'kind':'project','id':args.id,'title':scene['title'],'scene':'scene.json','files':files,
              'provenance':{'author':args.author,'license':args.license,'source':str(scene_path.resolve())}}
    core.validate_record(manifest)
    core.write_json(project/'project.json',manifest)
    run=core.create_run(args.workspace,'project.init',{'project':args.id,'sourceHash':core.sha256(scene_path)})
    core.record_event(run,{'status':'PASS','scope':'project structure and copy','project':str(project)})
    return {'status':'PASS','project':str(project),'run':str(run),'previewCommand':f'python studio/studio.py preview --project "{project}"'}


def validate(args):
    path=args.path.resolve()
    if path.suffix.lower()=='.glb':
        return {'status':'PASS',**core.validate_glb(path)}
    record=core.validate_record(core.read_json(path))
    kind=record['kind']
    if kind=='project':
        core.verify_inventory(path.parent,record['files'])
        scene=core.validate_record(core.read_json(core.checked_path(path.parent,record['scene'])))
        if scene['kind']!='scene': raise ValueError('project scene has wrong kind')
        inventory={item['path'] for item in record['files']}
        for instance in scene['instances']:
            asset=instance['asset']
            if asset not in ('button','servo','character'):
                if asset not in inventory: raise ValueError('scene asset is absent from inventory')
                core.validate_glb(core.checked_path(path.parent,asset))
    elif kind in ('asset','motion'): core.verify_inventory(path.parent,record['artifacts'])
    elif kind=='package': core.verify_inventory(path.parent,record['files'])
    return {'status':'PASS','kind':kind,'id':record['id'],'sha256':core.sha256(path),
            'scope':'structural and referenced-file integrity only; visual/content/provenance approval not implied'}


def run_list(args):
    directory=args.workspace/'runs'
    runs=[]
    if directory.exists():
        for path in sorted(directory.glob('*/run.json')):
            if path.is_symlink() or path.parent.is_symlink(): continue
            data=core.read_json(path)
            runs.append({'id':data['id'],'operation':data['operation'],'createdAt':data['createdAt'],'events':len(list((path.parent/'events').glob('*.json')))})
    return {'runs':runs}


def run_show(args):
    path=core.checked_path(args.workspace/'runs',args.id+'/run.json')
    return {'run':core.read_json(path),'events':[core.read_json(event) for event in sorted((path.parent/'events').glob('*.json'))]}


def serve(args):
    server=preview.make_server(ROOT/'studio/web/dist',args.project,args.port)
    url=f'http://127.0.0.1:{server.server_port}/'
    if server.scene_url: url+='?scene='+server.scene_url
    _emit({'status':'READY','url':url,'scope':'loopback allowlisted preview'})
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return {'status':'STOPPED'}


def package(args):
    return core.build_package(args.manifest.resolve().parent,core.read_json(args.manifest),args.output)


def parser():
    root=argparse.ArgumentParser(description=__doc__)
    root.add_argument('--workspace',type=Path,default=ROOT/'studio/.local')
    root.add_argument('--config',type=Path)
    commands=root.add_subparsers(dest='command',required=True)
    commands.add_parser('doctor',help='Inspect local configuration without invoking engines').set_defaults(handler=doctor)
    commands.add_parser('capabilities',help='List implemented routes and verification boundaries').set_defaults(handler=capabilities)
    project=commands.add_parser('project').add_subparsers(dest='project_command',required=True)
    init=project.add_parser('init',help='Create a new immutable-input project from a scene')
    init.add_argument('id'); init.add_argument('--scene',type=Path)
    init.add_argument('--author',default='local author'); init.add_argument('--license',default='UNREVIEWED')
    init.set_defaults(handler=project_init)
    runs=commands.add_parser('run').add_subparsers(dest='run_command',required=True)
    runs.add_parser('list').set_defaults(handler=run_list)
    show=runs.add_parser('show'); show.add_argument('id'); show.set_defaults(handler=run_show)
    check=commands.add_parser('validate'); check.add_argument('path',type=Path); check.set_defaults(handler=validate)
    view=commands.add_parser('preview'); view.add_argument('--project',type=Path); view.add_argument('--port',type=int,default=4395); view.set_defaults(handler=serve)
    pack=commands.add_parser('package'); pack.add_argument('--manifest',type=Path,required=True); pack.add_argument('--output',type=Path,required=True); pack.set_defaults(handler=package)
    providers.register_commands(commands); local.register_commands(commands)
    return root


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        args.settings=core.read_json(args.config) if args.config else {}
        args.workspace=args.workspace.resolve()
        result=args.handler(args)
        _emit(result)
        return 1 if isinstance(result,dict) and result.get('status') in ('FAIL','BLOCKED') else 0
    except (ValueError,OSError,KeyError,TypeError) as error:
        _emit({'status':'FAIL','error':str(error)})
        return 1

if __name__=='__main__': raise SystemExit(main())
