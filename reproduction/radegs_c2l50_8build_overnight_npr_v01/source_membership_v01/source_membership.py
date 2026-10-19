"""Frozen-source CPU-EWA sampled responsibility diagnostic (not native CUDA)."""
import numpy as np


def contributions(uv, z, cov, opacity, x, y):
    """Return every accepted original source index and its front-to-back alpha*T."""
    a, b, c = cov[:, 0, 0], cov[:, 0, 1], cov[:, 1, 1]
    det = a*c-b*b
    dx, dy = x-uv[:, 0], y-uv[:, 1]
    valid = (z > .2) & np.isfinite(z) & (opacity > 0) & np.isfinite(det) & (det > 1e-18)
    valid &= np.isfinite(dx) & np.isfinite(dy) & (np.abs(dx) <= 3*np.sqrt(np.maximum(a, 0))) & (np.abs(dy) <= 3*np.sqrt(np.maximum(c, 0)))
    idx = np.flatnonzero(valid)
    if not len(idx):
        return idx, np.empty(0, dtype=float)
    q = (c[idx]*dx[idx]**2-2*b[idx]*dx[idx]*dy[idx]+a[idx]*dy[idx]**2)/det[idx]
    idx = idx[q <= 9]
    q = q[q <= 9]
    if not len(idx):
        return idx, np.empty(0, dtype=float)
    order = np.argsort(z[idx], kind='stable')
    idx, q = idx[order], q[order]
    al = np.clip(opacity[idx]*np.exp(-q/2), 0, .999)
    t = 1.
    ids, weights = [], []
    for i, alpha in zip(idx, al):
        if t < 1e-5:
            break
        if alpha <= 0:
            continue
        ids.append(int(i))
        weights.append(t*alpha)
        t *= 1-alpha
    return np.asarray(ids, dtype=np.int32), np.asarray(weights, dtype=float)


def sample_pixels(labels, unknown, count, seed=0):
    """Stratify supported parts; inverse-frequency weights preserve full-mask prevalence."""
    rng = np.random.default_rng(seed)
    valid = (labels > 0) & ~unknown
    groups = [np.flatnonzero(valid & (labels == label)) for label in (1, 2, 3)]
    if any(len(g) == 0 for g in groups):
        raise ValueError('missing part: cannot run three-way pilot')
    count = min(int(count), int(valid.sum()))
    allocations = [min(len(g), count//3) for g in groups]
    for _ in range(count - sum(allocations)):
        candidates = [i for i in range(3) if allocations[i] < len(groups[i])]
        i = min(candidates, key=lambda j: allocations[j]/len(groups[j]))
        allocations[i] += 1
    out = []
    h, w = labels.shape
    for g, n in zip(groups, allocations):
        for idx in rng.choice(g, n, replace=False):
            y, x = divmod(int(idx), w)
            out.append((x, y, count*len(g)/(int(valid.sum())*n)))
    return out


def shuffled_within_strata(q, labels, seed):
    out=np.array(q,copy=True)
    rng=np.random.default_rng(seed)
    for label in np.unique(labels):
        indices=np.flatnonzero(labels==label)
        out[indices]=q[rng.permutation(indices)]
    return out


def winner_vote(ids, weights, sampling_weight):
    k=int(np.argmax(weights))
    return int(ids[k]), float(weights.sum()*sampling_weight)


def replay_rgb(ids, weights, all_colors, background):
    return (weights[:,None]*all_colors[ids]).sum(axis=0)+(1-weights.sum())*np.asarray(background)


def resolve_membership(score, exposure, distinct_views, min_exposure, min_fraction, min_views):
    out,reason=assign(score,exposure,min_exposure,min_fraction)
    reason[(exposure>0)&(exposure<min_exposure)]='low_mass'
    insufficient=(exposure>=min_exposure)&(distinct_views<min_views)
    out[insufficient]=0;reason[insufficient]='single_view'
    return out,reason


def conflicting_views(first, second, min_mass, min_fraction):
    mass1,mass2=first.sum(axis=1),second.sum(axis=1)
    p1=np.divide(first.max(axis=1),mass1,out=np.zeros_like(mass1),where=mass1>0)
    p2=np.divide(second.max(axis=1),mass2,out=np.zeros_like(mass2),where=mass2>0)
    return (mass1>=min_mass)&(mass2>=min_mass)&(p1>=min_fraction)&(p2>=min_fraction)&(first.argmax(axis=1)!=second.argmax(axis=1))


def aggregate(n, observations, classes):
    score = np.zeros((n, classes), dtype=float)
    exposure = np.zeros(n, dtype=float)
    for ids, w, q, sampling_weight in observations:
        if q is None:
            continue
        q = np.asarray(q, dtype=float)
        if q.shape != (classes,) or np.any(q < 0) or not np.isclose(q.sum(), 1):
            raise ValueError('invalid part probabilities')
        np.add.at(exposure, ids, w*sampling_weight)
        for j in range(classes):
            np.add.at(score[:, j], ids, w*sampling_weight*q[j])
    return score, exposure


def assign(score, exposure, min_exposure=.05, min_fraction=.8):
    result = np.zeros(len(exposure), dtype=np.uint8)
    reason = np.full(len(exposure), 'unobserved', dtype='<U20')
    enough = exposure >= min_exposure
    reason[enough] = 'mixed'
    fraction = np.divide(score.max(axis=1), exposure, out=np.zeros_like(exposure), where=exposure > 0)
    confident = enough & (fraction >= min_fraction)
    result[confident] = score.argmax(axis=1)[confident]+1
    reason[confident] = 'confident'
    return result, reason
