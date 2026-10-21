"""Eligibility, provenance and display metrics. No generation or GT repair."""
import numpy as np
from scipy import ndimage

def headroom_status(eligible_boundary_length, crossing_length, evidence_valid):
    values = np.asarray([eligible_boundary_length, crossing_length], float)
    if not evidence_valid or not np.isfinite(values).all() or (values < 0).any():
        return 'UNKNOWN'
    if eligible_boundary_length == 0 or crossing_length == 0:
        return 'ZERO_HEADROOM'
    return 'ELIGIBLE'

def topology(mesh):
    """Face adjacency ONLY via identical indexed mesh edges; never proximity."""
    edges = {}
    for i, face in enumerate(mesh['faces']):
        for j in range(3):
            edge = tuple(sorted((int(face[j]), int(face[(j+1) % 3]))))
            edges.setdefault(edge, []).append(i)
    neighbors = [[] for _ in mesh['faces']]
    boundary = []
    nonmanifold = 0
    for edge, owners in edges.items():
        if len(owners) > 2: nonmanifold += 1
        if len(owners) == 2:
            a, b = owners
            neighbors[a].append(b); neighbors[b].append(a)
            if mesh['parts'][a] != mesh['parts'][b]: boundary.append(edge)
    seen, components = set(), []
    for start in range(len(neighbors)):
        if start in seen: continue
        queue, faces = [start], []
        seen.add(start)
        while queue:
            node = queue.pop(); faces.append(node)
            for other in neighbors[node]:
                if other not in seen: seen.add(other); queue.append(other)
        components.append(dict(faces=len(faces), parts=np.unique(mesh['parts'][faces]).tolist(),
                               area_world2=float(mesh['areas'][faces].sum())))
    length = sum(float(np.linalg.norm(mesh['vertices'][a]-mesh['vertices'][b])) for a,b in boundary)
    return dict(face_components=components, component_count=len(components),
                shared_part_boundary_edges=len(boundary), shared_part_boundary_length_world=length,
                nonmanifold_edges=nonmanifold, open_edges=sum(len(v)==1 for v in edges.values()),
                adjacency='identical indexed edge only; no weld, KNN or fabricated connection')

def curve_evidence(points, provenance):
    """An authored geometric ring is not automatically a semantic boundary."""
    p = np.asarray(points, float)
    valid = p.ndim == 2 and p.shape[1:] == (3,) and len(p) >= 2 and np.isfinite(p).all()
    valid = valid and float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum()) > 0
    if not valid or not provenance or not provenance.get('confirmed') or not provenance.get('source'):
        return 'UNKNOWN'
    return {'physical_profile_ring':'AUTHORED_STRUCTURE_ONLY',
            'shared_part_boundary':'CONFIRMED_BOUNDARY',
            'authored_edit_region':'ORACLE_EDIT_BOUNDARY'}.get(provenance.get('kind'), 'UNKNOWN')

def display_metrics(off_image, on_image, off_hatch, on_hatch, contours_off, contours_on,
                    ring_ink, labels, aa_band=2):
    """Quantified display intervention, not a perceptual quality/H2 score."""
    arrays = [off_image, on_image, off_hatch, on_hatch, contours_off, contours_on, ring_ink]
    if any(a.shape != labels.shape or not np.isfinite(a).all() for a in arrays):
        return dict(status='UNKNOWN', reason='missing/invalid raster evidence')
    delta = np.abs(on_image-off_image)
    # This exact compositing reference tests fixed downstream inputs and drift.
    expected = 1.-np.maximum(np.maximum(off_hatch, contours_off), ring_ink)
    # Supersample max is not the max of downsampled layers: float image must
    # therefore be supplied independently for exact equality (checked outside).
    # This field is descriptive, never used as a gate.
    layer_max_discrepancy = float(np.abs(expected-on_image).sum())
    label_edge = np.zeros(labels.shape, bool)
    label_edge[:-1] |= labels[:-1] != labels[1:]
    label_edge[1:] |= labels[:-1] != labels[1:]
    label_edge[:, :-1] |= labels[:, :-1] != labels[:, 1:]
    label_edge[:, 1:] |= labels[:, :-1] != labels[:, 1:]
    band = ndimage.distance_transform_edt(~label_edge) <= aa_band
    changed = delta > 1e-12
    ring_support = ring_ink > 0
    near_ring = ndimage.distance_transform_edt(~ring_support) <= 2 if ring_support.any() else np.zeros_like(band)
    unchanged_hatch = np.array_equal(off_hatch, on_hatch)
    unchanged_contours = np.array_equal(contours_off, contours_on)
    # Adding rings can only darken; any loss of ink detects deletion controls.
    erased_ink = float(np.maximum(on_image-off_image, 0).sum())
    outside_ring = float(delta[~ring_support].sum())
    operation = float(delta.sum())
    parts = {}
    for part in (1, 2, 3):
        mask = labels == part
        support = mask & (on_hatch > .1)
        spacing = ndimage.distance_transform_edt(~(on_hatch > .1))[mask]
        parts[str(part)] = dict(visible_area_pixels=int(mask.sum()), hatch_support_pixels=int(support.sum()),
                               hatch_support_fraction=float(support.sum()/max(mask.sum(), 1)),
                               hatch_ink_mass=float(on_hatch[mask].sum()),
                               off_total_ink=float((1-off_image)[mask].sum()),
                               on_total_ink=float((1-on_image)[mask].sum()),
                               distance_to_hatch_p50_px=float(np.median(spacing)) if len(spacing) else None,
                               distance_to_hatch_p95_px=float(np.quantile(spacing,.95)) if len(spacing) else None)
    passed = (operation > 0 and unchanged_hatch and unchanged_contours and erased_ink == 0
              and outside_ring == 0 and all(v['hatch_support_pixels'] > 0 for v in parts.values()))
    return dict(status='VALID_DISPLAY' if passed else 'ENGINEERING_INVALID',
                nonzero_operation_L1=operation, changed_pixels=int(changed.sum()),
                hatch_exact=unchanged_hatch, contours_exact=unchanged_contours,
                erased_ink=erased_ink, outside_ring_delta=outside_ring,
                far_background_delta=float(delta[(labels==0)&~band].sum()),
                aa_label_boundary_delta=float(delta[band].sum()),
                ring_ink_mass=float(ring_ink.sum()), visible_ring_pixels=int(ring_support.sum()),
                near_ring_pixels=int(near_ring.sum()),
                near_ring_hatch_pixels=int((near_ring & (on_hatch > .1)).sum()),
                hatch_ring_overlap_pixels=int((ring_support & (on_hatch > .1)).sum()),
                parts=parts, downsampled_max_discrepancy_descriptive=layer_max_discrepancy,
                crossing='UNIDENTIFIABLE_FOR_H2 when physical boundary support is zero',
                clutter_scope='2px ring-neighborhood hatch overlap proxy; not crossing events or preference')
