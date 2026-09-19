"""Diagnostics for geometric fields implicit in a vanilla 3DGS posterior.

None of the quantities in this module is a ground-truth surface normal or SDF.
They are explicitly labelled posterior proxies.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree


def sigmoid(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    return np.where(x >= 0, 1.0 / (1.0 + np.exp(-x)), np.exp(x) / (1.0 + np.exp(x)))


def quaternion_to_matrix(q: np.ndarray) -> np.ndarray:
    """Convert Graphdeco quaternions in (w,x,y,z) order to rotations."""
    q = np.asarray(q, dtype=np.float64)
    q = q / np.maximum(np.linalg.norm(q, axis=-1, keepdims=True), 1e-15)
    w, x, y, z = np.moveaxis(q, -1, 0)
    out = np.empty(q.shape[:-1] + (3, 3), dtype=np.float64)
    out[..., 0, 0] = 1 - 2 * (y*y + z*z)
    out[..., 0, 1] = 2 * (x*y - z*w)
    out[..., 0, 2] = 2 * (x*z + y*w)
    out[..., 1, 0] = 2 * (x*y + z*w)
    out[..., 1, 1] = 1 - 2 * (x*x + z*z)
    out[..., 1, 2] = 2 * (y*z - x*w)
    out[..., 2, 0] = 2 * (x*z - y*w)
    out[..., 2, 1] = 2 * (y*z + x*w)
    out[..., 2, 2] = 1 - 2 * (x*x + y*y)
    return out


def gaussian_candidate_normals(log_scales: np.ndarray, quaternions: np.ndarray):
    """Return smallest covariance axis (axial candidate normal) and linear scales."""
    scales = np.exp(np.asarray(log_scales, dtype=np.float64))
    rotations = quaternion_to_matrix(quaternions)
    smallest = np.argmin(scales, axis=1)
    normals = rotations[np.arange(len(rotations)), :, smallest]
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-15)
    return normals, scales


def covariance_matrices(log_scales: np.ndarray, quaternions: np.ndarray) -> np.ndarray:
    scales = np.exp(np.asarray(log_scales, dtype=np.float64))
    r = quaternion_to_matrix(quaternions)
    return np.einsum('nij,nj,nkj->nik', r, scales * scales, r)


def axial_rgb(normals: np.ndarray) -> np.ndarray:
    """Sign-invariant XYZ orientation color; X=red, Y=green, Z=blue."""
    n = np.asarray(normals, dtype=np.float64)
    n = n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-15)
    return np.abs(n)


def local_surface_metrics(points: np.ndarray, candidate_normals: np.ndarray,
                          query_indices: np.ndarray, k: int = 24):
    """Compute local center-cloud PCA diagnostics for selected Gaussians.

    Planarity uses descending local covariance eigenvalues:
    (lambda_2-lambda_3)/lambda_1. Axis agreement is axial |dot|.
    """
    points = np.asarray(points, dtype=np.float64)
    candidate_normals = np.asarray(candidate_normals, dtype=np.float64)
    query_indices = np.asarray(query_indices, dtype=np.int64)
    kk = min(max(3, int(k)), len(points))
    tree = cKDTree(points)
    distances, nn = tree.query(points[query_indices], k=kk, workers=-1)
    neigh = points[nn]
    centered = neigh - neigh.mean(axis=1, keepdims=True)
    cov = np.einsum('nki,nkj->nij', centered, centered) / max(kk - 1, 1)
    vals, vecs = np.linalg.eigh(cov)  # ascending
    local_n = vecs[:, :, 0]
    denom = np.maximum(vals[:, 2], 1e-20)
    linearity = np.clip((vals[:, 2] - vals[:, 1]) / denom, 0, 1)
    planarity = np.clip((vals[:, 1] - vals[:, 0]) / denom, 0, 1)
    scattering = np.clip(vals[:, 0] / denom, 0, 1)
    agreement = np.abs(np.einsum('ni,ni->n', local_n, candidate_normals[query_indices]))
    spacing = np.median(distances[:, 1:], axis=1)
    return {
        'local_normal': local_n,
        'local_eigenvalues': vals,
        'linearity': linearity,
        'planarity': planarity,
        'scattering': scattering,
        'axis_agreement': agreement,
        'neighbor_spacing': spacing,
    }


def flattening_score(scales: np.ndarray) -> np.ndarray:
    """Scale-ratio proxy: 0 spherical, approaches 1 for a very flat Gaussian."""
    s = np.sort(np.asarray(scales, dtype=np.float64), axis=1)
    return np.clip(1.0 - s[:, 0] / np.maximum(s[:, 1], 1e-20), 0, 1)


def evaluate_gaussian_slice(means: np.ndarray, covariances: np.ndarray,
                            weights: np.ndarray, origin: np.ndarray,
                            plane_basis: np.ndarray, u: np.ndarray, v: np.ndarray,
                            chunk: int = 128) -> np.ndarray:
    """Evaluate a 3D Gaussian-mixture peak-opacity proxy on a 2D plane."""
    means = np.asarray(means, dtype=np.float64)
    covariances = np.asarray(covariances, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    origin = np.asarray(origin, dtype=np.float64)
    basis = np.asarray(plane_basis, dtype=np.float64)
    uu, vv = np.meshgrid(u, v)
    grid = origin[None, None, :] + uu[..., None] * basis[:, 0] + vv[..., None] * basis[:, 1]
    flat = grid.reshape(-1, 3)
    out = np.zeros(len(flat), dtype=np.float64)
    for start in range(0, len(means), chunk):
        m = means[start:start+chunk]
        c = covariances[start:start+chunk]
        w = weights[start:start+chunk]
        inv = np.linalg.pinv(c, rcond=1e-10)
        d = flat[:, None, :] - m[None, :, :]
        mahal = np.einsum('gni,nij,gnj->gn', d, inv, d, optimize=True)
        out += np.sum(w[None, :] * np.exp(-0.5 * np.minimum(mahal, 80.0)), axis=1)
    return out.reshape(len(v), len(u))


def weighted_quantiles(values, weights, quantiles):
    """Inverse weighted empirical CDF (leftmost value at each probability).

    Zero weights are ignored; stable sorting makes ties deterministic.
    """
    values = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    quantiles = np.asarray(quantiles, dtype=np.float64)
    if (values.ndim != 1 or weights.shape != values.shape or
            not np.all(np.isfinite(values)) or not np.all(np.isfinite(weights)) or
            np.any(weights < 0) or weights.sum() <= 0 or
            not np.all(np.isfinite(quantiles)) or np.any((quantiles < 0) | (quantiles > 1))):
        raise ValueError('finite values, nonnegative nonzero weights and probabilities in [0,1] required')
    indices = np.flatnonzero(weights > 0)
    indices = indices[np.argsort(values[indices], kind='stable')]
    cdf = np.cumsum(weights[indices]); cdf /= cdf[-1]
    return values[indices[np.minimum(np.searchsorted(cdf, quantiles, side='left'), len(indices)-1)]]


def density_pca_frame(points, weights):
    """Opacity-weighted global center PCA; canonical signs and right handed frame.

    All centers participate. Robustness is applied separately to plane offsets
    and plot bounds via weighted quantiles, not to this covariance.
    """
    points = np.asarray(points, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if (points.ndim != 2 or points.shape[1] != 3 or weights.shape != (len(points),) or
            not np.all(np.isfinite(points)) or not np.all(np.isfinite(weights)) or
            np.any(weights < 0) or weights.sum() <= 0):
        raise ValueError('finite Nx3 centers and nonnegative nonzero weights required')
    center = np.average(points, axis=0, weights=weights)
    delta = points - center
    _, basis = np.linalg.eigh((delta.T * weights) @ delta / weights.sum())
    basis = basis[:, ::-1].copy()
    for col in range(2):
        if basis[np.argmax(np.abs(basis[:, col])), col] < 0:
            basis[:, col] *= -1
    basis[:, 2] = np.cross(basis[:, 0], basis[:, 1])
    return center, basis, delta @ basis


def gaussian_density_contributions(points, means, log_scales, quaternions, opacity):
    """Return point-by-kernel occupancy and determinant-normalized PDF terms.

    Direct scale-space whitening preserves extremely thin learned axes. There
    is no covariance pseudoinverse, scale clipping or artificial exponent floor.
    PDF weights are alpha, NOT alpha/sum(alpha); its whole-space integral is
    sum(alpha). Units are inverse scene-coordinate volume, not physical units.
    This reference evaluator is intended for small batches of query points.
    """
    delta = np.asarray(points, dtype=np.float64)[:, None, :] - np.asarray(means)[None, :, :]
    logs = np.asarray(log_scales, dtype=np.float64)
    rotation = quaternion_to_matrix(quaternions)
    local = np.einsum('pni,nij->pnj', delta, rotation) * np.exp(-logs)[None, :, :]
    mahal = np.sum(local * local, axis=-1)
    occ = np.asarray(opacity, dtype=np.float64)[None, :] * np.exp(-.5 * mahal)
    return occ, occ * np.exp(-logs.sum(axis=1))[None, :] / (2*np.pi)**1.5


def evaluate_density_slice(means, log_scales, quaternions, opacity, origin,
                           plane_basis, u, v, radius=12.0):
    """Point-sample both posterior proxies on a plane, with explicit tail cutoff.

    All input kernels are considered in original index order (no top-N cap).
    A kernel is culled only if its radius-R Mahalanobis ellipsoid misses the
    plane or its conditional bounding rectangle misses the grid. Individual
    samples outside the ellipsoid are zero. Returned absolute tail bounds are
    exp(-R^2/2) times the sum of each field's peak amplitudes, valid at every
    query in exact arithmetic; floating-point roundoff is not included.

    Conditional bounding boxes use a projected square-root covariance factor
    rather than subtracting nearly equal covariance matrices. The fields are
    point samples, not pixel averages; thin kernels can fall between samples.
    """
    means = np.asarray(means, dtype=np.float64)
    logs = np.asarray(log_scales, dtype=np.float64)
    q = np.asarray(quaternions, dtype=np.float64)
    alpha = np.asarray(opacity, dtype=np.float64)
    origin = np.asarray(origin, dtype=np.float64)
    basis = np.asarray(plane_basis, dtype=np.float64)
    u = np.asarray(u, dtype=np.float64); v = np.asarray(v, dtype=np.float64)
    if (means.shape != (len(alpha), 3) or logs.shape != means.shape or q.shape != (len(alpha), 4)
            or origin.shape != (3,) or basis.shape != (3, 2)
            or not all(np.all(np.isfinite(a)) for a in (means, logs, q, alpha, origin, basis, u, v))
            or np.any((alpha < 0) | (alpha > 1)) or np.any(np.linalg.norm(q, axis=1) <= 1e-15)
            or not np.isfinite(radius) or radius <= 0
            or len(u) < 2 or len(v) < 2 or np.any(np.diff(u) <= 0) or np.any(np.diff(v) <= 0)
            or not np.allclose(basis.T @ basis, np.eye(2), atol=1e-12, rtol=0)):
        raise ValueError('valid Gaussian parameters, orthonormal plane, increasing grids and positive radius required')
    scales = np.exp(logs)
    rotation = quaternion_to_matrix(q)
    factor = rotation * scales[:, None, :]
    normal = np.cross(basis[:, 0], basis[:, 1])
    normal_factor = np.einsum('i,nij->nj', normal, factor)
    sigma_n = np.linalg.norm(normal_factor, axis=1)
    signed = (means - origin) @ normal
    plane_distance_sq = (signed / sigma_n)**2
    plane_ids = np.flatnonzero(plane_distance_sq <= radius**2)
    unit = normal_factor / sigma_n[:, None]
    # Closest point on the plane in the kernel's Mahalanobis metric.
    conditional_center = means - np.einsum('nij,nj->ni', factor, unit) * (signed/sigma_n)[:, None]
    xy = (conditional_center - origin) @ basis
    projected = np.einsum('ia,nij->naj', basis, factor)
    projected -= np.einsum('naj,nj->na', projected, unit)[:, :, None] * unit[:, None, :]
    halfwidth = np.sqrt(np.maximum(radius**2 - plane_distance_sq, 0))[:, None] * np.linalg.norm(projected, axis=2)
    # Round outward to retain samples lying on the truncation boundary.
    pad = 64*np.finfo(np.float64).eps * (1 + np.abs(xy) + halfwidth)
    lo = xy - halfwidth - pad; hi = xy + halfwidth + pad
    x0 = np.searchsorted(u, lo[:, 0], side='left'); x1 = np.searchsorted(u, hi[:, 0], side='right')
    y0 = np.searchsorted(v, lo[:, 1], side='left'); y1 = np.searchsorted(v, hi[:, 1], side='right')
    grid_ids = plane_ids[(x1[plane_ids] > x0[plane_ids]) & (y1[plane_ids] > y0[plane_ids])]
    occ = np.zeros((len(v), len(u))); pdf = np.zeros_like(occ)
    normalizer = np.exp(-logs.sum(axis=1)) / (2*np.pi)**1.5
    sample_sums = np.zeros(len(alpha)); hit_counts = np.zeros(len(alpha), dtype=np.int64)
    inverse_factor = rotation / scales[:, None, :]
    du = np.einsum('i,nij->nj', basis[:, 0], inverse_factor)
    dv = np.einsum('i,nij->nj', basis[:, 1], inverse_factor)
    base = np.einsum('ni,nij->nj', origin - means, inverse_factor)
    for i in grid_ids:
        # Compute in the original kernel frame, preserving all learned scales.
        local = (base[i] + u[x0[i]:x1[i]][None, :, None]*du[i]
                 + v[y0[i]:y1[i]][:, None, None]*dv[i])
        mahal = np.einsum('...j,...j->...', local, local)
        inside = mahal <= radius**2
        values = alpha[i] * np.exp(-.5*mahal) * inside
        occ[y0[i]:y1[i], x0[i]:x1[i]] += values
        pdf[y0[i]:y1[i], x0[i]:x1[i]] += values * normalizer[i]
        sample_sums[i] = values.sum()
        hit_counts[i] = np.count_nonzero(inside)
    return {
        'occupancy': occ, 'pdf': pdf,
        'plane_indices': plane_ids, 'grid_indices': grid_ids,
        'sample_sums_occupancy': sample_sums, 'sample_sums_pdf': sample_sums * normalizer,
        'hit_counts': hit_counts,
        'tail_bounds': {'occupancy': float(np.exp(-.5*radius**2)*alpha.sum()),
                        'pdf': float(np.exp(-.5*radius**2)*np.sum(alpha*normalizer))},
    }
