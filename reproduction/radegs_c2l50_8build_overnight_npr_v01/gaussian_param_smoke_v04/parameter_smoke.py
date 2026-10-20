"""CPU-only frozen-source Gaussian parameter clustering smoke, NOT semantic part labels.

9 controlled k=3 arms. Source PLY row i is the stable original kernel ID.
FIT cameras train_r_80/train_r_7 only; reserved cameras are never read here.
"""
import hashlib
import json
import os
import resource
import sys
import time
from pathlib import Path

for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

import numpy as np
from scipy.spatial.transform import Rotation

SH_C0 = 0.28209479177387814


def covariance_and_world_axis(log_scales, q_wxyz):
    scales = np.exp(np.asarray(log_scales, dtype=np.float64))
    q = np.asarray(q_wxyz, dtype=np.float64)
    norm = np.linalg.norm(q, axis=1)
    if (scales.shape[1:] != (3,) or q.shape != (len(scales), 4)
            or not np.isfinite(scales).all() or not np.isfinite(norm).all() or np.any(norm < 1e-12)):
        raise ValueError('invalid Gaussian scale or quaternion')
    rot = Rotation.from_quat((q / norm[:, None])[:, [1, 2, 3, 0]]).as_matrix()
    cov = (rot * (scales * scales)[:, None, :]) @ np.swapaxes(rot, 1, 2)
    return cov, scales.max(axis=1)


def projected_major_sigma(image_cov_with_floor, floor):
    c = np.asarray(image_cov_with_floor, dtype=np.float64).copy()
    c[:, 0, 0] -= floor
    c[:, 1, 1] -= floor
    eig = np.linalg.eigvalsh(c)[:, -1]
    if not np.isfinite(eig).all() or np.any(eig <= 0):
        raise ValueError('invalid projected major eigenvalue')
    return np.sqrt(eig)


def distance_weighted_world_axis(world_axis, depth_z, fx, fy):
    world_axis = np.asarray(world_axis)
    depth_z = np.asarray(depth_z)
    if np.any(depth_z <= 0) or not np.isfinite(depth_z).all():
        raise ValueError('invalid camera depth')
    return world_axis * np.sqrt(float(fx)*float(fy)) / depth_z


def sh_dc_rgb(dc):
    return np.maximum(0.0, 0.5 + SH_C0*np.asarray(dc, dtype=np.float64))


def standardize(x):
    x = np.asarray(x, dtype=np.float64)
    if not np.isfinite(x).all() or not len(x):
        raise ValueError('nonfinite or empty features')
    mean = x.mean(0)
    std = x.std(0)
    if np.any(std < 1e-12):
        raise ValueError('degenerate feature channel')
    return ((x - mean) / std).astype(np.float32)


def equal_block_features(blocks):
    if any(len(x) != len(blocks[0]) for x in blocks):
        raise ValueError('block row mismatch')
    return np.concatenate([standardize(x)/np.sqrt(np.asarray(x).shape[1]) for x in blocks], axis=1)


def prepare_arm_features(name, feat):
    # The fusion has ALREADY been standardized blockwise. Re-standardizing
    # its columns here would silently undo the equal-block-weight contract.
    return np.asarray(feat, dtype=np.float32) if name.startswith('I_fusion_') else standardize(feat)


def validate_fit_manifest(manifest, source, digest):
    views = manifest.get('fit_cameras', [])
    if (manifest.get('scene') != 'ficus' or manifest.get('model') != str(source)
            or manifest.get('model_sha256') != digest
            or [c.get('view') for c in views] != ['train_r_80', 'train_r_7']):
        raise ValueError('fit camera or source manifest mismatch')
    return views


def validate_partition(labels):
    unique = np.unique(labels)
    if not np.array_equal(unique, [0, 1, 2]):
        raise ValueError('expected three populated clusters')
    return len(unique)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def proxy_stats(labels, z):
    # Distribution against GEOMETRIC height quartiles, not pot/trunk/crown GT.
    edges = np.quantile(z, [0., .25, .50, .75, 1.])
    bins = np.searchsorted(edges[1:-1], z, side='right')
    table = np.array([[np.count_nonzero((labels == k) & (bins == b)) for b in range(4)] for k in range(3)])
    return {'counts': table.sum(1).astype(int).tolist(), 'z_quartile_by_cluster': table.astype(int).tolist(),
            'z_edges': [float(e) for e in edges]}


