"""Bounded refinement of existing model-derived geometry; no topology changes."""
import runtime
from runtime import js, sha, now, output_guard
from pathlib import Path
import argparse
import json
import time
import numpy as np
from scipy import sparse


def refine(vertices, faces, regions, config):
    original = np.asarray(vertices, dtype=float)
    faces = np.asarray(faces, dtype=np.int32)
    regions = np.asarray(regions, dtype=np.int32)
    if not np.isfinite(original).all() or original.ndim != 2 or original.shape[1] != 3:
        raise ValueError('finite 3D vertices required')
    cap = float(config['max_displacement'])
    iterations = int(config['iterations'])
    if not 0 < cap <= .05 or not 1 <= iterations <= 30:
        raise ValueError('bounded refinement requires cap (0,.05], 1..30 iterations')
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    unique, inverse, count = np.unique(edges, axis=0, return_inverse=True, return_counts=True)
    edge_regions = np.tile(regions, 3)
    rmin = np.full(len(unique), np.iinfo(regions.dtype).max); rmax = np.zeros(len(unique), dtype=int)
    np.minimum.at(rmin, inverse, edge_regions); np.maximum.at(rmax, inverse, edge_regions)
    pinned = np.zeros(len(original), bool)
    pinned[np.unique(unique[(count != 2) | (rmin != rmax)])] = True
    pinned[np.unique(faces[np.isin(regions, config['pinned_regions'])])] = True
    a, b = unique[:, 0], unique[:, 1]
    adjacency = sparse.csr_matrix((np.ones(2*len(a)), (np.r_[a, b], np.r_[b, a])),
                                  shape=(len(original), len(original)))
    degree = np.asarray(adjacency.sum(axis=1)).ravel()
    pinned |= degree == 0
    averaging = sparse.diags(1/np.maximum(degree, 1)) @ adjacency
    tri = original[faces]
    n0 = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
    area0 = np.linalg.norm(n0, axis=1)
    if (area0 <= 0).any():
        raise ValueError('degenerate source faces cannot be refined')
    current = original.copy(); rejected = 0
    for _ in range(iterations):
        for step in (config['positive_step'], config['negative_step']):
            proposed = current + step*(averaging @ current-current)
            displacement = proposed-original
            length = np.linalg.norm(displacement, axis=1)
            proposed = original + displacement*np.minimum(1, cap/np.maximum(length, 1e-30))[:, None]
            proposed[pinned] = original[pinned]
            # Restore only incident vertices to their previous valid position.
            # Recheck neighboring faces until all oriented-area constraints hold.
            for _guard in range(len(original)+1):
                tri = proposed[faces]
                n1 = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
                bad = (np.einsum('ij,ij->i', n0, n1) <= 0) | (np.linalg.norm(n1, axis=1) < .2*area0)
                if not bad.any():
                    break
                ids = np.unique(faces[bad]); rejected += len(ids)
                proposed[ids] = current[ids]
            else:
                raise RuntimeError('face guard did not converge')
            current = proposed
    displacement = np.linalg.norm(current-original, axis=1)
    info = dict(vertices=len(original), faces=len(faces), pinned_vertices=int(pinned.sum()),
                moved_vertices=int((displacement > 1e-12).sum()),
                displacement_max=float(displacement.max()),
                displacement_p50=float(np.median(displacement)),
                displacement_p95=float(np.quantile(displacement, .95)),
                face_guard_vertex_restorations=rejected,
                open_edges=int((count == 1).sum()), nonmanifold_edges=int((count > 2).sum()),
                region_boundary_edges=int((rmin != rmax).sum()), topology_unchanged=True,
                pinned_exact=bool(np.array_equal(current[pinned], original[pinned])),
                parameters=config)
    return current, info


def build(unit, source_mesh=None):
    unit = output_guard(unit)
    p = json.loads((unit/'PROTOCOL.json').read_text())
    frozen_source = Path(p['previous_unit'])/'assets/baseline/mesh.npz'
    source = frozen_source if source_mesh is None else Path(source_mesh)
    if sha(source) != p['inputs_sha256'][str(frozen_source)]:
        raise ValueError('source mesh changed after freeze')
    out = unit/'proxy'; out.mkdir(exist_ok=True)
    if (out/'mesh.npz').exists():
        raise FileExistsError('candidate already exists')
    t = time.monotonic()
    with np.load(source) as d:
        v, f, r = d['vertices'], d['faces'], d['face_regions']
    result, info = refine(v, f, r, p['refinement'])
    np.savez_compressed(out/'mesh.npz', vertices=result, faces=f, face_regions=r)
    info.update(utc=now(), seconds=time.monotonic()-t, source_mesh_sha256=sha(source),
                mesh_sha256=sha(out/'mesh.npz'), original_model_sha256=p['original']['sha256'],
                geometry_source=p['geometry'], limitation='bounded smoothing is not new surface evidence; no hole filling')
    js(out/'REFINEMENT.json', info)
    print(json.dumps(info), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--unit', required=True, type=Path)
    build(p.parse_args().unit)
