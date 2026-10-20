"""Exploratory CPU KMeans on PartField features. Clusters have NO part semantics."""
import hashlib
import json
import os
from pathlib import Path

for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '2'

import numpy as np
from threadpoolctl import threadpool_limits


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def cluster_summary(labels, z):
    if len(labels) != len(z) or not np.isin(labels, [0, 1, 2]).all():
        raise ValueError('row or cluster ID mismatch')
    edges = np.quantile(z, [0, .25, .5, .75, 1])
    bins = np.clip(np.searchsorted(edges[1:-1], z, side='right'), 0, 3)
    return {'counts': np.bincount(labels, minlength=3).astype(int).tolist(),
            'z_quartile_by_cluster': np.array([[np.count_nonzero((labels == c) & (bins == b))
                                                for b in range(4)] for c in range(3)]).tolist(),
            'z_edges': edges.tolist()}


def main():
    threadpool_limits(2)
    root = Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03')
    source = Path('/home/u00134/3dgs_line/tier1/out/multiscene_foundation/training/ficus/seed_1729/checkpoints/point_cloud/iteration_30000/point_cloud.ply')
    result = root / 'cpu_probe_v03'
    feature_path = result / 'full_features.npy'
    manifest = json.loads((result/'full_manifest.json').read_text())
    if manifest['source_sha256'] != '9afacac137474a50c5db52e41d2f1656b1e5f22ee5b6804e7e819697679cebac' or sha256(source) != manifest['source_sha256']:
        raise SystemExit('SOURCE_IDENTITY_FAILED')
    if sha256(feature_path) != manifest['features_sha256']:
        raise SystemExit('FEATURE_IDENTITY_FAILED')
    labels_path = result / 'k3_labels.npy'
    summary_path = result / 'k3_summary.json'
    image_path = result / 'k3_full_subject_projections.png'
    if any(p.exists() for p in (labels_path, summary_path, image_path)):
        raise SystemExit('EXISTING_OUTPUT_REFUSE_OVERWRITE')
    from plyfile import PlyData
    from sklearn.cluster import KMeans
    p = PlyData.read(source)['vertex']
    xyz = np.stack([p[k] for k in ('x','y','z')], axis=1).astype('f4')
    feat = np.load(feature_path, mmap_mode='r')
    if feat.shape != (284835,448) or xyz.shape != (284835,3):
        raise SystemExit('ROW_MISMATCH')
    print('KMEANS_START', len(feat), flush=True)
    model = KMeans(n_clusters=3, random_state=0, n_init=3, max_iter=100, algorithm='lloyd')
    labels = model.fit_predict(feat).astype('u1')
    summary = cluster_summary(labels, xyz[:,2])
    summary.update(status='EXPLORATORY_CLUSTERS_NOT_SEMANTIC_PARTS',
                   source_sha256=manifest['source_sha256'], features_sha256=manifest['features_sha256'],
                   source_rows=len(labels), row_mapping='labels[i] refers exactly to original PLY row i',
                   k=3, random_state=0, n_init=3, max_iter=100, algorithm='lloyd',
                   inertia=float(model.inertia_), center_shape=list(model.cluster_centers_.shape),
                   caveat='KMeans IDs are not pot/trunk/canopy; no reserved-view original GS edit; no semantic GO')
    np.save(labels_path, labels)
    summary['labels_sha256'] = sha256(labels_path)
    summary_path.write_text(json.dumps(summary, indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rng = np.random.default_rng(1729)
    show = np.sort(rng.choice(len(xyz), min(45000,len(xyz)), replace=False))
    colors = np.asarray(['#db583b','#299975','#5d76c9'])[labels[show]]
    fig, axes = plt.subplots(1,2,figsize=(13,6),dpi=150)
    for ax, dims, name in zip(axes,[(0,2),(1,2)],['XZ: full source kernels','YZ: full source kernels']):
        ax.scatter(xyz[show,dims[0]],xyz[show,dims[1]],s=1,c=colors,alpha=.28,rasterized=True)
        ax.set_xlabel(['X','Y'][dims[0]])
        ax.set_ylabel('Z')
        ax.set_title(name)
        ax.set_xlim(float(xyz[:,dims[0]].min()),float(xyz[:,dims[0]].max()))
        ax.set_ylim(float(xyz[:,2].min()),float(xyz[:,2].max()))
        ax.set_aspect('equal',adjustable='box')
    for c,color in enumerate(['#db583b','#299975','#5d76c9']):
        axes[0].scatter([],[],c=color,label=f'cluster {c} ({summary["counts"][c]} kernels)')
    axes[0].legend(markerscale=4,frameon=False,loc='upper right',fontsize=8)
    fig.suptitle('PartField CPU / KMeans k=3 — exploratory, NOT verified parts')
    fig.tight_layout()
    fig.savefig(image_path)
    plt.close(fig)
    print('KMEANS_RESULT',json.dumps(summary),flush=True)
    print('KMEANS_IMAGE',image_path,flush=True)


if __name__=='__main__':
    main()
