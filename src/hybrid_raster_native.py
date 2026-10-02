"""Isolated RaDe native evidence export on frozen vanilla checkpoints.

RaDe-GS geometry belongs to Zhang et al.; the existing instrumentation is our
independent export. Normals are native camera-space splat normals, never a
claimed physical surface normal. SH0, white background, no filter_3D.
"""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'out/hybrid_raster_evidence_v2'
NATIVE = STAGE / 'native'
_EXTENSIONS = {}
RENDER_SETTINGS = dict(sh_degree=0, background=[1., 1., 1.], kernel_size=0.,
                       scale_modifier=1., filter_3D=False, prefiltered=False,
                       require_depth=True, topk=4,
                       camera_principal_point='(W-1)/2, (H-1)/2')


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.partial')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    os.replace(temp, path)


def camera_record(cam):
    if isinstance(cam, dict):
        h = cam.get('native_height', cam.get('H'))
        w = cam.get('native_width', cam.get('W'))
        k = cam.get('native_K', cam.get('K'))
        w2c = cam['w2c']
    else:
        h, w, k, w2c = cam.H, cam.W, cam.K, cam.w2c
    return dict(native_height=int(h), native_width=int(w),
                native_K=np.asarray(k, dtype=np.float64).tolist(),
                w2c=np.asarray(w2c, dtype=np.float64).tolist())


def camera_hash(cam):
    return json_hash(camera_record(cam))


def camera_matrices(cam):
    """Match CUDA ndc2Pix: zero NDC maps to (W-1)/2, not W/2."""
    c = camera_record(cam)
    h, w = c['native_height'], c['native_width']
    k = np.asarray(c['native_K'], np.float64)
    w2c = np.asarray(c['w2c'], np.float64)
    if k.shape != (3, 3) or w2c.shape != (4, 4):
        raise ValueError('invalid camera dimensions')
    if not np.isfinite(k).all() or not np.isfinite(w2c).all():
        raise ValueError('nonfinite camera')
    if h <= 0 or w <= 0 or min(k[0, 0], k[1, 1]) <= 0:
        raise ValueError('invalid image/focal dimensions')
    if not np.allclose(k[[0, 1], [2, 2]], [(w-1)/2., (h-1)/2.], atol=1e-8, rtol=0):
        raise ValueError('native RaDe ray kernel requires exact (W-1)/2 principal point')
    if k[0, 1] != 0 or k[1, 0] != 0:
        raise ValueError('skewed camera unsupported')
    p = np.zeros((4, 4), np.float32)
    p[0, 0], p[1, 1] = 2*k[0, 0]/w, 2*k[1, 1]/h
    p[2, 2], p[2, 3], p[3, 2] = 100./(100.-.01), -100.*.01/(100.-.01), 1.
    view = w2c.astype(np.float32).T.copy()
    return view, (view @ p.T).copy()


def load_checkpoint(path, expected_sha256=None):
    """Preserve every PLY row ID; do not compute covariance-axis normals."""
    from plyfile import PlyData
    path = Path(path).resolve()
    digest = sha256(path)
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError('checkpoint SHA256 mismatch')
    vertex = PlyData.read(str(path))['vertex']
    names = set(vertex.data.dtype.names)
    read = lambda keys: np.stack([np.asarray(vertex[k], np.float64) for k in keys], axis=1)
    opacity_logit = np.asarray(vertex['opacity'], np.float64)
    opacity = np.empty_like(opacity_logit)
    positive = opacity_logit >= 0
    opacity[positive] = 1./(1.+np.exp(-opacity_logit[positive]))
    exp_negative = np.exp(opacity_logit[~positive])
    opacity[~positive] = exp_negative/(1.+exp_negative)
    scale = np.exp(read(['scale_0', 'scale_1', 'scale_2']))
    g = dict(mu=read(['x', 'y', 'z']), opacity=opacity, scale=scale,
             quat=read(['rot_0', 'rot_1', 'rot_2', 'rot_3']),
             albedo=np.clip(.5 + .28209479177387814 * read(['f_dc_0', 'f_dc_1', 'f_dc_2']), 0., 1.))
    if not all(np.isfinite(x).all() for x in g.values()):
        raise ValueError('nonfinite checkpoint parameters')
    if np.any(scale <= 0) or np.any(np.linalg.norm(g['quat'], axis=1) <= 1e-12):
        raise ValueError('invalid checkpoint scale/quaternion')
    g['_metadata'] = dict(path=str(path), sha256=digest, gaussians=len(g['mu']),
        color='SH0 clipped 0.5 + C0*f_dc', ignored_full_sh_coefficients=sum(n.startswith('f_rest_') for n in names),
        filter_3D_present='filter_3D' in names, filter_3D_applied=False,
        native_degenerate_inverse_covariance_count=int((scale.min(axis=1) <= 1e-7).sum()),
        proxy_axis_normals_computed=False, row_id_mapping='identity / original PLY row')
    return g


