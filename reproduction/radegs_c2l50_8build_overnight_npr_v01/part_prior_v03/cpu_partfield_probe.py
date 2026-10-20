"""CPU-only independent PartField feature probe for frozen original Ficus rows.

NOT a part classifier or Gaussian edit. Encoder uses a deterministic subset of original
centers; every query coordinate is normalized with the full original bbox. Full output
row i corresponds to untouched source PLY row i; smoke saves explicit query row IDs.
"""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
import sys
import time

for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '2'
import numpy as np


def normalize_full_cloud(points):
    lo, hi = points.min(0), points.max(0)
    diameter = (hi - lo).max()
    if not np.isfinite(diameter) or diameter <= 0:
        raise ValueError('degenerate bounding box')
    scale = np.float32(1.8) / diameter
    return ((points - (lo + hi) * np.float32(.5)) * scale).astype(np.float32)


def fixed_source_subset(n, count):
    if count < 1 or count > n:
        raise ValueError('invalid subset size')
    return np.sort(np.random.default_rng(1729).choice(n, count, replace=False).astype(np.int64))


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def run(args):
    # Defense in depth: no CUDA devices even if caller forgot the shell mask.
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    from threadpoolctl import threadpool_limits
    threadpool_limits(limits=2)
    source = Path(args.source)
    root = Path(args.root)
    if not source.is_file() or sha256(source) != args.source_sha256:
        raise SystemExit('SOURCE_IDENTITY_FAILED')
    checkpoint = root / 'checkpoint/model_objaverse.ckpt'
    if not checkpoint.is_file() or sha256(checkpoint) != args.checkpoint_sha256:
        raise SystemExit('CHECKPOINT_IDENTITY_FAILED')
    result = root / 'cpu_probe_v03'
    result.mkdir(parents=True, exist_ok=True)
    label = args.mode
    out = result / (label + '_features.npy')
    pending = result / (label + '_features.part.npy')
    manifest = result / (label + '_manifest.json')
    if out.exists() or pending.exists() or manifest.exists():
        raise SystemExit('OUTPUT_EXISTS_REFUSE_OVERWRITE')
    from plyfile import PlyData
    ply = PlyData.read(source)
    vertices = ply['vertex']
    if len(vertices) != 284835:
        raise SystemExit('SOURCE_ROW_COUNT_MISMATCH')
    points = np.stack([vertices[k] for k in ('x', 'y', 'z')], axis=1).astype('f4')
    if not np.isfinite(points).all():
        raise SystemExit('NONFINITE_SOURCE_XYZ')
    normalized = normalize_full_cloud(points)
    count = 1024 if args.mode == 'smoke' else 8192
    ids = fixed_source_subset(len(points), count)
    query_ids = ids[:128] if args.mode == 'smoke' else np.arange(len(points), dtype=np.int64)
    import torch
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    if torch.cuda.is_available():
        raise SystemExit('CUDA_VISIBLE_REFUSE_CPU_PROBE')
    code = root / 'third_party/PartField'
    actual_code_sha = subprocess.check_output(['git', '-C', str(code), 'rev-parse', 'HEAD'], text=True).strip()
    if actual_code_sha != '373025dbd283bb44cc4a6dc78c99994dbc91de32' or subprocess.run(
        ['git', '-C', str(code), 'diff', '--quiet', 'HEAD', '--'], check=False
    ).returncode != 0:
        raise SystemExit('OFFICIAL_CODE_IDENTITY_FAILED')
    sys.path.insert(0, str(code))
    from yacs.config import CfgNode
    from partfield.config.defaults import _C
    import partfield.model_trainer_pvcnn_only_demo as official
    from partfield.model.PVCNN.encoder_pc import sample_triplane_feat
    cfg = _C.clone()
    cfg.merge_from_file(str(code / 'configs/final/demo.yaml'))
    cfg.is_pc = True
    cfg.use_2d_feat = False
    constructor = official.TriPlanePC2Encoder
    def cpu_constructor(*a, **kw):
        kw['device'] = 'cpu'
        return constructor(*a, **kw)
    official.TriPlanePC2Encoder = cpu_constructor
    model = official.Model(cfg)
    # Official release checkpoint; only permit the two non-tensor globals used
    # by Lightning's metadata, not arbitrary pickle code.
    torch.serialization.add_safe_globals([CfgNode, set])
    loaded = torch.load(checkpoint, map_location='cpu', weights_only=True)
    model.load_state_dict(loaded['state_dict'], strict=True)
    model.eval()
    if any(p.device.type != 'cpu' for p in model.parameters()):
        raise SystemExit('MODEL_NOT_CPU_ONLY')
    print('CPU_MODEL_READY', len(ids), len(query_ids), flush=True)
    t0 = time.monotonic()
    with torch.inference_mode():
        inp = torch.from_numpy(normalized[ids]).unsqueeze(0)
        encoded = model.pvcnn(inp, inp)
        print('CPU_ENCODER_READY', round(time.monotonic()-t0, 2), flush=True)
        planes = model.triplane_transformer(encoded)
        part_planes = planes[:, :, 64:]
        if tuple(part_planes.shape[:3]) != (1, 3, 448):
            raise SystemExit('TRIPLANE_SHAPE_MISMATCH')
        print('CPU_TRIPLANES_READY', round(time.monotonic()-t0, 2), flush=True)
        arr = np.lib.format.open_memmap(pending, mode='w+', dtype='f4', shape=(len(query_ids), 448))
        for start in range(0, len(query_ids), 2048):
            indices = query_ids[start:start+2048]
            q = torch.from_numpy(normalized[indices]).unsqueeze(0)
            features = sample_triplane_feat(part_planes, q).squeeze(0).numpy()
            if features.shape != (len(indices), 448) or not np.isfinite(features).all():
                raise SystemExit('FEATURE_SHAPE_OR_FINITE_FAILURE')
            arr[start:start+len(indices)] = features
            if start % (2048*16) == 0:
                print('CPU_QUERY_PROGRESS', start+len(indices), len(query_ids), flush=True)
        arr.flush()
        del arr
    os.replace(pending, out)
    data = dict(status='FEATURES_ONLY_NOT_CLASSIFIED', source_sha256=args.source_sha256,
                checkpoint_sha256=args.checkpoint_sha256, source_rows=len(points),
                encoder_input_rows=len(ids), subset_seed=1729,
                query_rows=len(query_ids), feature_shape=[len(query_ids), 448],
                source_index_convention='original PLY row i; never re-sorted in feature output',
                query_source_index='first 128 sorted subset ids' if args.mode == 'smoke' else 'identity 0..284834',
                encoder_subset_sha256=hashlib.sha256(ids.tobytes()).hexdigest(),
                features_sha256=sha256(out), elapsed_seconds=round(time.monotonic()-t0, 2),
                cpu_threads=2, cuda_visible=False, official_code_sha=actual_code_sha,
                caveat='subsampled encoder deviates from official full-cloud inference; not part labels or source GS edit')
    if args.mode == 'smoke':
        np.save(result / 'smoke_source_indices.npy', query_ids)
    manifest.write_text(json.dumps(data, indent=2) + '\n')
    print('CPU_FEATURES_READY', json.dumps(data), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    p.add_argument('--source', required=True)
    p.add_argument('--source-sha256', required=True)
    p.add_argument('--checkpoint-sha256', required=True)
    p.add_argument('--mode', choices=['smoke', 'full'], required=True)
    run(p.parse_args())
