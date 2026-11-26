"""Phase 3 (v03): M1+M2 Per-Leaf Gaussian Kernel Substrate, 6 Artistic Style Presets & Mixed-Leaf Plant Composer.

Drops M3 texel subdivision to keep a compact, high-purity M1+M2 per-leaf Gaussian kernel model (~297k kernels,
472 discrete 3D leaf kernel sets). Because every leaf's constituent 3DGS kernels are cleanly isolated, each leaf
can be styled independently in color, opacity, AND 3D Gaussian scale/shape — enabling multi-style leaves to
coexist seamlessly on the exact same 3D plant model!
"""

from __future__ import annotations

import colorsys
import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.spatial import cKDTree

from .data_io import GaussianCloud3D, PriorVectorGeometry
from .kernel_partitioner import LeafInstance3D
from .leaf_refinement_v02 import (
    apply_m1_opacity_sharpening,
    apply_m2_straddling_kernel_splitting,
    build_cloud_from_arrays,
    build_polar_envelopes,
    compute_kernel_leaf_polar_coords,
)
from .multiview_leaf_cells import LABEL_POT_OR_SOIL, LABEL_WOOD_STEM

PRESET_ORDER: tuple[str, ...] = (
    "ghibli_gouache",
    "sumie_ink_wash",
    "ukiyoe_papercut",
    "pointillist_stipple",
    "sakura_watercolor",
    "cyanotype_celadon",
)

PRESET_TITLES: dict[str, str] = {
    "ghibli_gouache": "Ghibli Gouache",
    "sumie_ink_wash": "Sumi-e Ink Wash",
    "ukiyoe_papercut": "Ukiyo-e Cutout",
    "pointillist_stipple": "3D Pointillist",
    "sakura_watercolor": "Sakura Pastel",
    "cyanotype_celadon": "Cyanotype Glaze",
}


@dataclass
class LeafKernelSubstrateM12:
    """Canonical M1+M2 per-leaf 3DGS Gaussian kernel substrate (no M3 texel subdivision)."""

    cloud: GaussianCloud3D              # M2-split + M1-sharpened 3DGS cloud (~297k kernels)
    raw_m2_opacities: np.ndarray        # Pre-M1 opacities on the M2 cloud (allows soft-wash presets like Sumi-e)
    kernel_labels: np.ndarray           # (N,) int32: -1=POT, -2=WOOD_STEM, 0..L-1=discrete leaf_id
    leaf_instances: list[LeafInstance3D]
    s_01: np.ndarray                    # (N,) float32 anatomical base (0) -> tip (1) per kernel
    t_norm: np.ndarray                  # (N,) float32 lateral blade coord [-1.5, 1.5]
    rho: np.ndarray                     # (N,) float32 polar contour fraction (<1 interior, ~1 margin)
    build_stats: dict[str, Any]


def build_m1_m2_leaf_substrate(
    source_cloud: GaussianCloud3D,
    base_labels: np.ndarray,
    base_leaves: list[LeafInstance3D],
    priors: PriorVectorGeometry,
) -> LeafKernelSubstrateM12:
    """Build the clean M1+M2 per-leaf Gaussian kernel substrate (M2 seam split -> M1 Beer-Lambert sharpening)."""
    c_m2, lbl_m2, leaves_m2, st_m2 = apply_m2_straddling_kernel_splitting(
        source_cloud, base_labels, base_leaves, priors, num_passes=2, min_split_px=1.65
    )
    raw_op_m2 = c_m2.opacities.copy()
    c_m12, st_m1 = apply_m1_opacity_sharpening(
        c_m2, lbl_m2, leaves_m2, core_gamma_outer=4.6, core_gamma_mid=3.5, halo_thresh=0.024
    )
    env = build_polar_envelopes(leaves_m2)
    _, s_01, t_norm, rho, _ = compute_kernel_leaf_polar_coords(c_m12.means, lbl_m2, env)

    return LeafKernelSubstrateM12(
        cloud=c_m12,
        raw_m2_opacities=raw_op_m2,
        kernel_labels=lbl_m2,
        leaf_instances=leaves_m2,
        s_01=s_01,
        t_norm=t_norm,
        rho=rho,
        build_stats={"m2_seam_split": st_m2, "m1_opacity_sharp": st_m1},
    )


