import tempfile
from pathlib import Path
import unittest
from studio.adapters import local
from studio.adapters.retarget import convert_vector, validate_mapping

class LocalTests(unittest.TestCase):
    def test_axis(self):
        self.assertEqual(convert_vector([1,2,3], 'Z_UP', 'Y_UP'), [1,3,-2])
        self.assertEqual(convert_vector([1,3,-2], 'Y_UP', 'Z_UP'), [1,2,3])
        with self.assertRaises(ValueError): convert_vector([1,2,3], 'guess', 'Y_UP')
    def test_mapping(self):
        with self.assertRaises(ValueError): validate_mapping({'Hips':'pelvis','Spine':'pelvis'}, ['Hips','Spine'], ['pelvis'])
        with self.assertRaises(ValueError): validate_mapping({'Hips':'pelvis'}, [], ['pelvis'])
    def test_route(self):
        self.assertEqual(local.rig_route({'armatures':1}, False), 'preserve-rig')
        self.assertEqual(local.rig_route({'armatures':0}, False), 'organic-inference')
        self.assertEqual(local.rig_route({'armatures':0}, True), 'rigid-animation')
    def test_profile_vram(self):
        p = dict(local.default_profile(), repositoryRoot='/tmp/skin', python='/tmp/python', checkpoint='/tmp/ckpt', hfPath='/tmp/config')
        with self.assertRaises(ValueError): local.validate_profile(dict(p, host='host;touch BAD', executor='ssh'))
        with self.assertRaises(ValueError): local.validate_profile(dict(p, repositoryRoot='/tmp/../escape'))
        with self.assertRaises(ValueError): local.check_vram('8192,8000')
        self.assertEqual(local.check_vram('24576,20000')['freeMiB'],20000)
    def test_missing_input(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): local.blender_command({'python':'/usr/bin/python3'}, Path(d)/'absent.glb', Path(d), 'inspect')
    def test_dry_command(self):
        p = dict(local.default_profile(), repositoryRoot='/tmp/skin', python='/tmp/python', checkpoint='/tmp/ckpt', hfPath='/tmp/config')
        cmd=local.skin_command(p,'/tmp/input.glb','/tmp/output.glb',True)
        self.assertIn('--use_skeleton',cmd); self.assertIn('--use_transfer',cmd)
        self.assertEqual(cmd[1],'/tmp/skin/demo.py')
    def test_hash_intake(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); src=root/'input.glb'; src.write_bytes(b'input'); out=root/'result.glb'; out.write_bytes(b'output')
            r={'inputSha256':local.sha256(src),'output':'result.glb','outputSha256':local.sha256(out)}
            self.assertEqual(local.verify_intake(root,src,r),out)
            out.write_bytes(b'tampered')
            with self.assertRaises(ValueError): local.verify_intake(root,src,r)

class ExecutionTests(unittest.TestCase):
    def test_nonzero_and_timeout_are_not_success(self):
        import sys
        with tempfile.TemporaryDirectory() as d:
            root=local.create_run(Path(d),'fixture',{})
            with self.assertRaises(ValueError): local.execute([sys.executable,'-c','raise SystemExit(7)'],root,name='fail')
            with self.assertRaises(__import__('subprocess').TimeoutExpired): local.execute([sys.executable,'-c','import time; time.sleep(5)'],root,timeout=1,name='timeout')
            self.assertTrue((root/'fail.log').exists())
    def test_shared_lock_excludes_second_job(self):
        with tempfile.TemporaryDirectory() as d:
            with local.heavy_lock(Path(d)):
                with self.assertRaises(ValueError):
                    with local.heavy_lock(Path(d)): pass
    def test_snapshot_does_not_copy_environment_or_modify_source(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); repo=root/'repo'; repo.mkdir()
            subprocess.run(['git','init',str(repo)],check=True,capture_output=True)
            (repo/'engine.py').write_text('print(1)')
            (repo/'environment').mkdir(); (repo/'environment'/'large').write_text('private runtime')
            subprocess.run(['git','-C',str(repo),'add','engine.py'],check=True)
            subprocess.run(['git','-C',str(repo),'-c','user.email=test@example.com','-c','user.name=Test','commit','-m','fixture'],check=True,capture_output=True)
            copied=local.snapshot_sources(repo,root/'copy')
            self.assertTrue((copied/'engine.py').is_file())
            self.assertFalse((copied/'environment').exists())
            self.assertFalse((repo/'tmp').exists())


