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
