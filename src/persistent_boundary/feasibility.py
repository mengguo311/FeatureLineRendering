"""Conditional fixed-point ray consistency, not a claim about full curves."""
import numpy as np


def fit_fixed_point(cameras, pixels, tolerance_px):
    """Least-squares common point of calibrated rays; pixel tolerance is caller supplied."""
    if len(cameras) != len(pixels):
        raise ValueError('one pixel observation is required per camera')
    if not np.isfinite(tolerance_px) or tolerance_px < 0:
        raise ValueError('pixel tolerance must be finite and nonnegative')
    A = np.zeros((3, 3), dtype=np.float64)
    b = np.zeros(3, dtype=np.float64)
    for cam, uv in zip(cameras, pixels):
        K = np.asarray(cam.K, dtype=np.float64)
        c2w = np.linalg.inv(np.asarray(cam.w2c, dtype=np.float64))
        center = c2w[:3, 3]
        direction = c2w[:3, :3] @ np.linalg.solve(K, np.r_[uv, 1.])
        direction /= np.linalg.norm(direction)
        P = np.eye(3) - np.outer(direction, direction)
        A += P
        b += P @ center
    singular_values = np.linalg.svd(A, compute_uv=False)
    rank = int(np.linalg.matrix_rank(A))
    spectrum = [float(v) for v in singular_values]
    condition = float(singular_values[0] / singular_values[-1]) if rank == 3 else None
    if rank < 3:
        return {'xyz': None, 'residuals_px': None, 'depths': None,
                'rank': rank, 'singular_values': spectrum,
                'condition_number': condition,
                'feasible': False, 'status': 'underdetermined'}
    xyz = np.linalg.lstsq(A, b, rcond=None)[0]
    residuals, depths = [], []
    for cam, uv in zip(cameras, pixels):
        q = np.asarray(cam.w2c) @ np.r_[xyz, 1.]
        depths.append(float(q[2]))
        h = np.asarray(cam.K) @ q[:3]
        residuals.append(float(np.linalg.norm(h[:2] / h[2] - uv)))
    rank = int(np.linalg.matrix_rank(A))
    feasible = rank == 3 and min(depths) > 0 and max(residuals) <= tolerance_px
    status = 'behind_camera' if min(depths) <= 0 else ('feasible' if feasible else 'inconsistent')
    return {'xyz': xyz, 'residuals_px': residuals, 'depths': depths,
            'rank': rank, 'singular_values': spectrum, 'condition_number': condition,
            'feasible': feasible, 'status': status}
