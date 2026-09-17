"""Finite, persistent 3D endpoint bridges. No image, mesh or label inputs.

Good-continuation linking is prior art (e.g. NerVE); this module is a deliberately
simple geometric hypothesis generator, not a topology oracle.
"""
from collections import Counter
import numpy as np
from scipy.spatial import cKDTree


DEFAULTS = dict(max_gap_spacing=12., max_gap_extent=.06, min_gap_spacing=.75,
                tangent_cos=.7071067811865476, hermite_tension=.7, samples=48,
                max_arc_ratio=1.18, max_total_turn_deg=90., support_radius=2.5,
                min_supported_fraction=.9, max_support_distance=4.)


def unit(x):
    return np.asarray(x, dtype=float) / max(float(np.linalg.norm(x)), 1e-12)


def hermite(a, b, outward_a, outward_b, samples=48, tension=.7):
    """b's incoming derivative is opposite its outward endpoint tangent."""
    a, b = np.asarray(a), np.asarray(b)
    d = np.linalg.norm(b-a)
    t = np.linspace(0., 1., samples)[:, None]
    return ((2*t**3-3*t**2+1)*a + (t**3-2*t**2+t)*tension*d*unit(outward_a)
            + (-2*t**3+3*t**2)*b - (t**3-t**2)*tension*d*unit(outward_b))


def endpoints(paths):
    points, tangents, refs = [], [], []
    for i, p in enumerate(paths):
        if len(p) < 2:
            continue
        for side, index, inner in ((0, 0, min(2, len(p)-1)), (1, -1, -min(3, len(p)))):
            points.append(p[index]); tangents.append(unit(p[index]-p[inner])); refs.append([i, side])
    return np.asarray(points), np.asarray(tangents), refs


def propose(paths, gaussian_centers, cfg=None):
    """Returns accepted geometric hypotheses, every tested pair's audit, scale.

    All thresholds are global and spacing-normalized. Density support uses nearest
    defloated Gaussian center distances; no covariance normals or labels are used.
    """
    cfg = dict(DEFAULTS if cfg is None else cfg)
    centers = np.asarray(gaussian_centers)
    tree = cKDTree(centers)
    nn = tree.query(centers, k=2)[0][:, 1]
    spacing = max(float(np.median(nn[nn > 1e-10])), 1e-8)
    extent = float(np.linalg.norm(np.quantile(centers,.99,axis=0)-np.quantile(centers,.01,axis=0)))
    limit = min(cfg['max_gap_spacing']*spacing, cfg['max_gap_extent']*extent)
    pts, ts, refs = endpoints(paths)
    accepted, audit = [], []
    pairs = sorted(cKDTree(pts).query_pairs(limit)) if len(pts) else []
    for ei, ej in pairs:
        if refs[ei][0] == refs[ej][0]:
            continue
        delta = pts[ej]-pts[ei]; d = float(np.linalg.norm(delta))
        row = dict(endpoint_ids=[ei,ej], endpoints=[refs[ei],refs[ej]], chord=d)
        reason = None
        if d < cfg['min_gap_spacing']*spacing:
            reason = 'already_adjacent'
        cos_a = float(ts[ei]@unit(delta)); cos_b = float(ts[ej]@-unit(delta))
        row.update(tangent_cos_a=cos_a,tangent_cos_b=cos_b)
        if reason is None and min(cos_a,cos_b) < cfg['tangent_cos']:
            reason = 'G3_incompatible_tangents'
        if reason is None:
            curve = hermite(pts[ei],pts[ej],ts[ei],ts[ej],cfg['samples'],cfg['hermite_tension'])
            diff = np.diff(curve,axis=0); lengths = np.linalg.norm(diff,axis=1)
            tangent = diff/np.maximum(lengths[:,None],1e-12)
            turn = float(np.rad2deg(np.arccos(np.clip((tangent[1:]*tangent[:-1]).sum(1),-1,1))).sum())
            arc = float(lengths.sum()); dist = tree.query(curve)[0]/spacing
            support = float(np.mean(dist<=cfg['support_radius']))
            row.update(length_3d=arc,arc_ratio=arc/d,total_turn_deg=turn,
                       gaussian_supported_fraction=support,gaussian_distance_max=float(dist.max()),
                       gaussian_distance_mean=float(dist.mean()),gap_in_spacing=d/spacing)
            if arc/d > cfg['max_arc_ratio'] or turn > cfg['max_total_turn_deg']:
                reason = 'curvature_or_arclength'
            elif support < cfg['min_supported_fraction'] or dist.max() > cfg['max_support_distance']:
                reason = 'unsupported_3d_space'
        if reason is None:
            row['bridge_id'] = len(accepted)
            row['object_score'] = float(min(cos_a,cos_b)*support/(1+d/limit))
            accepted.append(dict(row,points=curve))
        row['reason'] = reason or 'object_accepted'
        audit.append(row)
    return accepted, audit, dict(spacing=spacing,extent=extent,max_gap=limit,
        endpoint_count=len(pts),tested_pairs=len(audit),accepted=len(accepted),
        reasons=dict(Counter(row['reason'] for row in audit)))


def choose(bridges, scores, visible_lengths, original_lengths, original_length_3d,
           max_bridges=20, fraction=.05):
    """Deterministic ranked selection; every fit-view budget and endpoint capacity.

    Zero visible cost cannot bypass the 3D length cap. Negative/nonfinite scores
    denote rejected hypotheses. This never consults human G1 annotations.
    """
    selected, used, audit = [], set(), []
    spent = np.zeros(len(original_lengths)); spent3d = 0.
    for i in sorted(range(len(bridges)),key=lambda i:(-scores[i],bridges[i]['bridge_id'])):
        b=bridges[i]; reason='accepted'
        if not np.isfinite(scores[i]) or scores[i] <= 0:
            reason='evidence_rejected'
        elif len(selected)>=max_bridges:
            reason='bridge_count_budget'
        elif any(e in used for e in b['endpoint_ids']):
            reason='endpoint_already_used'
        elif spent3d+b['length_3d'] > fraction*original_length_3d+1e-12:
            reason='object_length_budget'
        elif np.any(spent+visible_lengths[:,i] > fraction*np.asarray(original_lengths)+1e-9):
            reason='visible_length_budget'
        if reason=='accepted':
            selected.append(i); used.update(b['endpoint_ids'])
            spent+=visible_lengths[:,i]; spent3d+=b['length_3d']
        audit.append(dict(bridge_id=b['bridge_id'],reason=reason))
    return selected,dict(decisions=audit,added_visible_lengths=spent.tolist(),added_length_3d=spent3d)