class DelegationTests(unittest.TestCase):
    def test_unirig_uses_existing_candidate_runner(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'lab').mkdir(); (root/'lab/lab.py').write_text('# fixture')
            candidate=root/'candidate.json'; candidate.write_text('{}')
            command=local.unirig_command({'laboratoryRoot':str(root),'python':'/usr/bin/python3'},candidate,'rig',120)
            self.assertEqual(command[1],str(root/'lab/lab.py'))
            self.assertEqual(command[2:5],['rig','--candidate',str(candidate)])
            self.assertIn('--stage',command)
            with self.assertRaises(ValueError): local.unirig_command({'laboratoryRoot':str(root),'python':'/usr/bin/python3'},candidate,'skin',120)

class BpyIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(__import__('os').environ.get('STUDIO_BPY_PYTHON'),'Set STUDIO_BPY_PYTHON for real CPU Blender fixture')
    def test_export_reopen_rigid_and_humanoid_retarget(self):
        import os
        import subprocess
        import json
        python=os.environ['STUDIO_BPY_PYTHON']
        worker=Path(local.__file__).with_name('blender_worker.py')
        fixture=Path(__file__).with_name('local_fixture.py')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            env=os.environ.copy(); env.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1')
            def execute(command):
                result=subprocess.run(command,env=env,text=True,capture_output=True,timeout=120)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            execute([python,str(worker),'demo','--output-dir',str(root/'demo')])
            report=json.loads((root/'demo/inspection.json').read_text())
            self.assertAlmostEqual(report['reimported']['dimensionsMeters'][2],.3,places=5)
            self.assertEqual(report['reimported']['clips'][0]['durationSeconds'],1)
            execute([python,str(fixture),str(root/'fixture')])
            execute([python,str(worker),'retarget','--input',str(root/'fixture/target.blend'),'--motion',str(root/'fixture/motion.blend'),'--mapping',str(root/'fixture/mapping.json'),'--output-dir',str(root/'retarget')])
            report=json.loads((root/'retarget/inspection.json').read_text())
            self.assertEqual(report['reimported']['armatures'],1)
            self.assertEqual(report['reimported']['clips'][0]['durationSeconds'],1)
            self.assertEqual(report['motion']['sourceAction'],'HumanoidWave')
            script="import bpy,json,os; bpy.ops.wm.open_mainfile(filepath="+repr(str(root/'retarget/scene.blend'))+"); bpy.context.scene.frame_set(13); a=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE'); p=a.pose.bones['upper_arm.L']; open("+repr(str(root/'pose.json'))+",'w').write(json.dumps({'angle':p.matrix_basis.to_quaternion().angle})); os._exit(0)"
            execute([python,'-c',script])
            self.assertAlmostEqual(json.loads((root/'pose.json').read_text())['angle'],__import__('math').pi/4,places=4)

class SafetyTests(unittest.TestCase):
    def test_shared_lab_lock_and_profile_without_hf_override(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); lock=root/'existing.lock'; lock.touch()
            with local.heavy_lock(root/'a',lock):
                with self.assertRaises(ValueError):
                    with local.heavy_lock(root/'b',lock): pass
        p=dict(local.default_profile(),repositoryRoot='/tmp/skin',python='/tmp/python',checkpoint='/tmp/ckpt')
        self.assertNotIn('--hf_path',local.skin_command(p,'/tmp/in.glb','/tmp/out.glb'))
    def test_intake_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); src=root/'input'; src.write_bytes(b'input')
            with self.assertRaises(ValueError): local.verify_intake(root,src,{'inputSha256':local.sha256(src),'output':'../outside','outputSha256':'0'*64})


