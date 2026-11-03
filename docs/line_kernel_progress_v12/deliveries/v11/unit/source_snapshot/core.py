"""Frozen target-only bundle collapse."""
import limits
import numpy as np

def collapse(asset, rows, p):
    rows = np.asarray(rows)
    if rows.ndim != 1 or rows.dtype.kind not in 'iu' or len(rows) == 0:
        raise ValueError('empty/noninteger target rows')
    if len(np.unique(rows)) != len(rows) or np.any(rows < 0) or np.any(rows >= len(asset['means'])):
        raise ValueError('duplicate or out-of-domain target rows')
    if not np.isfinite(p) or p <= 0:
        raise ValueError('invalid p')
    x = asset['means'][rows]
    old_cov = asset['covariance'][rows]
    if not np.isfinite(x).all() or not np.isfinite(old_cov).all():
        raise ValueError('nonfinite target geometry')
    if not np.allclose(old_cov, old_cov.transpose(0, 2, 1), rtol=1e-12, atol=1e-24):
        raise ValueError('asymmetric target covariance')
    old_eigenvalues = np.linalg.eigvalsh(old_cov)
    if np.any(old_eigenvalues <= 0):
        raise ValueError('nonpositive target covariance')
    center = x.mean(axis=0)
    centered = x-center
    eig, axes = np.linalg.eigh(centered.T @ centered / len(rows))
    if eig[-1]-eig[-2] <= 1e-12*max(eig[-1], p*p):
        raise ValueError('degenerate principal axis')
    a = axes[:, -1].copy()
    if a[np.argmax(np.abs(a))] < 0:
        a *= -1
    world_axis = np.eye(3)[np.argmin(np.abs(a))]
    e1 = world_axis-a*np.dot(a, world_axis)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    transverse = np.column_stack([e1, e2])
    s = centered @ a
    lo, hi = float(s.min()), float(s.max())
    if hi-lo <= 1e-8*p:
        raise ValueError('degenerate longitudinal extent')
    u = 2*(s-lo)/(hi-lo)-1
    basis = legendre(u)
    y = centered @ transverse / p
    coefficients = np.linalg.solve(basis.T@basis/len(rows)+np.diag([0., 0., .01, .01]), basis.T@y/len(rows))
    model = dict(center=center, axis=a, e1=e1, e2=e2, s_min=lo, s_max=hi, p=float(p),
                 coefficients=coefficients, principal_eigenvalues=eig, ridge=.01,
                 domain='original min/max axial projection; no extrapolated centers',
                 geometry_regularization_not_physical_reconstruction=True)
    means, tangent = evaluate_model(model, s)
    sigma_parallel = np.clip(np.sqrt(old_eigenvalues[:, -1]), .5*p, 1.5*p)
    sigma_perp = .15*p
    new_cov = sigma_perp**2*np.eye(3)[None]+(sigma_parallel**2-sigma_perp**2)[:, None, None]*tangent[:, :, None]*tangent[:, None, :]
    if not np.isfinite(means).all() or not np.isfinite(new_cov).all() or np.any(np.linalg.eigvalsh(new_cov) <= 0):
        raise ValueError('invalid derived geometry')
    position = {k: v.copy() for k, v in asset.items()}
    position['means'][rows] = means
    derived = {k: v.copy() for k, v in position.items()}
    derived['covariance'][rows] = new_cov
    displacement = means-x
    residual = np.linalg.norm(displacement, axis=1)
    axial_sigma = np.sqrt(np.einsum('i,nij,j->n', a, new_cov, a))
    return dict(position_only=position, derived=derived, model=model,
                delta=dict(row_index=rows.copy(), old_means=x.copy(), new_means=means,
                           old_covariance=old_cov.copy(), new_covariance=new_cov,
                           displacement=displacement, residual_to_fixed_curve=residual,
                           s=s, u=u, tangent=tangent, sigma_parallel=sigma_parallel,
                           sigma_perp=np.full(len(rows), sigma_perp),
                           old_covariance_eigenvalues=old_eigenvalues,
                           axial_3sigma_intervals=np.column_stack([s-3*axial_sigma, s+3*axial_sigma])),
                metrics=dict(displacement_quantiles_p=np.quantile(residual/p, [0,.5,.9,.95,.99,1]),
                             original_residual_rms_p=float(np.sqrt(np.mean((residual/p)**2))),
                             derived_residual_rms_p=0.,
                             residual_zero_by_construction_not_accuracy=True,
                             original_transverse_std_p=np.std(y, axis=0),
                             derived_transverse_std_p=np.std((means-center)@transverse/p, axis=0),
                             endpoints=evaluate_model(model, np.array([lo, hi]))[0],
                             axial_3sigma_range=[float(np.min(s-3*axial_sigma)), float(np.max(s+3*axial_sigma))],
                             gaussian_tails_are_unbounded=True))

def legendre(u):
    u = np.asarray(u, dtype=np.float64)
    return np.column_stack([np.ones_like(u), u, (3*u*u-1)/2, (5*u*u*u-3*u)/2])

def evaluate_model(model, s):
    s = np.asarray(s, dtype=np.float64)
    lo, hi = model['s_min'], model['s_max']
    if np.any(s < lo) or np.any(s > hi):
        raise ValueError('model evaluation outside frozen domain')
    u = 2*(s-lo)/(hi-lo)-1
    transverse = np.column_stack([model['e1'], model['e2']])
    b = np.asarray(model['coefficients'])
    q = np.asarray(model['center'])+s[:, None]*np.asarray(model['axis'])+model['p']*(legendre(u)@b)@transverse.T
    derivative = np.column_stack([np.zeros_like(u), np.ones_like(u), 3*u, (15*u*u-3)/2])
    tangent = np.asarray(model['axis'])+model['p']*2/(hi-lo)*(derivative@b)@transverse.T
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    return q, tangent