def main():
    overall_start = time.monotonic()
    from threadpoolctl import threadpool_limits
    threadpool_limits(2)
    import argparse
    from plyfile import PlyData
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--source-sha256', required=True)
    p.add_argument('--fit-manifest', type=Path, required=True)
    p.add_argument('--fit-manifest-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--native-code', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists() or sha256(args.source) != args.source_sha256:
        raise SystemExit('OUTPUT_EXISTS_OR_SOURCE_HASH_MISMATCH')
    if sha256(args.fit_manifest) != args.fit_manifest_sha256:
        raise SystemExit('FIT_CAMERA_MANIFEST_HASH_MISMATCH')
    raw = PlyData.read(args.source)['vertex'].data
    if len(raw) != 284835 or 'source_index' in raw.dtype.names:
        raise SystemExit('SOURCE_SCHEMA_MISMATCH')
    xyz = np.stack([raw[k] for k in ('x','y','z')], axis=1).astype(np.float64)
    logscales = np.stack([raw[f'scale_{k}'] for k in range(3)], axis=1)
    quat = np.stack([raw[f'rot_{k}'] for k in range(4)], axis=1)
    dc = np.stack([raw[f'f_dc_{k}'] for k in range(3)], axis=1)
    opacity = np.asarray(raw['opacity'], dtype=np.float64)
    cov, long_axis = covariance_and_world_axis(logscales, quat)
    if not np.isfinite(xyz).all() or not np.isfinite(opacity).all():
        raise SystemExit('NONFINITE_SOURCE')
    cams = validate_fit_manifest(json.loads(args.fit_manifest.read_text()), args.source, args.source_sha256)
    if not args.native_code.is_dir():
        raise SystemExit('NATIVE_CODE_MISSING')
    sys.path.insert(0, str(args.native_code))
    from renderer import project_cov, colors
    from format import activate
    a = activate(raw.copy())
    if not np.allclose(a['covariance'], cov, rtol=1e-6, atol=1e-9):
        raise SystemExit('NATIVE_COVARIANCE_MISMATCH')
    if not np.allclose(a['means'], xyz):
        raise SystemExit('NATIVE_XYZ_MISMATCH')
    dc_rgb = sh_dc_rgb(dc)
    if not np.allclose(dc_rgb, sh_dc_rgb(a['SH'][:,:,0]), atol=1e-10):
        raise SystemExit('DC_FORMAT_MISMATCH')
    project_sizes, distance_sizes, rgb_views = [], [], []
    floor = .3
    for c in cams:
        uv, z, screen_cov = project_cov(xyz, cov, c, floor)
        eligible = (z > .2) & np.isfinite(z) & np.isfinite(uv).all(1) & np.isfinite(screen_cov).all((1,2))
        in_frame = eligible & (uv[:,0]>=0) & (uv[:,0]<c['width']) & (uv[:,1]>=0) & (uv[:,1]<c['height'])
        if not np.all(eligible) or not np.all(in_frame):
            raise SystemExit(f'COMMON_SUPPORT_NOT_FULL_{c["view"]}_{int(in_frame.sum())}')
        project_sizes.append(projected_major_sigma(screen_cov, floor))
        distance_sizes.append(distance_weighted_world_axis(long_axis, z, c['fx'], c['fy']))
        rgb_views.append(colors(a, c))
    # Crucial SH0 equivalence check using the native color evaluator with higher orders zeroed.
    dc_only = dict(a)
    dc_only['SH'] = np.zeros_like(a['SH'])
    dc_only['SH'][:,:,0] = a['SH'][:,:,0]
    for c in cams:
        if not np.allclose(colors(dc_only, c), dc_rgb, rtol=0, atol=3e-7):
            raise SystemExit('DC_RENDERER_EQUIVALENCE_FAILURE')
    shape = np.sort(logscales, axis=1)
    shape_opacity = np.column_stack([shape, opacity])
    rgb_concat = np.concatenate(rgb_views, axis=1)
    rgb_mean = np.mean(rgb_views, axis=0)
    axis_distance = np.mean(np.log(np.stack(distance_sizes, axis=1)), axis=1)[:, None]
    axis_projection = np.mean(np.log(np.stack(project_sizes, axis=1)), axis=1)[:, None]
    blocks = {
        'A_world_long': np.max(logscales, axis=1)[:,None],
        'B_distance_long': axis_distance,
        'C_projected_long': axis_projection,
        'D_rgb_dc': dc_rgb,
        'E_rgb_sh_fit_concat': rgb_concat,
        'F_rgb_sh_fit_mean': rgb_mean,
        'G_xyz': xyz,
        'H_shape_opacity': shape_opacity,
        'I_fusion_xyz_sh_projected': equal_block_features([xyz, rgb_concat, axis_projection]),
    }
    args.output.mkdir(parents=True)
    preprocess_seconds=round(time.monotonic()-overall_start,2)
    artifact = {'status':'PARAMETER_CLUSTER_SMOKE_NOT_SEMANTIC_LABELS',
                'source_sha256':args.source_sha256,'source_rows':len(xyz),
                'source_index':'original PLY row i; no explicit source_index field',
                'fit_views':[c['view'] for c in cams], 'fit_camera_manifest_sha256':args.fit_manifest_sha256,
                'reserved_pixel_data_opened':False,
                'projected_covariance_floor_removed':floor,
                'distance_formula':'sqrt(fx*fy)/camera_z * max(exp(log_scale))',
                'view_aggregate':'mean of per-view log(size); full SH RGB concatenates FIT views, mean is ablation',
                'standardization':'per-dimension z score for each arm; fusion equalizes blocks by sqrt(block_dimension)',
                'common_eligible_rows':len(xyz),'unknown_rows':0,'k':3,'seed':0,'n_init':3,'max_iter':100,
                'scoring':'z height-quartile contingency is a geometric diagnostic, not semantic truth; no labels from reserved views',
                'preprocess_seconds':preprocess_seconds,'arms':{}}
    for name, feat in blocks.items():
        start=time.monotonic()
        feat=prepare_arm_features(name, feat)
        if feat.shape[0]!=len(xyz):
            raise SystemExit('FEATURE_ROW_COUNT_MISMATCH')
        km=KMeans(n_clusters=3,random_state=0,n_init=3,max_iter=100,algorithm='lloyd')
        labels=km.fit_predict(feat).astype(np.uint8)
        # Independent initialization rerun is a stability diagnostic, NOT held-out accuracy.
        km_alt=KMeans(n_clusters=3,random_state=1,n_init=3,max_iter=100,algorithm='lloyd')
        labels_alt=km_alt.fit_predict(feat)
        actual_k=validate_partition(labels)
        alt_k=validate_partition(labels_alt)
        path=args.output/(name+'_labels.npy')
        np.save(path,labels)
        stats=proxy_stats(labels,xyz[:,2]);stats.update(
            feature_dim=int(feat.shape[1]), feature_input_min=float(np.min(blocks[name])), feature_input_max=float(np.max(blocks[name])),
            inertia=float(km.inertia_), seed_stability_ari=float(adjusted_rand_score(labels,labels_alt)),
            actual_k=actual_k, alt_actual_k=alt_k,
            n_iter=int(km.n_iter_), alt_n_iter=int(km_alt.n_iter_), max_iter_hit=bool(km.n_iter_ >= 100 or km_alt.n_iter_ >= 100),
            seconds=float(round(time.monotonic()-start,2)), labels_sha256=sha256(path))
        artifact['arms'][name]=stats
        print('ARM_RESULT',name,json.dumps(stats),flush=True)
        (args.output/'SUMMARY.json').write_text(json.dumps(artifact,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    # Consistent source-ID subsample, full subject bounds, and same view orientation for every panel.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    ids=np.sort(np.random.default_rng(1729).choice(len(xyz),45000,replace=False))
    fig,axes=plt.subplots(len(blocks),2,figsize=(14,3.4*len(blocks)),dpi=125)
    palette=np.asarray(['#d45d42','#229e85','#5979d8'])
    for i,name in enumerate(blocks):
        labels=np.load(args.output/(name+'_labels.npy'),allow_pickle=False)
        cc=palette[labels[ids]]
        for j,dim in enumerate((0,1)):
            ax=axes[i,j]
            ax.scatter(xyz[ids,dim],xyz[ids,2],s=.8,c=cc,alpha=.31,rasterized=True)
            ax.set_xlim(float(np.min(xyz[:,dim])),float(np.max(xyz[:,dim])))
            ax.set_ylim(float(np.min(xyz[:,2])),float(np.max(xyz[:,2])))
            ax.set_aspect('equal',adjustable='box')
            ax.set_title(name+(' XZ' if j==0 else ' YZ'),fontsize=10)
            ax.set_xlabel('X' if j==0 else 'Y');ax.set_ylabel('Z')
    fig.suptitle('Ficus original Gaussian parameters / k=3 — exploratory clusters, NOT parts',fontsize=14)
    fig.tight_layout(rect=(0,0,1,.99));fig.savefig(args.output/'PARAMETER_ARMS_XZ_YZ.png');plt.close(fig)
    artifact['image']='PARAMETER_ARMS_XZ_YZ.png'
    artifact['image_sha256']=sha256(args.output/artifact['image'])
    artifact['total_wall_seconds']=round(time.monotonic()-overall_start,2)
    artifact['maxrss_kib_linux']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    (args.output/'SUMMARY.json').write_text(json.dumps(artifact,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    print('PARAMETER_SMOKE_DONE',str(args.output/'SUMMARY.json'),flush=True)


if __name__=='__main__':
    main()