class SkinRoutingTests(unittest.TestCase):
    def test_existing_skin_is_preserved_without_explicit_reskin(self):
        import json
        import struct
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source=root/'rigged.glb'
            data=json.dumps({'asset':{'version':'2.0'},'meshes':[{'primitives':[]}],'skins':[{'joints':[]}]}).encode()
            data+=b' '*((-len(data))%4)
            source.write_bytes(struct.pack('<4sII',b'glTF',2,20+len(data))+struct.pack('<I4s',len(data),b'JSON')+data)
            args=SimpleNamespace(settings={},dry_run=False,use_skeleton=False,workspace=root)
            result=local.run_skin(args,source,local.create_run(root,'test',{}))
            self.assertEqual(result['route'],'preserve-rig')
            self.assertEqual(result['status'],'NOT_RUN')

class ChildCleanupTests(unittest.TestCase):
    def test_timeout_terminates_child_that_created_own_session(self):
        import sys, os, subprocess
        with tempfile.TemporaryDirectory() as d:
            root=local.create_run(Path(d),'test',{})
            code="import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True); print(p.pid,flush=True); time.sleep(60)"
            with self.assertRaises(subprocess.TimeoutExpired): local.execute([sys.executable,'-c',code],root,timeout=1,name='child')
            pid=int((root/'child.log').read_text().strip())
            state=Path('/proc')/str(pid)/'stat'
            if state.exists():
                self.assertEqual(state.read_text().rsplit(')',1)[1].split()[0],'Z')

class RemoteSupervisorTests(unittest.TestCase):
    def test_supervisor_preserves_exit_and_bounds_detached_children(self):
        import subprocess,sys
        worker=Path(local.__file__).with_name('remote_runner.py')
        p=subprocess.run([sys.executable,str(worker),'--timeout','5','--',sys.executable,'-c','raise SystemExit(9)'],capture_output=True,timeout=10)
        self.assertEqual(p.returncode,9)
        code="import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True); print(p.pid,flush=True); time.sleep(60)"
        p=subprocess.run([sys.executable,str(worker),'--timeout','1','--',sys.executable,'-c',code],capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,124)
        state=Path('/proc')/p.stdout.strip()/'stat'
        if state.exists(): self.assertEqual(state.read_text().rsplit(')',1)[1].split()[0],'Z')

@unittest.skipUnless(__import__('os').environ.get('STUDIO_BPY_PYTHON'),'Real CPU bpy runtime required')
class ReviewRegressionTests(unittest.TestCase):
    def test_reject_motion_metadata_and_effective_object_transform_mismatches(self):
        import os,subprocess
        python=os.environ['STUDIO_BPY_PYTHON']; env=os.environ.copy()
        env.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1')
        worker=Path(local.__file__).with_name('blender_worker.py')
        fixture=Path(__file__).with_name('local_fixture.py')
        variants={
            'fps':"bpy.context.scene.render.fps=60",
            'units':"bpy.context.scene.unit_settings.scale_length=.01",
            'quaternion':"rig.rotation_mode='QUATERNION'; rig.rotation_quaternion=Quaternion((0,0,1),1.57079632679)",
            'parent':"parent=bpy.data.objects.new('Parent',None); bpy.context.scene.collection.objects.link(parent); rig.parent=parent; parent.rotation_euler.z=1.57079632679",
            'axis_angle':"rig.rotation_mode='AXIS_ANGLE'; rig.rotation_axis_angle=(1.57079632679,0,0,1)",
        }
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=subprocess.run([python,str(fixture),str(root/'fixture')],env=env,capture_output=True,text=True,timeout=120)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            for name,mutation in variants.items():
                with self.subTest(name=name):
                    motion=root/(name+'.blend')
                    script="import bpy,os; from mathutils import Quaternion; bpy.ops.wm.open_mainfile(filepath="+repr(str(root/'fixture/motion.blend'))+"); rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE'); "+mutation+"; bpy.ops.wm.save_as_mainfile(filepath="+repr(str(motion))+"); os._exit(0)"
                    p=subprocess.run([python,'-c',script],env=env,capture_output=True,text=True,timeout=120)
                    self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                    output=root/name
                    p=subprocess.run([python,str(worker),'retarget','--input',str(root/'fixture/target.blend'),'--motion',str(motion),'--mapping',str(root/'fixture/mapping.json'),'--output-dir',str(output)],env=env,capture_output=True,text=True,timeout=120)
                    self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
                    self.assertFalse((output/'inspection.json').exists())
                    self.assertIn('mismatch' if name in ('fps','units') else 'transform',p.stderr.lower())

    def test_every_blender_adapter_run_records_hashes(self):
        import os,subprocess,json
        from types import SimpleNamespace
        python=os.environ['STUDIO_BPY_PYTHON']
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            env=os.environ.copy(); env.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1')
            fixture=Path(__file__).with_name('local_fixture.py')
            p=subprocess.run([python,str(fixture),str(root/'incoming')],env=env,capture_output=True,text=True,timeout=120)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            args=SimpleNamespace(workspace=root,settings={'blender':{'python':python}},engine='blender',operation='retarget',input='incoming/target.blend',motion='incoming/motion.blend',mapping='incoming/mapping.json',timeout=120,dry_run=False,use_skeleton=False)
            result=local.handler(args); run=Path(result['run'])
            inputs=local.read_json(run/'blender-inputs.json')
            self.assertEqual(set(inputs['inputs']),{'input','motion','mapping'})
            for role,entry in inputs['inputs'].items(): self.assertEqual(entry['sha256'],local.sha256(root/getattr(args,role)))
            outputs=local.read_json(run/'blender-outputs.json')
            self.assertEqual({e['path'] for e in outputs['outputs']},{'scene.blend','asset.glb','inspection.json'})
            for entry in outputs['outputs']: self.assertEqual(entry['sha256'],local.sha256(run/entry['path']))
            self.assertEqual(outputs['inputManifestSha256'],local.sha256(run/'blender-inputs.json'))

