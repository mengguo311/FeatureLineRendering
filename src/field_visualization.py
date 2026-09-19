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