def _style_pot_and_wood(
    sub: LeafKernelSubstrateM12,
    trunk_theme: str = "natural_warm",
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Initialize base colors, opacities, and scales with harmonious pot & wooden trunk styling."""
    rgb = sub.cloud.rgb_dc.copy()
    op = sub.cloud.opacities.copy()
    sc = sub.cloud.scales.copy()

    lum = (0.299 * rgb[:, 0] + 0.587 * rgb[:, 1] + 0.114 * rgb[:, 2])[:, None]
    pot_m = sub.kernel_labels == LABEL_POT_OR_SOIL
    wood_m = sub.kernel_labels == LABEL_WOOD_STEM

    if trunk_theme == "sumie_monochrome":
        rgb[pot_m] = np.clip(0.10 + 0.42 * lum[pot_m], 0.0, 1.0)
        rgb[wood_m] = np.clip(np.array([0.24, 0.22, 0.20], dtype=np.float32) * (0.55 + 0.85 * lum[wood_m]), 0.0, 1.0)
    elif trunk_theme == "cyanotype":
        rgb[pot_m] = np.clip(np.array([0.09, 0.18, 0.34], dtype=np.float32) * (0.65 + 0.80 * lum[pot_m]), 0.0, 1.0)
        rgb[wood_m] = np.clip(np.array([0.16, 0.30, 0.50], dtype=np.float32) * (0.60 + 0.85 * lum[wood_m]), 0.0, 1.0)
    else:
        # Crisp cel-shaded ceramic pot & warm bark wood stems
        cel_w = np.where(lum > 0.45, 1.08, 0.78).astype(np.float32)
        rgb[pot_m] = np.clip((0.15 + 0.68 * rgb[pot_m]) * cel_w[pot_m], 0.0, 1.0)
        rgb[wood_m] = np.clip(
            np.array([0.45, 0.34, 0.23], dtype=np.float32) * (0.62 + 0.72 * lum[wood_m]), 0.0, 1.0
        )
    return rgb, op, sc


def _apply_preset_to_leaf_subset(
    preset_name: str,
    k_idx: np.ndarray,
    sub: LeafKernelSubstrateM12,
    z_lo: float,
    z_hi: float,
    leaf_ctr_z_lut: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute stylized (rgb, opacity, scales) for a subset of foliage kernel indices k_idx under preset_name."""
    if len(k_idx) == 0:
        return (
            np.zeros((0, 3), dtype=np.float32),
            np.zeros((0,), dtype=np.float32),
            np.zeros((0, 3), dtype=np.float32),
        )

    lids = sub.kernel_labels[k_idx]
    s = sub.s_01[k_idx]
    rho = sub.rho[k_idx]
    base_rgb = sub.cloud.rgb_dc[k_idx]
    lum = 0.299 * base_rgb[:, 0] + 0.587 * base_rgb[:, 1] + 0.114 * base_rgb[:, 2]
    op_m1 = sub.cloud.opacities[k_idx].copy()
    op_raw = sub.raw_m2_opacities[k_idx].copy()
    sc = sub.cloud.scales[k_idx].copy()

    sun_leaf = np.clip((leaf_ctr_z_lut[lids] - z_lo) / max(z_hi - z_lo, 1e-4), 0.0, 1.0).astype(np.float32)
    leaf_hash = (((lids.astype(np.int64) * 1103515245 + 12345) & 0x7FFFFFFF) / float(0x7FFFFFFF)).astype(np.float32)
    kern_hash = (((k_idx.astype(np.int64) * 2654435761) & 0x7FFFFFFF) / float(0x7FFFFFFF)).astype(np.float32)

    if preset_name == "ghibli_gouache":
        # Lush Studio Ghibli hand-painted gouache: cool viridian-teal shadows -> warm sunlit meadow-emerald tips
        c_shadow = np.array([0.09, 0.38, 0.30], dtype=np.float32)
        c_mid = np.array([0.22, 0.63, 0.28], dtype=np.float32)
        c_sun = np.array([0.66, 0.86, 0.25], dtype=np.float32)
        warm = np.clip(0.55 * sun_leaf + 0.30 * s + 0.15 * leaf_hash, 0.0, 1.0)[:, None]
        col = np.where(warm < 0.5, (1.0 - 2.0 * warm) * c_shadow + 2.0 * warm * c_mid, (2.0 - 2.0 * warm) * c_mid + (2.0 * warm - 1.0) * c_sun)
        # 3-step gouache cel shading + subtle dark forest rim for overlapping leaf separation
        cel = np.where(lum > 0.50, 1.08, np.where(lum > 0.35, 0.93, 0.75)).astype(np.float32)[:, None]
        rim = np.clip((rho - 0.85) / 0.14, 0.0, 1.0)[:, None]
        col = col * cel * (1.0 - 0.32 * rim)
        # Slightly fuller painterly brush overlap on in-plane axes
        max_ax = np.argmax(sc, axis=1)
        sc[np.arange(len(k_idx)), max_ax] *= 1.06
        return np.clip(col, 0.0, 1.0).astype(np.float32), op_m1, sc

    if preset_name == "sumie_ink_wash":
        # Traditional Chinese Sumi-e Xuan-paper ink wash (Jiao / Nong / Zhong / Dan / Qing 5-ink tonalities)
        # Outer margins & shaded leaf bases hold concentrated dark charcoal ink; sunlit leaf bellies breathe pale wash!
        ink_density = np.clip(
            0.35 * (1.0 - sun_leaf) + 0.35 * (1.0 - lum) + 0.45 * np.clip((rho - 0.76) / 0.22, 0.0, 1.0) + 0.18 * (1.0 - s),
            0.0,
            1.0,
        )
        # Quantize gently toward Sumi-e tonal washes on warm Xuan rice-paper tint
        gray = 0.84 - 0.75 * (ink_density ** 1.15)
        col = np.stack([gray * 0.98, gray * 0.99, gray * 0.96], axis=-1)
        # Genuine Xuan-paper ink translucency in pale belly, concentrated opaque ink along leaf rim!
        is_faint = op_raw < 0.022
        gamma_ink = 1.8 + 3.2 * ink_density
        op_ink = np.where(is_faint, op_raw * 0.05, 1.0 - np.power(np.clip(1.0 - op_raw, 1e-5, 1.0), gamma_ink))
        return np.clip(col, 0.0, 1.0).astype(np.float32), np.clip(op_ink, 1e-4, 0.99).astype(np.float32), sc

    if preset_name == "ukiyoe_papercut":
        # Flat graphic Ukiyo-e woodblock / paper-cutout: crisp vermilion, mineral gold, and Prussian pine per leaf!
        band_sel = (0.60 * sun_leaf + 0.40 * leaf_hash)
        c_verm = np.array([0.87, 0.29, 0.17], dtype=np.float32)
        c_gold = np.array([0.93, 0.69, 0.18], dtype=np.float32)
        c_pine = np.array([0.14, 0.46, 0.42], dtype=np.float32)
        col = np.where(
            (band_sel > 0.64)[:, None],
            c_verm[None, :],
            np.where((band_sel > 0.34)[:, None], c_gold[None, :], c_pine[None, :]),
        )
        # Strict 2-tone posterized woodblock print block + crisp dark indigo-black keyline rim!
        two_tone = np.where(s > 0.55, 1.05, 0.91).astype(np.float32)[:, None]
        keyline = (rho > 0.86).astype(np.float32)[:, None]
        c_key = np.array([0.12, 0.11, 0.14], dtype=np.float32)[None, :]
        col = np.clip(col * two_tone, 0.0, 1.0) * (1.0 - 0.72 * keyline) + c_key * (0.72 * keyline)
        # Ultra-opaque matte paper-cutout sheet
        op_cut = np.where(op_raw < 0.024, op_raw * 0.04, 1.0 - np.power(np.clip(1.0 - op_raw, 1e-5, 1.0), 6.2))
        return np.clip(col, 0.0, 1.0).astype(np.float32), np.clip(op_cut, 1e-4, 0.995).astype(np.float32), sc

    if preset_name == "pointillist_stipple":
        # Neo-Impressionist 3D Pointillism (Seurat optical mixing): shrinks 3DGS kernel scales into crisp pigment dots!
        # Primary viridian-turquoise dots juxtaposed with complementary cadmium-gold & violet accent dots inside each leaf!
        c_viridian = np.array([0.10, 0.70, 0.48], dtype=np.float32)
        c_cadmium = np.array([0.97, 0.80, 0.16], dtype=np.float32)
        c_lavender = np.array([0.52, 0.36, 0.86], dtype=np.float32)
        c_coral = np.array([0.95, 0.42, 0.34], dtype=np.float32)

        # Optical dot selection per Gaussian kernel
        col = np.where(
            (kern_hash < 0.52)[:, None],
            c_viridian[None, :],
            np.where(
                (kern_hash < 0.80)[:, None],
                (1.0 - sun_leaf[:, None]) * c_cadmium[None, :] + sun_leaf[:, None] * c_coral[None, :],
                c_lavender[None, :],
            ),
        )
        # Shrink in-plane scales to 0.58x and harden dot opacity so individual 3D stipple particles pop crisply!
        order_ax = np.argsort(sc, axis=1)
        ar = np.arange(len(k_idx))
        sc[ar, order_ax[:, 2]] *= 0.56
        sc[ar, order_ax[:, 1]] *= 0.62
        op_dots = np.where(op_raw < 0.026, op_raw * 0.03, np.clip(1.0 - np.power(np.clip(1.0 - op_raw, 1e-5, 1.0), 7.5), 0.0, 0.98))
        return np.clip(col, 0.0, 1.0).astype(np.float32), op_dots.astype(np.float32), sc

    if preset_name == "sakura_watercolor":
        # Spring Sakura Botanical Pastel: blossom rose-pink upper crown & tender spring jade lower leaves
        is_blossom = (0.68 * sun_leaf + 0.32 * leaf_hash) > 0.36
        c_petal_base = np.array([0.88, 0.40, 0.56], dtype=np.float32)
        c_petal_tip = np.array([0.99, 0.80, 0.86], dtype=np.float32)
        c_bud_base = np.array([0.36, 0.64, 0.36], dtype=np.float32)
        c_bud_tip = np.array([0.70, 0.88, 0.52], dtype=np.float32)

        col_blos = (1.0 - s[:, None]) * c_petal_base[None, :] + s[:, None] * c_petal_tip[None, :]
        col_bud = (1.0 - s[:, None]) * c_bud_base[None, :] + s[:, None] * c_bud_tip[None, :]
        col = np.where(is_blossom[:, None], col_blos, col_bud)
        rim = np.clip((rho - 0.83) / 0.16, 0.0, 1.0)[:, None]
        c_plum_rim = np.array([0.55, 0.20, 0.35], dtype=np.float32)[None, :]
        col = col * (0.86 + 0.26 * lum[:, None])
        col = (1.0 - 0.48 * rim) * col + (0.48 * rim) * c_plum_rim
        return np.clip(col, 0.0, 1.0).astype(np.float32), op_m1, sc

    if preset_name == "cyanotype_celadon":
        # Museum Botanical Cyanotype & Song Celadon Glaze: deep Prussian blue base -> luminous ice-celadon tip & rim
        c_prussian = np.array([0.07, 0.22, 0.48], dtype=np.float32)
        c_celadon = np.array([0.28, 0.68, 0.72], dtype=np.float32)
        c_ivory = np.array([0.84, 0.94, 0.96], dtype=np.float32)
        t_prog = np.clip(0.60 * s + 0.40 * sun_leaf, 0.0, 1.0)[:, None]
        col = np.where(
            t_prog < 0.55,
            (1.0 - t_prog / 0.55) * c_prussian + (t_prog / 0.55) * c_celadon,
            (1.0 - (t_prog - 0.55) / 0.45) * c_celadon + ((t_prog - 0.55) / 0.45) * c_ivory,
        )
        # Classic cyanotype white-cyan silhouette rim highlight + Prussian contour line
        outer_line = (rho > 0.89).astype(np.float32)[:, None]
        inner_glow = ((rho > 0.76) & (rho <= 0.89)).astype(np.float32)[:, None]
        col = col * (1.0 - 0.35 * inner_glow) + c_ivory[None, :] * (0.35 * inner_glow)
        col = col * (1.0 - 0.65 * outer_line) + c_prussian[None, :] * (0.65 * outer_line)
        return np.clip(col, 0.0, 1.0).astype(np.float32), op_m1, sc

    raise ValueError(f"Unknown style preset: {preset_name}")


def compose_mixed_style_plant(
    sub: LeafKernelSubstrateM12,
    leaf_style_map: dict[int, str] | str,
    trunk_theme: str = "natural_warm",
) -> tuple[GaussianCloud3D, np.ndarray, dict[str, int]]:
    """Compile a single unified 3DGS plant model where each 3D leaf has its own assigned artistic preset!

    Args:
      sub: Canonical M1+M2 per-leaf Gaussian kernel substrate.
      leaf_style_map: Either a single preset name (uniform plant style) or a dict {leaf_id: preset_name}
        assigning arbitrarily different styles to individual leaves on the same plant!

    Returns:
      (styled_cloud, per_kernel_rgb, leaf_counts_per_style)
    """
    rgb_out, op_out, sc_out = _style_pot_and_wood(sub, trunk_theme=trunk_theme)

    z_leaves = np.array([lf.centroid[2] for lf in sub.leaf_instances], dtype=np.float32)
    z_lo = float(np.percentile(z_leaves, 5.0)) if len(z_leaves) > 0 else -0.3
    z_hi = float(np.percentile(z_leaves, 95.0)) if len(z_leaves) > 0 else 0.9
    max_lid = max((lf.leaf_id for lf in sub.leaf_instances), default=0)
    z_lut = np.zeros(max_lid + 1, dtype=np.float32)
    for lf in sub.leaf_instances:
        z_lut[lf.leaf_id] = float(lf.centroid[2])

    # Group leaf IDs by their assigned preset so each preset runs in one fast vectorized call!
    preset_to_lids: dict[str, list[int]] = {p: [] for p in PRESET_ORDER}
    if isinstance(leaf_style_map, str):
        for lf in sub.leaf_instances:
            preset_to_lids.setdefault(leaf_style_map, []).append(lf.leaf_id)
    else:
        for lf in sub.leaf_instances:
            pname = leaf_style_map.get(lf.leaf_id, "ghibli_gouache")
            preset_to_lids.setdefault(pname, []).append(lf.leaf_id)

    style_leaf_counts: dict[str, int] = {}
    for pname, lids_list in preset_to_lids.items():
        if not lids_list:
            continue
        style_leaf_counts[pname] = len(lids_list)
        k_mask = np.isin(sub.kernel_labels, lids_list)
        k_idx = np.where(k_mask)[0]
        c_sub, op_sub, sc_sub = _apply_preset_to_leaf_subset(pname, k_idx, sub, z_lo, z_hi, z_lut)
        rgb_out[k_idx] = c_sub
        op_out[k_idx] = op_sub
        sc_out[k_idx] = sc_sub

    styled_cloud = build_cloud_from_arrays(
        means=sub.cloud.means,
        scales=sc_out,
        quats_wxyz=sub.cloud.quats_wxyz,
        opacities=op_out,
        rgb_dc=rgb_out,
        shs=sub.cloud.shs,
    )
    return styled_cloud, rgb_out, style_leaf_counts


def build_mixed_mode_a_crown_sectors(sub: LeafKernelSubstrateM12) -> dict[int, str]:
    """Mode A (5-Zone Crown Symphony): partitions the tree crown spatially into 5 distinct artistic style zones."""
    ctrs = np.array([lf.centroid for lf in sub.leaf_instances], dtype=np.float64)
    center_xy = np.median(ctrs[:, :2], axis=0)
    z_med = float(np.median(ctrs[:, 2]))

    # Use 3D crown azimuth + upper/lower crown split so all 5 styles are prominently visible from EVERY side view!
    style_map: dict[int, str] = {}
    sector_presets = [
        "ukiyoe_papercut",      # Warm vermilion/gold upper-left
        "ghibli_gouache",       # Lush emerald-chartreuse mid-left
        "sumie_ink_wash",       # Monochrome Xuan ink central-right
        "sakura_watercolor",    # Blossom pink upper-right
        "pointillist_stipple",  # Crisp 3D stipple dots lower/mid-front
        "cyanotype_celadon",    # Cool Prussian-celadon accent zone
    ]
    # K-means-like deterministic 6-medoid spatial crown partition so each branch cluster holds a coherent style!
    # Pick 6 well-spread seed centroids across (x, y, z)
    angles = np.arctan2(ctrs[:, 1] - center_xy[1], ctrs[:, 0] - center_xy[0])  # [-pi, pi]
    for lf, ang, pt in zip(sub.leaf_instances, angles, ctrs):
        # Project onto screen-horizontal & vertical band (x + 0.35*y) and z so side views see a rich 6-zone tapestry!
        horiz = float(pt[0] - center_xy[0] + 0.35 * (pt[1] - center_xy[1]))
        is_upper = float(pt[2]) >= z_med + 0.04
        if is_upper:
            if horiz < -0.09:
                s_name = "ukiyoe_papercut"
            elif horiz < 0.08:
                s_name = "sakura_watercolor"
            else:
                s_name = "sumie_ink_wash"
        else:
            if horiz < -0.08:
                s_name = "ghibli_gouache"
            elif horiz < 0.08:
                s_name = "pointillist_stipple"
            else:
                s_name = "cyanotype_celadon"
        style_map[lf.leaf_id] = s_name
    return style_map


def build_mixed_mode_b_rosette_mosaic(sub: LeafKernelSubstrateM12) -> dict[int, str]:
    """Mode B (Intra-Rosette Per-Leaflet Mosaic): greedy 3D graph-coloring so touching leaflets in the SAME rosette get DIFFERENT styles!"""
    ctrs = np.array([lf.centroid for lf in sub.leaf_instances], dtype=np.float64)
    tree = cKDTree(ctrs)
    _, nbrs = tree.query(ctrs, k=min(6, len(ctrs)))

    style_map: dict[int, str] = {}
    usage_counts = {p: 0 for p in PRESET_ORDER}

    # Process leaves in spatial order and greedily pick the least-used preset NOT used by closest neighbors!
    order = np.argsort(ctrs[:, 2] * 2.0 + ctrs[:, 0])
    for idx_i in order:
        lid = sub.leaf_instances[int(idx_i)].leaf_id
        nbr_styles = set()
        for nb in nbrs[int(idx_i), 1:]:
            nb_lid = sub.leaf_instances[int(nb)].leaf_id
            if nb_lid in style_map:
                nbr_styles.add(style_map[nb_lid])

        candidates = [p for p in PRESET_ORDER if p not in nbr_styles]
        if not candidates:
            candidates = list(PRESET_ORDER)
        # Pick least globally used candidate to ensure balanced 1/6 representation across all 6 presets
        chosen = min(candidates, key=lambda p: (usage_counts[p], PRESET_ORDER.index(p)))
        style_map[lid] = chosen
        usage_counts[chosen] += 1

    return style_map


def build_mixed_mode_c_sumie_hero_bloom(sub: LeafKernelSubstrateM12) -> dict[int, str]:
    """Mode C (Sumi-e Monochrome Crown + 4 Vivid Stylized Hero Bouquets): selective botanical focal showcase."""
    ctrs = np.array([lf.centroid for lf in sub.leaf_instances], dtype=np.float64)
    tree = cKDTree(ctrs)

    style_map: dict[int, str] = {lf.leaf_id: "sumie_ink_wash" for lf in sub.leaf_instances}
    outer_ids = [i for i, lf in enumerate(sub.leaf_instances) if lf.visibility_tier == "OUTER_ENCLOSED"]
    if len(outer_ids) < 8:
        return style_map

    out_ctrs = ctrs[outer_ids]
    x_lo, x_hi = np.percentile(out_ctrs[:, 0], [18.0, 82.0])
    y_lo, y_hi = np.percentile(out_ctrs[:, 1], [20.0, 80.0])
    z_lo, z_mid, z_hi = np.percentile(out_ctrs[:, 2], [25.0, 58.0, 86.0])

    # Data-driven outer-canopy anchor targets (upper-left apex, upper-right branch, mid-front rosette, lower-side rosette)
    targets = np.array(
        [
            [x_lo, 0.0, z_hi],
            [x_hi, y_lo, z_mid + 0.06],
            [0.0, y_hi, z_mid],
            [x_lo * 0.8, y_lo * 0.8, z_lo],
        ],
        dtype=np.float64,
    )
    hero_presets = ["ukiyoe_papercut", "sakura_watercolor", "cyanotype_celadon", "ghibli_gouache"]

    for tgt, h_preset in zip(targets, hero_presets):
        _, seed_pos = tree.query(tgt, k=1)
        # Group the 22 nearest leaves around each focal outer rosette (~18-20 outer/mid leaflets per bouquet)
        _, bouquet_idxs = tree.query(ctrs[int(seed_pos)], k=min(22, len(ctrs)))
        for r_i in np.atleast_1d(bouquet_idxs):
            lf = sub.leaf_instances[int(r_i)]
            if lf.visibility_tier != "DEEP_OCCLUDED":
                style_map[lf.leaf_id] = h_preset

    return style_map
