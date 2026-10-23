"""Run real CUDA kernels and check UniRig/Blender imports, writing a JSON receipt."""
import argparse
import importlib
import importlib.metadata
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / 'lab/.local'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'lab/reports/unirig-gpu.json')
    args = parser.parse_args()
    result = {'schemaVersion': 1, 'engine': 'unirig', 'status': 'running', 'checks': [],
              'profileSha256': hashlib.sha256((ROOT / 'lab/envs/unirig.profile.json').read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    def check(name, function):
        start = time.monotonic()
        try:
            detail = function()
            result['checks'].append({'name': name, 'status': 'passed',
                                     'seconds': round(time.monotonic() - start, 3), 'detail': detail})
            print(name + ': passed', flush=True)
        except Exception as error:
            result['checks'].append({'name': name, 'status': 'failed', 'error': str(error)})
            traceback.print_exc()
    def versions():
        from packaging.requirements import Requirement
        checked = {}
        for line in (ROOT / 'lab/envs/unirig.constraints.txt').read_text().splitlines():
            if not line.strip() or line.startswith('#'):
                continue
            requirement = Requirement(line)
            actual = importlib.metadata.version(requirement.name)
            if actual not in requirement.specifier:
                raise RuntimeError(requirement.name + ' differs from the pinned profile: ' + actual)
            checked[requirement.name] = actual
        return checked
    check('pinned_versions', versions)
    import torch
    def cuda():
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA is not available to this Python')
        torch.cuda.reset_peak_memory_stats()
        a = torch.randn(64, 64, device='cuda', dtype=torch.bfloat16)
        b = a @ a.T
        torch.cuda.synchronize()
        if not torch.isfinite(b).all():
            raise RuntimeError('Non-finite BF16 matrix result')
        return {'torch': torch.__version__, 'cudaRuntime': torch.version.cuda,
                'device': torch.cuda.get_device_name(), 'capability': list(torch.cuda.get_device_capability()),
                'bf16': torch.cuda.is_bf16_supported(), 'totalBytes': torch.cuda.get_device_properties(0).total_memory}
    check('cuda_bf16', cuda)
    def scatter():
        from torch_scatter import scatter_add
        values = torch.tensor([1., 2., 3.], device='cuda')
        out = scatter_add(values, torch.tensor([0, 1, 0], device='cuda'))
        torch.cuda.synchronize()
        if out.tolist() != [4., 2.]:
            raise RuntimeError('Incorrect scatter_add result')
        return out.tolist()
    check('torch_scatter_cuda', scatter)
    def cluster():
        from torch_cluster import fps
        points = torch.randn(32, 3, device='cuda')
        indices = fps(points, ratio=0.25, random_start=False)
        torch.cuda.synchronize()
        if len(indices) != 8:
            raise RuntimeError('Unexpected furthest-point sample count')
        return {'samples': len(indices)}
    check('torch_cluster_cuda', cluster)
    def attention():
        from flash_attn import flash_attn_qkvpacked_func
        qkv = torch.randn(1, 16, 3, 2, 32, device='cuda', dtype=torch.bfloat16)
        out = flash_attn_qkvpacked_func(qkv)
        torch.cuda.synchronize()
        if not torch.isfinite(out).all():
            raise RuntimeError('Non-finite FlashAttention result')
        return {'shape': list(out.shape)}
    check('flash_attention_cuda', attention)
    def sparse():
        import spconv.pytorch as spconv
        features = torch.randn(4, 4, device='cuda')
        indices = torch.tensor([[0, 0, 0, 0], [0, 1, 1, 1], [0, 2, 2, 2], [0, 3, 3, 3]],
                               dtype=torch.int32, device='cuda')
        tensor = spconv.SparseConvTensor(features, indices, [4, 4, 4], 1)
        conv = spconv.SubMConv3d(4, 4, 3, padding=1, bias=False).cuda()
        out = conv(tensor)
        torch.cuda.synchronize()
        if not torch.isfinite(out.features).all():
            raise RuntimeError('Non-finite sparse convolution result')
        return {'shape': list(out.features.shape)}
    check('spconv_cuda', sparse)
    def blender():
        import bpy
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(LOCAL / 'examples/UniRig/giraffe.glb'))
        meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        if not meshes:
            raise RuntimeError('Blender did not import the example mesh')
        return {'version': bpy.app.version_string, 'meshes': len(meshes)}
    check('blender_example_import', blender)
    def upstream():
        sys.path.insert(0, str(LOCAL / 'repos/UniRig'))
        for name in ['lightning', 'open3d', 'pyrender', 'transformers',
                     'src.model.unirig_ar', 'src.model.unirig_skin', 'src.data.extract']:
            importlib.import_module(name)
        return 'UniRig skeleton, skinning and extraction modules imported'
    check('upstream_imports', upstream)
    result['packages'] = {name: importlib.metadata.version(name) for name in
                          ['torch', 'torchvision', 'numpy', 'bpy', 'transformers', 'lightning',
                           'flash-attn', 'spconv-cu124', 'torch-scatter', 'torch-cluster']}
    result['status'] = 'passed' if all(item['status'] == 'passed' for item in result['checks']) else 'failed'
    if torch.cuda.is_available():
        result['peakAllocatedBytes'] = torch.cuda.max_memory_allocated()
        result['peakReservedBytes'] = torch.cuda.max_memory_reserved()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'report': str(args.output)}))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
