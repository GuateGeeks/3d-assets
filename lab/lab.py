"""Local rigging laboratory: diagnostics, isolated setup and a recorded UniRig smoke test."""
import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / 'lab'
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))
import creation_adapter
LOCAL = LAB / '.local'
REPORTS = LAB / 'reports'
PROFILE = LAB / 'envs/unirig.profile.json'
VENV_PYTHON = LOCAL / 'envs/unirig/bin/python'


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.partial')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    os.replace(temp, path)


def environment():
    (LOCAL / 'cache').mkdir(parents=True, exist_ok=True)
    (LOCAL / 'tmp').mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({'UV_CACHE_DIR': str(LOCAL / 'cache/uv'),
                'UV_PYTHON_INSTALL_DIR': str(LOCAL / 'python'),
                'UV_PYTHON_BIN_DIR': str(LOCAL / 'bin'),
                'HF_HOME': str(LOCAL / 'cache/huggingface'),
                'XDG_CACHE_HOME': str(LOCAL / 'cache'),
                'TORCH_HOME': str(LOCAL / 'cache/torch'),
                'MPLCONFIGDIR': str(LOCAL / 'cache/matplotlib'),
                'TMPDIR': str(LOCAL / 'tmp'),
                'HF_HUB_DISABLE_TELEMETRY': '1', 'HF_HUB_DISABLE_XET': '1',
                'WANDB_MODE': 'disabled', 'MAX_JOBS': '2', 'UV_NO_PROGRESS': '1',
                'PYTHONUNBUFFERED': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
    if VENV_PYTHON.exists():
        env['PATH'] = str(VENV_PYTHON.parent) + os.pathsep + env.get('PATH', '')
    return env


def query(args, timeout=20):
    try:
        result = subprocess.run(args, text=True, capture_output=True, timeout=timeout, check=False)
        return {'exitCode': result.returncode, 'output': result.stdout.strip(), 'error': result.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {'exitCode': None, 'output': '', 'error': str(error)}


def doctor():
    memory = {}
    meminfo = Path('/proc/meminfo')
    if meminfo.exists():
        for line in meminfo.read_text().splitlines():
            key, value = line.split(':', 1)
            if key in {'MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'}:
                memory[key + 'Bytes'] = int(value.strip().split()[0]) * 1024
    gpu = query(['nvidia-smi', '--query-gpu=name,memory.total,memory.free,driver_version', '--format=csv,noheader,nounits'])
    devices = []
    if gpu['exitCode'] == 0:
        for line in gpu['output'].splitlines():
            name, total, free, driver = [part.strip() for part in line.split(',')]
            devices.append({'name': name, 'totalMiB': int(total), 'freeMiB': int(free), 'driver': driver})
    disks = {}
    for name, path in [('linuxWorkspace', ROOT), ('windowsC', Path('/mnt/c')), ('windowsD', Path('/mnt/d'))]:
        if path.exists():
            total, used, free = shutil.disk_usage(path)
            disks[name] = {'totalBytes': total, 'freeBytes': free}
    cpu = {}
    if Path('/proc/cpuinfo').exists():
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):
                cpu['model'] = line.split(':', 1)[1].strip()
                break
    cpu['logicalCores'] = os.cpu_count()
    catalog = json.loads((ROOT / 'index.json').read_text())
    report = {'schemaVersion': 1, 'recordedAt': timestamp(),
              'platform': platform.platform(), 'machine': platform.machine(),
              'systemPython': platform.python_version(), 'cpu': cpu, 'memory': memory,
              'disks': disks, 'gpus': devices, 'nvidiaSmi': gpu,
              'tools': {name: shutil.which(name) for name in ['python3', 'uv', 'nvcc', 'gcc', 'g++', 'cmake', 'ninja', 'git', 'curl']},
              'labPythonPresent': VENV_PYTHON.exists(), 'catalogModels': len(catalog['models']),
              'profile': json.loads(PROFILE.read_text()),
              'checks': {'linuxX86_64': sys.platform == 'linux' and platform.machine() == 'x86_64',
                         'cudaVisible': bool(devices),
                         'nominal8GiB': any(device['totalMiB'] >= 8192 for device in devices),
                         'workspace50GiB': disks['linuxWorkspace']['freeBytes'] >= 50 * 1024**3}}
    report['status'] = 'passed' if all(report['checks'].values()) else 'needs_attention'
    save_json(REPORTS / 'diagnostic.json', report)
    print(json.dumps({'status': report['status'], 'gpus': devices, 'report': 'lab/reports/diagnostic.json'}, ensure_ascii=False))
    return report


@contextlib.contextmanager
def engine_lock():
    import fcntl
    path = LOCAL / 'locks/unirig.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('Another UniRig laboratory operation is active') from error
        stream.seek(0)
        stream.truncate()
        stream.write(json.dumps({'pid': os.getpid(), 'startedAt': timestamp()}))
        stream.flush()
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


class StageError(RuntimeError):
    def __init__(self, message, status='dependency_error'):
        super().__init__(message)
        self.status = status


class Run:
    def __init__(self, command):
        self.id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
        self.path = LOCAL / 'runs' / self.id
        self.path.mkdir(parents=True)
        self.report = {'schemaVersion': 1, 'runId': self.id, 'command': command,
                       'startedAt': timestamp(), 'status': 'running', 'engine': 'unirig',
                       'profileSha256': sha256(PROFILE), 'stages': [], 'artifacts': []}
        self.started = time.monotonic()
        self.save()

    def save(self):
        save_json(self.path / 'run.json', self.report)

    def finish(self, status, error=None):
        self.report.update({'status': status, 'finishedAt': timestamp(),
                            'seconds': round(time.monotonic() - self.started, 3)})
        if error:
            self.report['error'] = str(error)
        self.save()
        latest_name = self.report['command']
        if latest_name == 'rig' and self.report.get('inputKind') == 'creation-candidate':
            latest_name = 'rig-candidate'
        save_json(REPORTS / ('latest-' + latest_name + '.json'), self.report)
        print(json.dumps({'runId': self.id, 'status': status,
                          'report': str((self.path / 'run.json').relative_to(ROOT))}))

    def execute(self, name, args, cwd=ROOT, timeout=3600, extra_env=None):
        log = self.path / (name + '.log')
        env = environment()
        if extra_env:
            env.update(extra_env)
        stage = {'name': name, 'command': [str(arg) for arg in args], 'startedAt': timestamp(),
                 'log': str(log.relative_to(ROOT))}
        start = time.monotonic()
        self.report['stages'].append(stage)
        self.save()
        print('Starting ' + name + '; log: ' + str(log.relative_to(ROOT)), flush=True)
        last_gpu_sample = 0.0
        with log.open('w') as output:
            child = subprocess.Popen([str(arg) for arg in args], cwd=cwd, env=env,
                                     stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                while child.poll() is None:
                    if self.report['command'] in {'smoke', 'rig'}:
                        status_file = Path('/proc') / str(child.pid) / 'status'
                        try:
                            for line in status_file.read_text().splitlines():
                                if line.startswith('VmHWM:'):
                                    rss = int(line.split()[1]) * 1024
                                    stage['sampledPeakMainChildRssBytes'] = max(rss, stage.get('sampledPeakMainChildRssBytes', 0))
                        except OSError:
                            pass
                        if time.monotonic() - last_gpu_sample >= 1:
                            sample = query(['nvidia-smi', '-i', '0', '--query-gpu=memory.used,memory.free', '--format=csv,noheader,nounits'], timeout=3)
                            if sample['exitCode'] == 0:
                                used, free = [int(value.strip()) for value in sample['output'].split(',')]
                                memory = stage.setdefault('sampledDeviceMemoryMiB', {'initialUsed': used, 'peakUsed': used, 'minimumFree': free, 'samples': 0, 'scope': 'whole GPU 0, includes other applications; approximately one sample per second'})
                                memory.update({'peakUsed': max(memory['peakUsed'], used), 'minimumFree': min(memory['minimumFree'], free), 'samples': memory['samples'] + 1})
                            last_gpu_sample = time.monotonic()
                    if time.monotonic() - start > timeout:
                        raise TimeoutError(name + ' exceeded its time limit')
                    time.sleep(0.25)
            except BaseException:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait()
                stage.update({'exitCode': child.returncode, 'seconds': round(time.monotonic() - start, 3)})
                self.save()
                raise
        stage.update({'exitCode': child.returncode, 'seconds': round(time.monotonic() - start, 3)})
        self.save()
        if child.returncode != 0:
            tail = log.read_text(errors='replace')[-6000:]
            print(tail, file=sys.stderr)
            status = ('oom' if 'out of memory' in tail.lower() else
                      'invalid_output' if name.startswith('validate-') else
                      'dependency_error' if name in {'install', 'download-models', 'gpu-and-imports'} else 'execution_error')
            raise StageError(name + ' failed; inspect ' + str(log.relative_to(ROOT)), status)
        print(name + ': passed (' + str(stage['seconds']) + ' s)', flush=True)

    def artifact(self, path):
        if not path.is_file() or path.stat().st_size == 0:
            raise StageError('Expected output missing: ' + str(path), 'invalid_output')
        item = {'file': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': sha256(path)}
        self.report['artifacts'].append(item)
        self.save()
        return item


def require_environment():
    if not VENV_PYTHON.exists():
        raise RuntimeError('Run setup --engine unirig first')


def smoke(run, args):
    require_environment()
    gpu_receipt = REPORTS / 'unirig-gpu.json'
    if not gpu_receipt.exists() or json.loads(gpu_receipt.read_text())['status'] != 'passed':
        raise RuntimeError('Run verify --engine unirig before smoke')
    gpu_info = json.loads(gpu_receipt.read_text())
    if gpu_info.get('profileSha256') != sha256(PROFILE):
        raise RuntimeError('GPU verification is stale; run verify again')
    models_path = REPORTS / 'unirig-models.json'
    if not models_path.exists() or json.loads(models_path.read_text())['status'] != 'passed':
        raise RuntimeError('Run setup --models-only before smoke')
    prepare_command = [VENV_PYTHON, LAB / 'scripts/prepare_smoke.py', '--run-dir', run.path, '--voxel-backend', args.voxel_backend]
    corpus = None
    candidate_root = None
    if args.command == 'rig':
        if args.candidate:
            candidate_root, corpus = creation_adapter.copy_prepared(args.candidate, ROOT, run.path)
            worker = creation_adapter.snapshot_code(run.path, ROOT)
            prepare_command += ['--input', candidate_root / corpus['prepared']['file']]
            run.report['asset'] = corpus['assetId']
            run.report['candidatePrepared'] = {'file': str((candidate_root / 'creation-prepared.json').relative_to(ROOT)),
                                                'sha256': sha256(candidate_root / 'creation-prepared.json')}
        else:
            corpus_path = LOCAL / 'corpus' / args.asset / 'prepared.json'
            corpus = json.loads(corpus_path.read_text())
            if sha256(ROOT / corpus['prepared']['file']) != corpus['prepared']['sha256']:
                raise StageError('Prepared corpus hash changed; prepare again', 'invalid_output')
            if sha256(ROOT / corpus['sourceFile']) != corpus['sourceSha256']:
                raise StageError('Original corpus hash changed', 'invalid_output')
            prepare_command += ['--input', ROOT / corpus['prepared']['file']]
            run.report['asset'] = args.asset
        run.report['provenance'] = corpus
    run.execute('prepare-workspace', prepare_command)
    workspace = run.path / 'workspace'
    repo = LOCAL / 'repos/UniRig'
    original = workspace / 'input/model.glb'
    run.report['input'] = {'file': corpus['prepared']['file'] if corpus else 'official:examples/giraffe.glb', 'sha256': sha256(original)}
    if candidate_root:
        if sha256(original) != corpus['prepared']['sha256']:
            raise StageError('Inference workspace copy differs from prepared candidate', 'invalid_output')
        run.report['input']['file'] = str((candidate_root / corpus['prepared']['file']).relative_to(ROOT))
    run.report['seed'] = args.seed
    run.report['voxelBackend'] = args.voxel_backend
    offline = {'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}
    common = [VENV_PYTHON, '-m', 'src.data.extract', '--config=configs/data/quick_inference.yaml',
              '--require_suffix=glb,fbx', '--faces_target_count=50000', '--num_runs=1',
              '--force_override=true', '--id=0', '--time=' + run.id]
    temp = workspace / 'tmp'
    run.execute('extract-skeleton', common + ['--input=input/model.glb', '--output_dir=' + str(temp)],
                cwd=workspace, timeout=args.timeout, extra_env=offline)
    if not list(temp.rglob('raw_data.npz')):
        raise StageError('Mesh extraction produced no raw_data.npz', 'invalid_output')
    skeleton = workspace / 'output/model_skeleton.fbx'
    run.execute('generate-skeleton', [VENV_PYTHON, repo / 'run.py',
        '--task=configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml',
        '--seed=' + str(args.seed), '--input=input/model.glb', '--output=' + str(skeleton),
        '--npz_dir=' + str(temp)], cwd=workspace, timeout=args.timeout, extra_env=offline)
    run.artifact(skeleton)
    run.execute('validate-skeleton', [VENV_PYTHON, LAB / 'scripts/inspect_fbx.py', skeleton,
                '--output', run.path / 'skeleton-inspection.json'], extra_env=offline)
    run.artifact(run.path / 'skeleton-inspection.json')
    if args.stage == 'skeleton':
        return
    # For the installation smoke test use the officially supplied reviewed skeleton.
    reviewed = workspace / 'input/reviewed.fbx'
    if corpus:
        shutil.copy2(skeleton, reviewed)
    temp_skin = workspace / 'tmp-skin'
    run.report['skinningInput'] = {'file': str(skeleton.relative_to(ROOT)) if corpus else 'official:examples/skeleton/giraffe.fbx', 'sha256': sha256(reviewed)}
    run.execute('extract-skin', common + ['--input=input/reviewed.fbx', '--output_dir=' + str(temp_skin)],
                cwd=workspace, timeout=args.timeout, extra_env=offline)
    skin = workspace / 'output/model_skin.fbx'
    run.execute('generate-skin', [VENV_PYTHON, repo / 'run.py',
        '--task=configs/task/quick_inference_unirig_skin.yaml', '--seed=' + str(args.seed),
        '--input=input/reviewed.fbx', '--output=' + str(skin), '--npz_dir=' + str(temp_skin),
        '--data_name=raw_data.npz'], cwd=workspace, timeout=args.timeout, extra_env=offline)
    run.artifact(skin)
    run.execute('validate-skin', [VENV_PYTHON, LAB / 'scripts/inspect_fbx.py', skin,
                '--require-weights', '--output', run.path / 'skin-inspection.json'], extra_env=offline)
    merged = workspace / 'output/model_rigged.glb'
    run.execute('merge', [VENV_PYTHON, '-m', 'src.inference.merge', '--require_suffix=glb,fbx',
        '--num_runs=1', '--id=0', '--source=' + str(skin), '--target=' + str(original), '--output=' + str(merged)],
        cwd=workspace, timeout=args.timeout, extra_env=offline)
    run.artifact(merged)
    run.execute('validate-glb', [VENV_PYTHON, LAB / 'scripts/inspect_fbx.py', merged,
                '--require-weights', '--output', run.path / 'glb-inspection.json'], extra_env=offline)
    run.artifact(run.path / 'glb-inspection.json')
    if corpus:
        run.report['scope'] = 'automatic generated skeleton and weights; candidate pending visual review, no clips'
        if candidate_root:
            # The normalized inference result is evidence, not the deliverable.
            # Restore the inverse once on mesh/armature roots, preserving weights.
            restored_dir = run.path / 'restored'
            restoration_report = run.path / 'restoration-report.json'
            run.execute('restore-creation-scale', [VENV_PYTHON, worker, 'restore', '--input', merged,
                        '--geometry', candidate_root / corpus['geometry']['file'],
                        '--output-dir', restored_dir, '--report', restoration_report], timeout=300,
                        extra_env={'CUDA_VISIBLE_DEVICES': '', 'OMP_NUM_THREADS': '2'})
            creation_adapter.verify_restoration(restoration_report, restored_dir, merged,
                        candidate_root / corpus['geometry']['file'], worker, corpus['normalization'])
            run.artifact(restoration_report)
            final = run.artifact(restored_dir / 'restored.glb')
            run.report['restoredCandidate'] = {**final, 'units': 'm', 'normalization': corpus['normalization'],
                                                'provenance': corpus['provenance'], 'visual': 'NOT_RUN'}
            run.report['scope'] = 'reviewed creation source; automatic skeleton/weights; restored original meters and appearance; rig visual review pending, no clips'
        else:
            save_json(REPORTS / ('rig-' + args.asset + '.json'), run.report)
        return
    run.report['scope'] = 'installation smoke: generated skeleton plus skinning of upstream-reviewed skeleton; no animation or visual approval'
    receipt = json.loads((REPORTS / 'unirig-install.json').read_text())
    receipt['inferenceVerified'] = True
    receipt['status'] = 'inference_verified'
    receipt['inferenceScope'] = run.report['scope']
    receipt['inferenceRunId'] = run.id
    save_json(REPORTS / 'unirig-install.json', receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor', help='Record host, GPU, tool and storage diagnostics')
    setup = sub.add_parser('setup', help='Install pinned UniRig packages and cache its models')
    setup.add_argument('--engine', choices=['unirig'], default='unirig')
    setup.add_argument('--packages-only', action='store_true')
    setup.add_argument('--models-only', action='store_true')
    verify = sub.add_parser('verify', help='Execute real CUDA kernels and Blender imports')
    verify.add_argument('--engine', choices=['unirig'], default='unirig')
    sample = sub.add_parser('smoke', help='Run the official giraffe installation test')
    sample.add_argument('--engine', choices=['unirig'], default='unirig')
    sample.add_argument('--stage', choices=['skeleton', 'all'], default='all')
    sample.add_argument('--seed', type=int, default=42)
    sample.add_argument('--voxel-backend', choices=['open3d', 'pyrender'], default='open3d',
                        help='Upstream voxelizer; open3d avoids EGL initialization on this WSL host')
    sample.add_argument('--timeout', type=int, default=1800, help='Maximum seconds per inference stage')
    prepare = sub.add_parser('prepare', help='Prepare rest-pose copies and a normalized original rig control')
    prepare.add_argument('--asset', choices=['human', 'quadruped', 'all'], default='all')
    ingest = sub.add_parser('ingest', help='Validate and copy reviewed creation evidence; explicitly normalize an isolated candidate')
    ingest.add_argument('--candidate', type=Path, required=True, help='Closed creation-lab handoff candidate.json')
    ingest.add_argument('--timeout', type=int, default=300, help='Maximum seconds for CPU Blender preparation')
    rig = sub.add_parser('rig', help='Run generated skeleton and skinning on a prepared corpus asset')
    rig_source = rig.add_mutually_exclusive_group(required=True)
    rig_source.add_argument('--asset', choices=['human', 'quadruped'])
    rig_source.add_argument('--candidate', type=Path, help='Sealed creation-prepared.json produced by ingest')
    rig.add_argument('--stage', choices=['skeleton', 'all'], default='all')
    rig.add_argument('--seed', type=int, default=42)
    rig.add_argument('--voxel-backend', choices=['open3d', 'pyrender'], default='open3d')
    rig.add_argument('--timeout', type=int, default=1800)
    review = sub.add_parser('review', help='Bake equivalent diagnostic stills and build the local gallery inventory')
    review.add_argument('--asset', choices=['human', 'quadruped', 'all'], default='all')
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('Use lab/lab.cmd from Windows or run this command in WSL/Linux')
    if args.command == 'doctor':
        return 0 if doctor()['status'] == 'passed' else 1
    if args.command == 'setup' and args.packages_only and args.models_only:
        parser.error('--packages-only and --models-only are mutually exclusive')
    if args.command in {'smoke', 'rig', 'ingest'} and args.timeout <= 0:
        parser.error('--timeout must be positive')
    if args.command == 'ingest' and args.timeout > 300:
        parser.error('ingest --timeout cannot exceed 300 seconds')
    signal.signal(signal.SIGTERM, lambda signum, frame: (_ for _ in ()).throw(KeyboardInterrupt()))
    with engine_lock():
        run = Run(args.command)
        if args.command == 'rig' and args.candidate:
            run.report['inputKind'] = 'creation-candidate'
        try:
            if args.command == 'setup':
                if args.models_only:
                    require_environment()
                    run.execute('download-models', [VENV_PYTHON, LAB / 'scripts/download_models.py'])
                    receipt_path = REPORTS / 'unirig-install.json'
                    receipt = json.loads(receipt_path.read_text())
                    receipt['modelsVerified'] = True
                    receipt['status'] = 'ready_for_smoke' if receipt.get('cudaVerified') else 'models_cached'
                    save_json(receipt_path, receipt)
                else:
                    command = [sys.executable, LAB / 'scripts/setup_unirig.py']
                    if args.packages_only:
                        command.append('--packages-only')
                    run.execute('install', command, timeout=7200)
                    if not args.packages_only:
                        receipt_path = REPORTS / 'unirig-install.json'
                        receipt = json.loads(receipt_path.read_text())
                        receipt.update({'cudaVerified': True, 'modelsVerified': True, 'status': 'ready_for_smoke', 'verificationRunId': run.id})
                        save_json(receipt_path, receipt)
            elif args.command == 'verify':
                require_environment()
                run.execute('gpu-and-imports', [VENV_PYTHON, LAB / 'scripts/probe_unirig.py'])
                receipt_path = REPORTS / 'unirig-install.json'
                receipt = json.loads(receipt_path.read_text())
                models_path = REPORTS / 'unirig-models.json'
                models_ready = models_path.exists() and json.loads(models_path.read_text()).get('status') == 'passed'
                receipt.update({'cudaVerified': True, 'verificationRunId': run.id,
                                'modelsVerified': models_ready, 'status': 'ready_for_smoke' if models_ready else 'cuda_verified'})
                save_json(receipt_path, receipt)
            elif args.command == 'prepare':
                require_environment()
                for asset in (['human', 'quadruped'] if args.asset == 'all' else [args.asset]):
                    run.execute('prepare-' + asset, [VENV_PYTHON, LAB / 'scripts/prepare_corpus.py', '--asset', asset, '--run-dir', run.path])
                    run.artifact(run.path / ('prepared-' + asset + '.json'))
            elif args.command == 'ingest':
                require_environment()
                receipt = creation_adapter.copy_candidate(args.candidate, ROOT, run.path)
                worker = creation_adapter.snapshot_code(run.path, ROOT)
                run.execute('prepare-creation-candidate', [VENV_PYTHON, worker, 'prepare',
                            '--input', run.path / receipt['sourceOriginal']['file'],
                            '--output-dir', run.path / 'prepared', '--report', run.path / 'geometry-preparation.json'],
                            timeout=args.timeout, extra_env={'CUDA_VISIBLE_DEVICES': '', 'OMP_NUM_THREADS': '2'})
                prepared = creation_adapter.seal_prepared(run.path, receipt)
                run.report['asset'] = prepared['assetId']
                run.report['preparedManifest'] = str((run.path / 'creation-prepared.json').relative_to(ROOT))
                run.report['normalization'] = prepared['normalization']
                run.report['provenance'] = prepared['provenance']
                run.artifact(run.path / 'creation-prepared.json')
                run.artifact(run.path / 'creation-prepared.COMPLETE')
                print(json.dumps({'preparedManifest': run.report['preparedManifest'], 'status': 'passed'}), flush=True)
            elif args.command == 'review':
                require_environment()
                run.execute('build-review', [VENV_PYTHON, LAB / 'scripts/build_review.py', '--asset', args.asset, '--run-dir', run.path])
                run.artifact(run.path / 'review-manifest.json')
                run.artifact(run.path / 'review-poses.json')
                for asset in (['human', 'quadruped'] if args.asset == 'all' else [args.asset]):
                    run.artifact(run.path / ('review-' + asset + '.json'))
            elif args.command in {'smoke', 'rig'}:
                smoke(run, args)
            run.finish('success')
            if args.command == 'rig' and args.asset:
                save_json(REPORTS / ('rig-' + args.asset + '.json'), run.report)
            return 0
        except KeyboardInterrupt as error:
            run.finish('cancelled', 'Interrupted; child process group terminated')
            return 130
        except TimeoutError as error:
            run.finish('timeout', error)
            return 1
        except Exception as error:
            run.finish(error.status if isinstance(error, StageError) else 'dependency_error', error)
            print(str(error), file=sys.stderr)
            return 1


if __name__ == '__main__':
    raise SystemExit(main())
