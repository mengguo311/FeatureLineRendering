"""CPU diagnostic of covariance precision through Eq4/normal and its VJP.

This is not a CUDA test or a replacement for the sealed GPU probe. The
approximate inverse's derivative is the inverse identity used by C24; the
reference uses torch.double solve. All branch/fixture decisions are recorded.
"""
import json
from pathlib import Path
import numpy as np
import torch

from eigen_probe import OUT, legacy_eigh, rotation
from stable_eigen_candidate import geometry_eigh


def quantities(means, precision, rotation_camera):
    # Nonidentity rotation coverage without any FoV clamp in this CPU oracle.
    t = rotation_camera @ means
    x, y, z = t
    u, v = x / z, y / z
    ray = torch.stack([u, v, z * 0 + 1])
    p = rotation_camera @ precision @ rotation_camera.T
    q = p @ ray
    n = -q / torch.linalg.vector_norm(q)
    ij = torch.stack([1+v*v, -u*v, -u, -u*v, 1+u*u, -v,
                      z*0, z*0, z*0]).reshape(3, 3)
    plane = ij @ q / (q @ ray) * z / (1+u*u+v*v)
    # Keep fixed pixel displacement at the reference camera; this diagnostic
    # differentiates a fixed image coordinate, not a moving pixel.
    delta = torch.stack([1500*u+15.5-23, 1500*v+15.5-9])
    depth = z + (plane[:2] * delta / 1500).sum()
    return n, depth


def evaluate(a, precision, camera):
    packed = torch.tensor(a[[0, 0, 0, 1, 1, 2], [0, 1, 2, 1, 2, 2]] / 1e-4,
                          dtype=torch.float64, requires_grad=True)
    v = packed * 1e-4
    sigma = torch.stack([v[0],v[1],v[2],v[1],v[3],v[4],v[2],v[4],v[5]]).reshape(3,3)
    if precision is None:
        inv = torch.linalg.solve(sigma, torch.eye(3, dtype=torch.float64))
    else:
        p = torch.tensor(precision, dtype=torch.float64)
        # Exactly the value p, with the inverse-identity derivative. This is a
        # diagnostic of the C24 analytic assumption, never a training detach.
        inv = p - p @ (sigma - sigma.detach()) @ p
    c = torch.tensor(camera, dtype=torch.float64)
    m = (c.T @ torch.tensor([.01, -.008, 2.], dtype=torch.float64)).requires_grad_()
    normal, depth = quantities(m, inv, c)
    loss = normal @ torch.tensor([.2, -.4, .7], dtype=torch.float64) + .3 * depth
    gradients = torch.autograd.grad(loss, (m, packed))
    return dict(normal=normal.detach().numpy(), depth=float(depth),
                means_vjp=gradients[0].detach().numpy(),
                scaled_covariance_vjp=gradients[1].detach().numpy())


def main():
    fixtures = json.loads((OUT/'extreme_fixture_branch_audit.json').read_text())
    r = rotation(np.array([[.7, .2, -.3, .4]], np.float32))[0]
    fixtures.append(dict(iteration=None,index='fixed_CPU_RED',
                         matrix=(r @ np.diag([1e-7,4e-6,1e-5]) @ r.T).tolist()))
    camera = rotation(np.array([[.9, -.1, .2, .3]], np.float32))[0].astype(float)
    # Orthonormalize only the synthetic camera; this does not alter covariance.
    u, _, vh = np.linalg.svd(camera)
    cameras = {'identity':np.eye(3), 'rotated':u@vh}
    rows=[]
    for fixture in fixtures:
        a = np.asarray(fixture['matrix'], np.float32)
        true_eigenvalues=np.linalg.eigvalsh(a.astype(float))
        for name, c in cameras.items():
            reference = evaluate(a.astype(float), None, c)
            row=dict(iteration=fixture['iteration'],index=fixture['index'],
                     camera=name, true_eigenvalues=true_eigenvalues.tolist(), methods={})
            for mode, eig in [('original',legacy_eigh),('normalized_candidate',geometry_eigh)]:
                val,vec=eig(a)
                assert val.min()>1e-8 and true_eigenvalues.min()>1e-8
                p=(vec/val[:,None,:])@vec.transpose(0,2,1)
                actual=evaluate(a.astype(float),p[0],c)
                entry={'estimated_eigenvalues':val[0].tolist(),'well_conditioned_branch':True,
                       'values':{},'errors':{}}
                for key in reference:
                    expected=np.asarray(reference[key]);got=np.asarray(actual[key]);error=np.abs(got-expected)
                    entry['values'][key]={'actual':got.tolist(),'reference':expected.tolist()}
                    entry['errors'][key]={'max_absolute':float(error.max()),
                        'relative_l2':float(np.linalg.norm(error)/max(np.linalg.norm(expected),1e-30))}
                row['methods'][mode]=entry
            rows.append(row)
    result={'kind':'CPU inverse-identity VJP diagnostic, NOT CUDA validation',
            'torch_cuda_initialized':torch.cuda.is_initialized(), 'rows':rows}
    assert not result['torch_cuda_initialized']
    path=OUT/'geometry_precision_CPU_audit.json'
    path.write_text(json.dumps(result,indent=2)+'\n')
    for row in rows:
        print(json.dumps({key:row[key] for key in ['iteration','index','camera']} | {
            mode:entry['errors'] for mode,entry in row['methods'].items()}),flush=True)


if __name__=='__main__':main()