class BlenderLineageTests(unittest.TestCase):
    def test_input_changed_by_process_is_rejected_and_original_hash_retained(self):
        import sys,json
        from types import SimpleNamespace
        original_worker=local.WORKER
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source=root/'input.glb'; source.write_bytes(b'original')
            expected=local.sha256(source)
            worker=root/'worker.py'
            worker.write_text("import sys,json; from pathlib import Path; a=sys.argv; p=Path(a[a.index('--input')+1]); p.write_bytes(b'changed'); out=Path(a[a.index('--output-dir')+1]); (out/'inspection.json').write_text(json.dumps({'status':'PASS'}))")
            (root/'retarget.py').write_text('# fixture code')
            args=SimpleNamespace(workspace=root,settings={'blender':{'python':sys.executable}},engine='blender',operation='inspect',input='input.glb',motion=None,mapping=None,timeout=10,dry_run=False,use_skeleton=False)
            try:
                local.WORKER=worker
                with self.assertRaisesRegex(ValueError,'input changed'): local.handler(args)
            finally: local.WORKER=original_worker
            run=next((root/'runs').iterdir())
            self.assertEqual(local.read_json(run/'blender-inputs.json')['inputs']['input']['sha256'],expected)
            self.assertFalse((run/'blender-outputs.json').exists())

@unittest.skipUnless(__import__('os').environ.get('STUDIO_BPY_PYTHON'),'Real CPU bpy runtime required')
class GlbTargetRegressionTests(unittest.TestCase):
    def test_glb_target_isolated_from_temporary_motion_metadata_scene(self):
        import os,subprocess,json
        python=os.environ['STUDIO_BPY_PYTHON']; env=os.environ.copy()
        env.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1')
        worker=Path(local.__file__).with_name('blender_worker.py'); fixture=Path(__file__).with_name('local_fixture.py')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            def execute(command):
                p=subprocess.run(command,env=env,capture_output=True,text=True,timeout=120)
                self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            execute([python,str(fixture),str(root/'fixture')])
            execute([python,str(worker),'export','--input',str(root/'fixture/target.blend'),'--output-dir',str(root/'exported')])
            execute([python,str(worker),'retarget','--input',str(root/'exported/asset.glb'),'--motion',str(root/'fixture/motion.blend'),'--mapping',str(root/'fixture/mapping.json'),'--output-dir',str(root/'retarget')])
            report=json.loads((root/'retarget/inspection.json').read_text())
            self.assertEqual(report['inspection']['armatures'],1)
            self.assertEqual(report['reimported']['armatures'],1)
            self.assertEqual(report['reimported']['meshes'],1)
            self.assertAlmostEqual(report['reimported']['clips'][0]['durationSeconds'],1)
            self.assertEqual(report['motion']['sourceMetadata'],{'fps':24,'unitScale':1})
