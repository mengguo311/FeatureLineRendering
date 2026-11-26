"""Stage 1 & 2: 3DGS semantic pre-separation + 32-view 2D enclosed leaf region watershed detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt, maximum_filter
from scipy.spatial import cKDTree
from skimage.segmentation import watershed

from .data_io import CalibratedLeafView, GaussianCloud3D, PriorVectorGeometry

# Semantic label constants for non-leaf Gaussians
LABEL_POT_OR_SOIL = -1
LABEL_WOOD_STEM = -2
LABEL_UNASSIGNED_FOLIAGE = -3


@dataclass
class EnclosedLeaf2DViewMap:
    """Detected 2D enclosed leaf regions for a single calibrated view."""

    view_name: str
    cell_id_map: np.ndarray        # (H, W) int32: 0 = background/boundary/stem, 1..K = valid enclosed leaf cell
    cell_closure_score: np.ndarray # (K+1,) float32 in [0, 1], index 0 unused
    cell_area_px: np.ndarray       # (K+1,) int32
    boundary_wall: np.ndarray      # (H, W) bool composite leaf boundary wall
    num_valid_cells: int


def preclassify_3dgs_semantic_domains(
    cloud: GaussianCloud3D,
    priors: PriorVectorGeometry,
) -> tuple[np.ndarray, dict[str, int]]:
    """Partition all 284,835 Gaussians into POT (-1), WOOD_STEM (-2), and FOLIAGE_CANDIDATE (-3)."""
    n = len(cloud.means)
    labels = np.full(n, LABEL_UNASSIGNED_FOLIAGE, dtype=np.int32)

    xyz = cloud.means.astype(np.float64)
    rgb = cloud.rgb_dc.astype(np.float64)

    # 1. Ceramic Pot & Soil Base (below pot_h_max within pot outer radius)
    rel_pot = xyz - priors.pot_axis_origin[None, :]
    h_pot = rel_pot @ priors.pot_axis_dir
    r_pot = np.linalg.norm(rel_pot - h_pot[:, None] * priors.pot_axis_dir[None, :], axis=1)
    is_pot = (h_pot <= priors.pot_h_max + 0.004) & (r_pot <= 0.31)
    labels[is_pot] = LABEL_POT_OR_SOIL

    # 2. Woody Trunks, Stems & Petioles: inside v04 swept trunk tubes OR strong brown woody chromaticity
    rem_idx = np.where(~is_pot)[0]
    rem_xyz = xyz[rem_idx]
    rem_rgb = rgb[rem_idx]
    exg = 2.0 * rem_rgb[:, 1] - rem_rgb[:, 0] - rem_rgb[:, 2]
    g_minus_r = rem_rgb[:, 1] - rem_rgb[:, 0]

    is_wood_color = (g_minus_r < -0.018) & (exg < 0.05)
    is_in_tube = np.zeros(len(rem_idx), dtype=bool)
    if len(priors.trunk_points) > 0:
        t_tree = cKDTree(priors.trunk_points)
        d_t, nn_t = t_tree.query(rem_xyz, k=1, distance_upper_bound=0.03)
        ok_t = np.isfinite(d_t) & (nn_t < len(priors.trunk_radii))
        # Only claim kernel for trunk if inside 1.15*radius AND not bright green leaf crossing in front
        in_r = np.zeros(len(rem_idx), dtype=bool)
        in_r[ok_t] = d_t[ok_t] <= 1.15 * priors.trunk_radii[nn_t[ok_t]]
        is_in_tube = in_r & (g_minus_r < 0.035)

    wood_mask = is_wood_color | is_in_tube
    labels[rem_idx[wood_mask]] = LABEL_WOOD_STEM

    foliage_cnt = int(np.sum(labels == LABEL_UNASSIGNED_FOLIAGE))
    active_foliage_cnt = int(np.sum((labels == LABEL_UNASSIGNED_FOLIAGE) & (cloud.opacities >= 0.025)))
    stats = {
        "total_3dgs_kernels": n,
        "pot_and_soil_kernels": int(np.sum(labels == LABEL_POT_OR_SOIL)),
        "wood_stem_kernels": int(np.sum(labels == LABEL_WOOD_STEM)),
        "total_foliage_kernels": foliage_cnt,
        "active_foliage_kernels_opac_ge_0025": active_foliage_cnt,
        "faint_halo_foliage_kernels": foliage_cnt - active_foliage_cnt,
    }
    return labels, stats


def detect_2d_enclosed_leaves_for_view(
    view: CalibratedLeafView,
    priors: PriorVectorGeometry,
    min_area_px: int = 32,
    max_area_px: int = 4800,
    min_closure_ratio: float = 0.66,
) -> EnclosedLeaf2DViewMap:
    """Detect closed 2D leaflet interiors by fusing projected v04 3D rims + C2L50 edges + depth steps + watershed."""
    h, w = view.height, view.width
    p = priors.median_pixel_scale

    # 1. Identify green foliage foreground mask in 2D image (excluding sky, dark pot, and brown trunks)
    rgb = view.rgb
    exg_2d = 2.0 * rgb[..., 1] - rgb[..., 0] - rgb[..., 2]
    g_minus_r_2d = rgb[..., 1] - rgb[..., 0]

    # Project pot cap height & require genuine green foliage chromaticity (G > R + 0.016 and ExG > 0.055)
    # so sunlit beige/tan woody stems (where R >= G even though ExG > 0) and dark ceramic pot are 100% rejected!
    is_green_fg = (view.alpha > 0.50) & (view.front_depth > 0.2) & (exg_2d > 0.055) & (g_minus_r_2d > 0.016)
    # Also exclude bottom pot region by unprojecting pixel world-z!
    uu, vv = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    zc = view.front_depth
    xc = (uu - float(view.cx)) * zc / float(view.fx)
    yc = (vv - float(view.cy)) * zc / float(view.fy)
    R_c2w = view.c2w[:3, :3].astype(np.float32)
    t_c2w = view.c2w[:3, 3].astype(np.float32)
    world_z = xc * R_c2w[2, 0] + yc * R_c2w[2, 1] + zc * R_c2w[2, 2] + t_c2w[2]
    is_green_fg = is_green_fg & (world_z >= float(priors.pot_h_max))

    if int(is_green_fg.sum()) < min_area_px:
        return EnclosedLeaf2DViewMap(
            view_name=view.view_name,
            cell_id_map=np.zeros((h, w), dtype=np.int32),
            cell_closure_score=np.zeros(1, dtype=np.float32),
            cell_area_px=np.zeros(1, dtype=np.int32),
            boundary_wall=~is_green_fg,
            num_valid_cells=0,
        )

    # 2. Project visible 3D v04 leaf-rim points onto this view to close small 2D detector gaps!
    proj_v04_wall = np.zeros((h, w), dtype=np.uint8)
    if len(priors.rim_points) > 0:
        Xc_r = priors.rim_points @ view.w2c[:3, :3].T + view.w2c[:3, 3]
        zr = Xc_r[:, 2]
        ok = zr > 0.2
        if np.any(ok):
            ur = np.round(view.fx * (Xc_r[ok, 0] / zr[ok]) + view.cx).astype(np.int32)
            vr = np.round(view.fy * (Xc_r[ok, 1] / zr[ok]) + view.cy).astype(np.int32)
            zr_ok = zr[ok]
            in_b = (ur >= 0) & (ur < w) & (vr >= 0) & (vr < h)
            ur, vr, zr_ok = ur[in_b], vr[in_b], zr_ok[in_b]
            vis_r = zr_ok <= view.front_depth[vr, ur] + 4.0 * p
            proj_v04_wall[vr[vis_r], ur[vis_r]] = 1
            proj_v04_wall = cv2.dilate(proj_v04_wall, np.ones((2, 2), dtype=np.uint8))

    # 3. Composite physical boundary evidence (C2L50 skeleton/darkness + depth step + projected 3D rim + silhouette)
    c2l_edge = view.skeleton | (view.darkness > 0.20)
    depth_wall = view.depth_jump > 0.015
    hard_boundary = (~is_green_fg) | c2l_edge | depth_wall | (proj_v04_wall > 0)

    # Bridge tiny 1-2 px gaps along leaf margins via 3x3 morphological closing on boundary inside foliage
    edge_only = (c2l_edge | depth_wall | (proj_v04_wall > 0)).astype(np.uint8)
    closed_edge = cv2.morphologyEx(edge_only, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))) > 0
    wall = (~is_green_fg) | closed_edge

    # 4. Marker-controlled watershed on interior Euclidean distance transform!
    interior = is_green_fg & (~wall)
    if int(interior.sum()) < min_area_px:
        return EnclosedLeaf2DViewMap(
            view_name=view.view_name,
            cell_id_map=np.zeros((h, w), dtype=np.int32),
            cell_closure_score=np.zeros(1, dtype=np.float32),
            cell_area_px=np.zeros(1, dtype=np.int32),
            boundary_wall=wall,
            num_valid_cells=0,
        )

    dt = distance_transform_edt(interior).astype(np.float32)
    dt_smooth = cv2.GaussianBlur(dt, (5, 5), 0.9)

    # Local maxima of interior distance >= 2.2 px separated by at least 7 px (typical leaflet half-width 3..12 px)
    loc_max = (dt_smooth == maximum_filter(dt_smooth, size=7)) & (dt >= 2.2) & interior
    n_markers, markers = cv2.connectedComponents(loc_max.astype(np.uint8), connectivity=8)

    if n_markers <= 1:
        return EnclosedLeaf2DViewMap(
            view_name=view.view_name,
            cell_id_map=np.zeros((h, w), dtype=np.int32),
            cell_closure_score=np.zeros(1, dtype=np.float32),
            cell_area_px=np.zeros(1, dtype=np.int32),
            boundary_wall=wall,
            num_valid_cells=0,
        )

    # Elevation map for watershed: combine -dt_smooth with strong ridge energy (darkness + depth_jump + v04_wall)
    elevation = -dt_smooth + 4.0 * view.darkness + 25.0 * np.minimum(view.depth_jump, 0.1) + 2.5 * proj_v04_wall
    ws_labels = watershed(elevation, markers=markers, mask=is_green_fg)

    # 5. Validate each watershed cell for physical boundary closure & smooth single-surface depth!
    # True physical boundary support map (within 1.5 px of real C2L edge, depth step, v04 3D rim, or silhouette edge)
    real_phys_edge = (~is_green_fg) | c2l_edge | (view.depth_jump > 0.011) | (proj_v04_wall > 0)
    phys_edge_dil = cv2.dilate(real_phys_edge.astype(np.uint8), np.ones((3, 3), dtype=np.uint8)) > 0

    valid_map = np.zeros((h, w), dtype=np.int32)
    closures = [0.0]
    areas = [0]
    next_id = 1

    # Fast bounding-box slice evaluation per candidate region
    slices_info = cv2.connectedComponentsWithStats((ws_labels > 0).astype(np.uint8))
    del slices_info  # iterate directly via flat bincount & bounding boxes
    counts = np.bincount(ws_labels.ravel())
    cand_ids = np.where((counts >= min_area_px) & (counts <= max_area_px))[0]
    cand_ids = cand_ids[cand_ids > 0]

    # Precompute pixel coordinates per label via argsort for O(H*W) total complexity!
    flat_lbl = ws_labels.ravel()
    nz_idx = np.flatnonzero(flat_lbl > 0)
    nz_lbl = flat_lbl[nz_idx]
    order = np.argsort(nz_lbl)
    sorted_idx = nz_idx[order]
    sorted_lbl = nz_lbl[order]
    split_pos = np.searchsorted(sorted_lbl, cand_ids)
    split_end = np.searchsorted(sorted_lbl, cand_ids, side="right")

    for k_i, cid in enumerate(cand_ids):
        pix_flat = sorted_idx[split_pos[k_i] : split_end[k_i]]
        area = len(pix_flat)
        if area < min_area_px or area > max_area_px:
            continue
        rs = pix_flat // w
        cs = pix_flat % w

        # Check depth smoothness inside cell (single leaf blade shouldn't span huge depth discontinuity)
        z_vals = view.front_depth[rs, cs]
        q75, q25 = np.percentile(z_vals, [75.0, 25.0])
        if float(q75 - q25) > 0.045:
            continue

        # Local crop for 4-neighbor perimeter check
        r0, r1 = max(0, int(rs.min()) - 1), min(h, int(rs.max()) + 2)
        c0, c1 = max(0, int(cs.min()) - 1), min(w, int(cs.max()) + 2)
        sub_m = (ws_labels[r0:r1, c0:c1] == cid).astype(np.uint8)
        eroded = cv2.erode(sub_m, np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.uint8))
        perim = (sub_m > 0) & (eroded == 0)
        n_perim = int(perim.sum())
        if n_perim < 8:
            continue

        closure = float(np.mean(phys_edge_dil[r0:r1, c0:c1][perim]))
        if closure < min_closure_ratio:
            continue

        valid_map[rs, cs] = next_id
        closures.append(closure)
        areas.append(area)
        next_id += 1

    return EnclosedLeaf2DViewMap(
        view_name=view.view_name,
        cell_id_map=valid_map,
        cell_closure_score=np.array(closures, dtype=np.float32),
        cell_area_px=np.array(areas, dtype=np.int32),
        boundary_wall=wall,
        num_valid_cells=next_id - 1,
    )
