"""Create a per-run workspace with pinned model/configuration paths; leave upstream intact."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import yaml

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / 'lab/.local'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--voxel-backend', choices=['open3d', 'pyrender'], default='open3d')
    parser.add_argument('--input', type=Path, help='Prepared corpus GLB instead of official smoke input')
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if not run.is_relative_to((LOCAL / 'runs').resolve()):
        parser.error('Workspace must be inside a laboratory run')
    repo = LOCAL / 'repos/UniRig'
    workspace = run / 'workspace'
    workspace.mkdir()
    shutil.copytree(repo / 'configs', workspace / 'configs')
    (workspace / 'src').symlink_to(repo / 'src', target_is_directory=True)
    (workspace / 'input').mkdir()
    (workspace / 'output').mkdir()
    shutil.copy2(args.input if args.input else LOCAL / 'examples/UniRig/giraffe.glb', workspace / 'input/model.glb')
    shutil.copy2(LOCAL / 'examples/UniRig/giraffe-reviewed.fbx', workspace / 'input/reviewed.fbx')
    receipt = json.loads((ROOT / 'lab/reports/unirig-models.json').read_text())
    if receipt['status'] != 'passed':
        raise RuntimeError('Checkpoint download has not completed')
    for kind, task in [('skeleton', 'quick_inference_skeleton_articulationxl_ar_256'),
                       ('skin', 'quick_inference_unirig_skin')]:
        entry = next(item for item in receipt['files'] if item['file'].startswith(kind + '/'))
        checkpoint = LOCAL / entry['cachePath']
        digest = hashlib.sha256()
        if not checkpoint.is_file() or checkpoint.stat().st_size != entry['bytes']:
            raise RuntimeError('Checkpoint is missing or changed')
        with checkpoint.open('rb') as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != entry['sha256']:
            raise RuntimeError('Checkpoint hash mismatch')
        path = workspace / 'configs/task' / (task + '.yaml')
        config = yaml.safe_load(path.read_text())
        config['resume_from_checkpoint'] = str(checkpoint)
        path.write_text(yaml.safe_dump(config, sort_keys=False))
    config_folder = (LOCAL / 'cache/huggingface/hub/models--facebook--opt-350m/snapshots'
                     / receipt['optConfigRevision'])
    if not (config_folder / 'config.json').is_file():
        raise RuntimeError('Pinned OPT configuration missing')
    if hashlib.sha256((config_folder / 'config.json').read_bytes()).hexdigest() != receipt['optConfigSha256']:
        raise RuntimeError('OPT configuration hash mismatch')
    model = workspace / 'configs/model/unirig_ar_350m_1024_81920_float32.yaml'
    config = yaml.safe_load(model.read_text())
    config['llm']['pretrained_model_name_or_path'] = str(config_folder)
    model.write_text(yaml.safe_dump(config, sort_keys=False))
    transform = workspace / 'configs/transform/inference_skin_transform.yaml'
    config = yaml.safe_load(transform.read_text())
    config['predict_transform_config']['vertex_group_config']['kwargs']['voxel_skin']['backend'] = args.voxel_backend
    transform.write_text(yaml.safe_dump(config, sort_keys=False))
    profile = {'voxelBackend': args.voxel_backend, 'upstreamVoxelBackend': 'pyrender',
               'checkpointRevision': receipt['revision'], 'optConfigRevision': receipt['optConfigRevision'],
               'changes': ['checkpoint paths pinned locally', 'OPT configuration pinned locally', 'voxel backend selected explicitly'],
               'configs': {str(path.relative_to(workspace)): hashlib.sha256(path.read_bytes()).hexdigest()
                           for path in (workspace / 'configs').rglob('*.yaml')}}
    (run / 'smoke-profile.json').write_text(json.dumps(profile, indent=2) + '\n')
    print('Prepared isolated smoke workspace with local checkpoint and OPT paths.')


if __name__ == '__main__':
    main()