def gpu_guard():
    """Refuse any other compute PID, including unrelated jobs of this user."""
    gpu = subprocess.run(['nvidia-smi', '--query-gpu=index,name,memory.used,utilization.gpu',
                          '--format=csv,noheader'], capture_output=True, text=True, check=True).stdout.strip()
    rows = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,process_name,used_gpu_memory',
                           '--format=csv,noheader'], capture_output=True, text=True, check=True).stdout.strip()
    entries = []
    for line in rows.splitlines():
        if not line.strip():
            continue
        pid = int(line.split(',', 1)[0].strip())
        owner = subprocess.run(['ps', '-o', 'user=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()
        entries.append(dict(pid=pid, owner=owner, gpu_process=line))
    record = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  pid=os.getpid(), uid=os.getuid(), gpu=gpu, processes=entries)
    logs = STAGE / 'native_logs'
    logs.mkdir(parents=True, exist_ok=True)
    with (logs / 'GPU_GUARD.jsonl').open('a') as handle:
        handle.write(json.dumps(record) + '\n')
    foreign = [row for row in entries if row['pid'] != os.getpid()]
    if foreign:
        raise RuntimeError('GPU_BUSY: other compute jobs present: ' + json.dumps(foreign))
    return record


def source_hashes():
    build = json.loads((NATIVE / 'BUILD.json').read_text())
    return dict(build_hash=build['build_hash'], source_hash=build['source_hash'],
                wrapper_sha256=sha256(__file__),
                source_manifest_sha256=sha256(NATIVE / 'SOURCE_MANIFEST.json'),
                variants=build['variants'], render_settings=RENDER_SETTINGS)


def _extension(patched):
    variant = 'patched' if patched else 'unpatched'
    if variant not in _EXTENSIONS:
        import torch  # Loads the shared Torch libraries before importing native CUDA.
        metadata = json.loads((NATIVE / 'BUILD.json').read_text())['variants'][variant]
        path = Path(metadata['path'])
        if sha256(path) != metadata['sha256']:
            raise ValueError('native binary SHA256 mismatch')
        name = '_hybrid_raster_' + variant + '._C'
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        _EXTENSIONS[variant] = module
    return _EXTENSIONS[variant]


def render_native(g, cam, patched=True):
    """One real CUDA traversal for all returned fields; no proxy replacement."""
    gpu_guard()
    import torch
    c = camera_record(cam)
    view, full = camera_matrices(c)
    h, w = c['native_height'], c['native_width']
    k = np.asarray(c['native_K'], np.float64)
    t = lambda x: torch.as_tensor(np.asarray(x), dtype=torch.float32, device='cuda').contiguous()
    xyz, sc, rot = t(g['mu']), t(g['scale']), t(g['quat'])
    rot = rot / rot.norm(dim=1, keepdim=True).clamp(min=1e-12)
    empty = torch.empty(0, device='cuda')
    center = np.linalg.inv(np.asarray(c['w2c']))[:3, 3]
    args = [torch.ones(3, device='cuda'), xyz, t(g['albedo']), t(g['opacity']).reshape(-1, 1),
            sc, rot, 1., empty, t(view), t(full), w/(2*k[0, 0]), h/(2*k[1, 1]),
            0., h, w, empty, 0, t(center), False, True, False]
    extra = {}
    if patched:
        extra = dict(topk_id=torch.full((h, w, 4), -1, device='cuda', dtype=torch.int32),
                     topk_w=torch.zeros((h, w, 4), device='cuda'),
                     topk_depth=torch.zeros((h, w, 4), device='cuda'),
                     topk_normal=torch.zeros((h, w, 4, 3), device='cuda'),
                     moment2=torch.zeros((h, w), device='cuda'),
                     normal_len=torch.zeros((h, w), device='cuda'))
        args.extend(extra.values())
    native = _extension(patched)
    torch.cuda.synchronize()
    start = time.perf_counter()
    with torch.no_grad():
        _, rgb, alpha, normal, depth, median, radii, *_ = native.rasterize_gaussians(*args)
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - start
    with (STAGE / 'native_logs/RENDER_TIMES.jsonl').open('a') as handle:
        handle.write(json.dumps(dict(pid=os.getpid(), patched=bool(patched),
            camera_hash=camera_hash(cam), gaussian_count=len(g['mu']),
            cuda_synchronized_wall_seconds=elapsed,
            utc=datetime.datetime.now(datetime.timezone.utc).isoformat())) + '\n')
    array = lambda x: x.detach().cpu().numpy()
    raw = dict(rgb=np.moveaxis(array(rgb), 0, -1), alpha=array(alpha[0]),
               depth=array(depth[0]), median_depth=array(median[0]),
               normal=np.moveaxis(array(normal), 0, -1), radii=array(radii))
    raw.update({key: array(value) for key, value in extra.items()})
    if patched:
        validate_raw(raw, len(g['mu']), (h, w))
    elif not all(np.isfinite(value).all() for value in raw.values()):
        raise ValueError('nonfinite unpatched native state')
    return raw


render = render_native


def validate_raw(raw, gaussian_count, shape):
    h, w = shape
    dimensions = dict(rgb=(h, w, 3), alpha=(h, w), depth=(h, w), median_depth=(h, w),
                      normal=(h, w, 3), radii=(gaussian_count,), topk_id=(h, w, 4),
                      topk_w=(h, w, 4), topk_depth=(h, w, 4), topk_normal=(h, w, 4, 3),
                      moment2=(h, w), normal_len=(h, w))
    for key, expected in dimensions.items():
        if key not in raw or raw[key].shape != expected:
            raise ValueError('native field dimension mismatch: ' + key)
        if not np.isfinite(raw[key]).all():
            raise ValueError('nonfinite native field: ' + key)
    ids, weights = raw['topk_id'], raw['topk_w']
    if ids.dtype.kind not in 'iu' or np.any(ids < -1) or np.any(ids >= gaussian_count):
        raise ValueError('invalid original Gaussian IDs')
    empty = ids == -1
    if np.any(weights[empty] != 0) or np.any(raw['topk_depth'][empty] != 0) or np.any(raw['topk_normal'][empty] != 0):
        raise ValueError('empty contribution slots must have zero fields')
    if np.any(weights < 0) or np.any(np.diff(weights, axis=-1) > 0):
        raise ValueError('invalid contribution weight ordering')
    if np.max(weights.sum(-1) - raw['alpha']) > 3e-6:
        raise ValueError('top4 alpha mass exceeds total alpha')
    if np.any(raw['alpha'] < 0) or np.any(raw['alpha'] > 1):
        raise ValueError('alpha outside [0,1]')
    empty_ray = raw['alpha'] == 0
    if np.any(ids[empty_ray] != -1):
        raise ValueError('empty ray has contributor IDs')
    return True


def compare_calibration(patched, unpatched):
    errors = {}
    for key in ('rgb', 'alpha', 'depth', 'normal', 'median_depth'):
        a, b = patched[key].astype(np.float64), unpatched[key].astype(np.float64)
        if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError('calibration field mismatch: ' + key)
        error = np.abs(a-b)
        absolute = float(error.max(initial=0))
        relative = float((error / np.maximum(np.abs(b), 1e-8)).max(initial=0))
        passed = absolute <= 3e-6
        if key in ('depth', 'median_depth'):
            passed = passed or (absolute <= 1e-5 and relative <= 3e-6)
        errors[key] = dict(max_abs=absolute, mean_abs=float(error.mean()), max_rel=relative, passed=passed)
    return dict(status='PASS' if all(x['passed'] for x in errors.values()) else 'ENGINEERING_INVALID', errors=errors)


def calibrate_primary():
    """Only the frozen Lego/Chair F1/F41 engineering slice, never C/arc."""
    inputs_path = ROOT / 'artifacts/direct_curve_global_fit_probe/INPUTS.json'
    inputs = json.loads(inputs_path.read_text())
    out = STAGE / 'calibration'
    out.mkdir(parents=True, exist_ok=True)
    sources = source_hashes()
    report = dict(status='RUNNING', source_hash=sources['source_hash'], build_hash=sources['build_hash'],
                  source=sources, inputs_sha256=sha256(inputs_path), frames=[],
                  qualifications=['SH0 only', 'frozen vanilla GS; no filter_3D or RaDe training',
                                  'native splat normals unverified as physical surface normals',
                                  'top4 may omit substantial alpha; full moments use every accepted contribution'])
    atomic_json(out / 'CALIBRATION.json', report)
    try:
        for scene in ('lego', 'chair'):
            checkpoint = inputs['scenes'][scene]['checkpoint']
            g = load_checkpoint(checkpoint['path'], checkpoint['sha256'])
            for index in (1, 41):
                cam = inputs['scenes'][scene]['cameras'][str(index)]
                patched = render_native(g, cam, True)
                unpatched = render_native(g, cam, False)
                result = compare_calibration(patched, unpatched)
                if result['status'] != 'PASS':
                    raise RuntimeError(json.dumps(result))
                path = out / f'{scene}_F{index}.npz'
                temp = path.with_name(path.name + '.partial')
                with temp.open('wb') as handle:
                    np.savez_compressed(handle, **patched)
                os.replace(temp, path)
                alpha = patched['alpha']
                foreground = alpha >= .08
                coverage = patched['topk_w'].sum(-1)[foreground] / alpha[foreground]
                item = dict(scene=scene, index=index, path=str(path), sha256=sha256(path),
                            camera_hash=camera_hash(cam), camera=camera_record(cam),
                            exact_input_camera=cam, exact_input_camera_sha256=json_hash(cam),
                            checkpoint_sha256=checkpoint['sha256'], checkpoint=g['_metadata'],
                            calibration=result, source=sources,
                            diagnostics=dict(foreground_pixels=int(foreground.sum()),
                                top4_alpha_coverage_mean=float(coverage.mean()),
                                top4_alpha_coverage_p05=float(np.quantile(coverage, .05)),
                                max_excess_top4_alpha=float((patched['topk_w'].sum(-1)-alpha).max()),
                                bytes=path.stat().st_size))
                atomic_json(path.with_suffix('.json'), item)
                report['frames'].append(item)
                atomic_json(out / 'CALIBRATION.json', report)
                print(json.dumps(dict(scene=scene, index=index, calibration=result,
                                      diagnostics=item['diagnostics'])), flush=True)
                del patched, unpatched
        report['status'] = 'PASS'
    except Exception as error:
        report['status'] = 'ENGINEERING_INVALID'
        report['error'] = repr(error)
        atomic_json(out / 'CALIBRATION.json', report)
        raise
    atomic_json(out / 'CALIBRATION.json', report)
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--calibrate-primary', action='store_true')
    options = parser.parse_args()
    if options.calibrate_primary:
        calibrate_primary()
    else:
        parser.error('choose --calibrate-primary')
